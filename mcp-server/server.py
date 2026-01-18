"""
MCP Server for Recipe Management using FastMCP 2.0

This server provides tools and resources to interact with recipes stored in a GitHub repository.
It exposes functionality for listing, searching, getting, creating, and updating recipes.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from github import Github, GithubException
import base64
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    name="Recipe MCP Server"
)

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "malekmaciej/przepisy")
RECIPES_PATH = os.getenv("RECIPES_PATH", "")  # Root path in the repo for recipes

# Initialize GitHub client
github_client = None
repo = None

def initialize_github():
    """Initialize GitHub client and repository"""
    global github_client, repo
    
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN environment variable not set")
        raise ValueError("GITHUB_TOKEN is required")
    
    try:
        github_client = Github(GITHUB_TOKEN)
        repo = github_client.get_repo(GITHUB_REPO)
        logger.info(f"Successfully connected to GitHub repo: {GITHUB_REPO}")
    except Exception as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        raise


def get_file_content(file_path: str) -> str:
    """Get content of a file from the repository"""
    try:
        content_file = repo.get_contents(file_path)
        if isinstance(content_file, list):
            raise ValueError(f"Path {file_path} is a directory, not a file")
        
        content = base64.b64decode(content_file.content).decode('utf-8')
        return content
    except GithubException as e:
        logger.error(f"GitHub error fetching {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error decoding content from {file_path}: {e}")
        raise


def extract_recipe_name_from_content(content: str) -> Optional[str]:
    """
    Extract recipe name from the first line of the file content.
    Recipe name is expected to be on the first line starting with '#'.
    
    Args:
        content: The full content of the recipe file
        
    Returns:
        The recipe name without the '#' prefix, or None if not found
    """
    lines = content.split('\n')
    if lines and lines[0].startswith('#'):
        # Remove the '#' and any leading/trailing whitespace
        return lines[0].lstrip('#').strip()
    return None


def list_recipes_in_path(path: str = "") -> List[Dict[str, Any]]:
    """List all recipe files in a given path"""
    recipes = []
    try:
        contents = repo.get_contents(path)
        
        for content in contents:
            if content.type == "file" and content.name.endswith(".md"):
                recipes.append({
                    "name": content.name,
                    "path": content.path,
                    "size": content.size,
                    "sha": content.sha
                })
            elif content.type == "dir":
                # Recursively list recipes in subdirectories
                recipes.extend(list_recipes_in_path(content.path))
        
        return recipes
    except GithubException as e:
        logger.error(f"Error listing recipes in {path}: {e}")
        return []


@mcp.tool()
def list_recipes() -> List[Dict[str, Any]]:
    """
    List all available recipes from the GitHub repository.
    
    Returns:
        A list of recipe metadata including name, path, size, and SHA.
    """
    try:
        recipes = list_recipes_in_path(RECIPES_PATH)
        logger.info(f"Listed {len(recipes)} recipes")
        return recipes
    except Exception as e:
        logger.error(f"Error listing recipes: {e}")
        raise


@mcp.tool()
def search_recipes(query: str) -> List[Dict[str, Any]]:
    """
    Search for recipes by name found inside the file (first line starting with '#').
    Files without a '#' header on the first line will be skipped.
    
    Args:
        query: Search term to find in recipe names (from first line of files)
        
    Returns:
        A list of matching recipes with their metadata and extracted names.
    """
    try:
        matching_recipes = []
        recipes = list_recipes_in_path(RECIPES_PATH)
        
        query_lower = query.lower()
        
        # Search by extracting the name from each file's first line
        for recipe in recipes:
            try:
                content = get_file_content(recipe["path"])
                recipe_name = extract_recipe_name_from_content(content)
                
                if recipe_name and query_lower in recipe_name.lower():
                    # Add the extracted name to the recipe metadata
                    recipe_with_name = recipe.copy()
                    recipe_with_name["recipe_name"] = recipe_name
                    matching_recipes.append(recipe_with_name)
            except Exception as e:
                logger.warning(f"Could not search recipe at {recipe['path']}: {e}")
        
        logger.info(f"Found {len(matching_recipes)} recipes matching '{query}'")
        return matching_recipes
    except Exception as e:
        logger.error(f"Error searching recipes: {e}")
        raise


@mcp.tool()
def get_recipe(path: str) -> Dict[str, Any]:
    """
    Get the full content and metadata of a specific recipe.
    
    Args:
        path: Path to the recipe file in the repository
        
    Returns:
        Recipe content and metadata including name (extracted from first line), content, and path.
    """
    try:
        content = get_file_content(path)
        
        # Extract recipe name from the first line of the file
        recipe_name = extract_recipe_name_from_content(content)
        
        # Fallback to filename if name extraction fails
        if not recipe_name:
            recipe_name = os.path.basename(path).replace(".md", "").replace("-", " ").title()
        
        return {
            "name": recipe_name,
            "path": path,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error getting recipe from {path}: {e}")
        raise


@mcp.tool()
def create_recipe(name: str, content: str, path: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new recipe in the GitHub repository.
    
    Args:
        name: Name of the recipe (will be used for filename if path not provided)
        content: Full content of the recipe in Markdown format
        path: Optional custom path. If not provided, will use sanitized name in root recipes path
        
    Returns:
        Information about the created recipe including its path and commit SHA.
    """
    try:
        # Sanitize filename if path not provided
        if not path:
            sanitized_name = re.sub(r'[^a-z0-9\s-]', '', name.lower())
            sanitized_name = re.sub(r'\s+', '-', sanitized_name)
            file_path = os.path.join(RECIPES_PATH, f"{sanitized_name}.md")
        else:
            file_path = path
        
        # Create the file in the repository
        result = repo.create_file(
            path=file_path,
            message=f"Add recipe: {name}",
            content=content,
            branch="main"
        )
        
        logger.info(f"Created recipe at {file_path}")
        return {
            "success": True,
            "path": file_path,
            "sha": result['commit'].sha,
            "message": f"Recipe '{name}' created successfully"
        }
    except GithubException as e:
        logger.error(f"GitHub error creating recipe: {e}")
        return {"error": str(e), "success": False}
    except Exception as e:
        logger.error(f"Error creating recipe: {e}")
        return {"error": str(e), "success": False}


@mcp.tool()
def update_recipe(path: str, content: str, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Update an existing recipe in the GitHub repository.
    
    Args:
        path: Path to the recipe file to update
        content: New content for the recipe
        message: Optional commit message (defaults to "Update recipe: {filename}")
        
    Returns:
        Information about the updated recipe including its new SHA.
    """
    try:
        # Get the current file to retrieve its SHA
        file = repo.get_contents(path)
        
        if isinstance(file, list):
            return {"error": f"Path {path} is a directory, not a file", "success": False}
        
        # Set default commit message
        if not message:
            filename = os.path.basename(path)
            message = f"Update recipe: {filename}"
        
        # Update the file
        result = repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=file.sha,
            branch="main"
        )
        
        logger.info(f"Updated recipe at {path}")
        return {
            "success": True,
            "path": path,
            "sha": result['commit'].sha,
            "message": f"Recipe updated successfully"
        }
    except GithubException as e:
        logger.error(f"GitHub error updating recipe: {e}")
        return {"error": str(e), "success": False}
    except Exception as e:
        logger.error(f"Error updating recipe: {e}")
        return {"error": str(e), "success": False}


@mcp.resource("recipe://list")
def get_recipe_list() -> str:
    """
    Resource endpoint to get a formatted list of all recipes.
    
    Returns:
        A formatted text list of all available recipes.
    """
    try:
        recipes = list_recipes_in_path(RECIPES_PATH)
        
        if not recipes:
            return "No recipes found in the repository."
        
        output = f"# Available Recipes ({len(recipes)} total)\n\n"
        for recipe in recipes:
            output += f"- **{recipe['name']}** (`{recipe['path']}`)\n"
        
        return output
    except Exception as e:
        logger.error(f"Error getting recipe list: {e}")
        return f"Error: {str(e)}"


@mcp.resource("recipe://{path}")
def get_recipe_resource(path: str) -> str:
    """
    Resource endpoint to get the content of a specific recipe.
    
    Args:
        path: Path to the recipe file
        
    Returns:
        The full content of the recipe.
    """
    try:
        content = get_file_content(path)
        return content
    except Exception as e:
        logger.error(f"Error getting recipe resource {path}: {e}")
        return f"Error: {str(e)}"


def main():
    """Main entry point for the MCP server"""
    # Initialize GitHub connection
    initialize_github()
    
    # Get configuration from environment
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")
    
    logger.info(f"Starting MCP server on {host}:{port}{path}")
    logger.info(f"Connected to GitHub repository: {GITHUB_REPO}")
    
    # Run the server with streamable HTTP transport
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=path,
        session_timeout=3600,
        max_connections=1000
    )


if __name__ == "__main__":
    main()
