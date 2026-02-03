// CookBook Chatbot Application
class ChatbotApp {
    constructor() {
        this.conversationHistory = [];
        this.currentUser = null;
        this.userPool = null;
        this.cognitoUser = null;
        this.bedrockAgentRuntime = null;
        this.bedrockRuntime = null;
        this.mcpTools = null;
        
        this.initializeElements();
        this.initializeCognito();
    }

    initializeElements() {
        this.loginModal = document.getElementById('login-modal');
        this.loginBtn = document.getElementById('login-btn');
        this.logoutBtn = document.getElementById('logout-btn');
        this.sendBtn = document.getElementById('send-btn');
        this.userInput = document.getElementById('user-input');
        this.messagesContainer = document.getElementById('messages');

        // Event listeners
        this.loginBtn.addEventListener('click', () => this.handleLogin());
        this.logoutBtn.addEventListener('click', () => this.handleLogout());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    initializeCognito() {
        const poolData = {
            UserPoolId: window.CONFIG.cognito.userPoolId,
            ClientId: window.CONFIG.cognito.userPoolWebClientId
        };
        this.userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

        // Check if user is already logged in
        this.cognitoUser = this.userPool.getCurrentUser();
        
        if (this.cognitoUser != null) {
            this.cognitoUser.getSession((err, session) => {
                if (err) {
                    console.error('Session error:', err);
                    this.showLoginModal();
                    return;
                }
                if (session.isValid()) {
                    this.onAuthSuccess(session);
                } else {
                    this.showLoginModal();
                }
            });
        } else {
            this.showLoginModal();
        }
    }

    showLoginModal() {
        this.loginModal.classList.add('active');
    }

    hideLoginModal() {
        this.loginModal.classList.remove('active');
    }

    handleLogin() {
        // Redirect to Cognito Hosted UI
        const domain = window.CONFIG.cognito.domain;
        const clientId = window.CONFIG.cognito.userPoolWebClientId;
        const redirectUri = window.location.origin + window.location.pathname;
        
        const authUrl = `https://${domain}/login?` +
            `client_id=${clientId}&` +
            `response_type=code&` +
            `scope=openid+email+profile&` +
            `redirect_uri=${encodeURIComponent(redirectUri)}`;
        
        window.location.href = authUrl;
    }

    handleLogout() {
        if (this.cognitoUser) {
            this.cognitoUser.signOut();
        }
        
        // Clear AWS credentials
        AWS.config.credentials = null;
        
        // Redirect to Cognito logout
        const domain = window.CONFIG.cognito.domain;
        const clientId = window.CONFIG.cognito.userPoolWebClientId;
        const redirectUri = window.location.origin + window.location.pathname;
        
        const logoutUrl = `https://${domain}/logout?` +
            `client_id=${clientId}&` +
            `logout_uri=${encodeURIComponent(redirectUri)}`;
        
        window.location.href = logoutUrl;
    }

    async onAuthSuccess(session) {
        this.hideLoginModal();
        
        // Configure AWS credentials
        const token = session.getIdToken().getJwtToken();
        
        AWS.config.region = window.CONFIG.region;
        AWS.config.credentials = new AWS.CognitoIdentityCredentials({
            IdentityPoolId: window.CONFIG.cognito.identityPoolId,
            Logins: {
                [`cognito-idp.${window.CONFIG.region}.amazonaws.com/${window.CONFIG.cognito.userPoolId}`]: token
            }
        });

        // Refresh credentials
        await new Promise((resolve, reject) => {
            AWS.config.credentials.refresh((err) => {
                if (err) {
                    console.error('Credential refresh error:', err);
                    reject(err);
                } else {
                    resolve();
                }
            });
        });

        // Initialize AWS services
        this.bedrockAgentRuntime = new AWS.BedrockAgentRuntime({
            region: window.CONFIG.region
        });
        
        this.bedrockRuntime = new AWS.BedrockRuntime({
            region: window.CONFIG.region
        });

        // Discover MCP tools if configured
        if (window.CONFIG.mcpServerUrl) {
            await this.discoverMCPTools();
        }

        // Show welcome message
        this.addMessage('assistant', this.getWelcomeMessage());
    }

    getWelcomeMessage() {
        let message = `👨‍🍳 Welcome to CookBook Chatbot! I'm your AI cooking assistant powered by AWS Bedrock.

I can help you with:
- Finding recipes from the cookbook
- Answering cooking questions
- Providing ingredient substitutions
- Explaining cooking techniques`;

        if (window.CONFIG.mcpServerUrl && this.mcpTools) {
            message += '\n- Adding new recipes to the cookbook 📝';
        }

        message += '\n\nWhat would you like to cook today?';
        return message;
    }

    async discoverMCPTools() {
        try {
            const response = await fetch(window.CONFIG.mcpServerUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    id: 1,
                    method: 'tools/list'
                })
            });

            const result = await response.json();
            const tools = result?.result?.tools || [];

            // Convert MCP tools to Bedrock format
            this.mcpTools = tools.map(tool => ({
                toolSpec: {
                    name: tool.name,
                    description: tool.description || '',
                    inputSchema: { json: tool.inputSchema || {} }
                }
            }));

            console.log('Discovered MCP tools:', this.mcpTools);
        } catch (error) {
            console.error('Failed to discover MCP tools:', error);
            this.mcpTools = null;
        }
    }

    async callMCPTool(toolName, toolInput) {
        if (!window.CONFIG.mcpServerUrl) {
            return { error: 'MCP server is not configured' };
        }

        try {
            const response = await fetch(window.CONFIG.mcpServerUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    id: 1,
                    method: 'tools/call',
                    params: { name: toolName, arguments: toolInput }
                })
            });

            const result = await response.json();
            return result?.result || {};
        } catch (error) {
            return { error: error.message };
        }
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.textContent = role === 'user' ? '👤' : '👨‍🍳';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Convert markdown-style formatting to HTML
        contentDiv.innerHTML = this.formatMessage(content);

        if (role === 'user') {
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(avatarDiv);
        } else {
            messageDiv.appendChild(avatarDiv);
            messageDiv.appendChild(contentDiv);
        }

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Simple markdown-to-HTML conversion
        let formatted = content
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Lists
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
            // Line breaks
            .replace(/\n/g, '<br>');

        // Wrap consecutive <li> items in <ul>
        formatted = formatted.replace(/(<li>.*?<\/li>(?:<br>)?)+/g, (match) => {
            return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
        });

        return formatted;
    }

    showTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant typing';
        messageDiv.id = 'typing-indicator';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.textContent = '👨‍🍳';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chat-container');
        container.scrollTop = container.scrollHeight;
    }

    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message) return;

        // Disable input
        this.userInput.value = '';
        this.userInput.disabled = true;
        this.sendBtn.disabled = true;

        // Add user message
        this.addMessage('user', message);

        // Show typing indicator
        this.showTypingIndicator();

        try {
            await this.processMessage(message);
        } catch (error) {
            this.removeTypingIndicator();
            this.addMessage('assistant', `❌ Sorry, I encountered an error: ${error.message}\n\nPlease make sure the Knowledge Base is properly set up and contains recipe documents.`);
        } finally {
            // Re-enable input
            this.userInput.disabled = false;
            this.sendBtn.disabled = false;
            this.userInput.focus();
        }
    }

    async processMessage(userMessage) {
        try {
            // First, retrieve relevant context from Knowledge Base
            let kbContext = '';
            try {
                const retrieveParams = {
                    knowledgeBaseId: window.CONFIG.bedrock.knowledgeBaseId,
                    retrievalQuery: { text: userMessage },
                    retrievalConfiguration: {
                        vectorSearchConfiguration: { numberOfResults: 5 }
                    }
                };

                const kbResponse = await this.bedrockAgentRuntime.retrieve(retrieveParams).promise();
                const retrievedResults = kbResponse.retrievalResults || [];

                if (retrievedResults.length > 0) {
                    kbContext = retrievedResults
                        .map((result, i) => `Recipe context ${i + 1}:\n${result.content?.text || ''}`)
                        .join('\n\n');
                }
            } catch (error) {
                console.warn('Knowledge Base retrieval failed:', error);
            }

            // Prepare system prompt
            // Note: Recipe format uses Polish language as this is a Polish cookbook
            const systemPrompt = [{
                text: `You are a helpful cooking assistant with access to a cookbook knowledge base and recipe management tools.

Your capabilities:
1. Search and provide recipes from the cookbook
2. Answer cooking questions and provide advice
3. Use available tools to manage recipes (list, search, create, update)

When providing recipes, always format them clearly:

# Recipe Name

## Opis
Brief description

**Porcje:** [servings]
**Czas przygotowania:** [time]

## Składniki
- Ingredient list

## Sposób przygotowania
1. Step-by-step instructions

Always provide COMPLETE recipes with ALL ingredients and ALL steps.

If you have tools available, use them when appropriate:
- Use list_recipes or search_recipes to find recipes
- Use create_recipe to save new recipes the user wants to add
- Use update_recipe to modify existing recipes`
            }];

            // Prepare messages
            const messages = [{
                role: 'user',
                content: []
            }];

            // Add KB context if available
            if (kbContext) {
                messages[0].content.push({
                    text: `Relevant cookbook context:\n${kbContext}\n\n`
                });
            }

            messages[0].content.push({ text: userMessage });

            // Prepare tool configuration
            const converseParams = {
                modelId: window.CONFIG.bedrock.modelId,
                messages: messages,
                system: systemPrompt
            };

            if (this.mcpTools && this.mcpTools.length > 0) {
                converseParams.toolConfig = { tools: this.mcpTools };
            }

            // Call Bedrock Converse API with tool use
            const maxIterations = 5;
            let iteration = 0;

            while (iteration < maxIterations) {
                iteration++;

                const response = await this.bedrockRuntime.converse(converseParams).promise();

                const stopReason = response.stopReason;
                const outputMessage = response.output?.message || {};

                // Add assistant response to messages
                converseParams.messages.push(outputMessage);

                // Check if tool use is requested
                if (stopReason === 'tool_use') {
                    // Process tool calls
                    const toolResults = [];

                    for (const contentBlock of (outputMessage.content || [])) {
                        if (contentBlock.toolUse) {
                            const toolUse = contentBlock.toolUse;
                            const toolName = toolUse.name;
                            const toolInput = toolUse.input || {};
                            const toolUseId = toolUse.toolUseId;

                            console.log(`Calling tool: ${toolName} with input:`, toolInput);

                            // Call the MCP tool
                            const toolResult = await this.callMCPTool(toolName, toolInput);

                            // Format tool result
                            toolResults.push({
                                toolResult: {
                                    toolUseId: toolUseId,
                                    content: [{ json: toolResult }]
                                }
                            });
                        }
                    }

                    // Add tool results to messages
                    converseParams.messages.push({
                        role: 'user',
                        content: toolResults
                    });

                    // Continue the loop to get next response
                    continue;
                } else {
                    // Extract final response
                    let finalText = '';
                    for (const contentBlock of (outputMessage.content || [])) {
                        if (contentBlock.text) {
                            finalText += contentBlock.text;
                        }
                    }

                    this.removeTypingIndicator();
                    this.addMessage('assistant', finalText);
                    break;
                }
            }

            if (iteration >= maxIterations) {
                this.removeTypingIndicator();
                this.addMessage('assistant', '⚠️ Maximum tool iterations reached.');
            }

        } catch (error) {
            console.error('Error processing message:', error);
            throw error;
        }
    }
}

// Handle OAuth callback
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code) {
        // Exchange code for tokens using Cognito token endpoint
        const domain = window.CONFIG.cognito.domain;
        const clientId = window.CONFIG.cognito.userPoolWebClientId;
        const redirectUri = window.location.origin + window.location.pathname;
        
        fetch(`https://${domain}/oauth2/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                client_id: clientId,
                code: code,
                redirect_uri: redirectUri
            })
        })
        .then(response => response.json())
        .then(tokens => {
            // Store tokens in session storage
            sessionStorage.setItem('id_token', tokens.id_token);
            sessionStorage.setItem('access_token', tokens.access_token);
            sessionStorage.setItem('refresh_token', tokens.refresh_token);
            
            // Clean URL and reload
            window.history.replaceState({}, document.title, window.location.pathname);
            window.location.reload();
        })
        .catch(error => {
            console.error('Token exchange error:', error);
            alert('Authentication failed. Please try again.');
            window.history.replaceState({}, document.title, window.location.pathname);
        });
        
        return true;
    }
    
    return false;
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check for OAuth callback
    if (!handleOAuthCallback()) {
        // Initialize the chatbot app
        const app = new ChatbotApp();
        window.chatbotApp = app;
    }
});
