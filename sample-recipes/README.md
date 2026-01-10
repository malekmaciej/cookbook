# Sample Recipe Collection

This directory contains sample recipes to demonstrate the format and structure that works best with the CookBook Chatbot.

## Available Sample Recipes

1. **chocolate-chip-cookies.md** - Classic American cookies
2. **spaghetti-carbonara.md** - Traditional Italian pasta dish

## Recipe Format Best Practices

For best results with the Knowledge Base, structure your recipes with:

### Essential Sections
- **Title**: Clear, descriptive name
- **Information**: Prep time, cook time, servings, difficulty
- **Ingredients**: Organized by category with measurements
- **Instructions**: Step-by-step numbered list
- **Tips**: Common issues and solutions

### Optional But Helpful Sections
- Variations
- Substitutions
- Storage instructions
- Nutritional information
- Cultural/historical context
- Pairing suggestions

## Supported File Formats

The Bedrock Knowledge Base supports:
- **.md** (Markdown) - Recommended
- **.txt** (Plain text)
- **.pdf** (PDF documents)
- **.docx** (Microsoft Word)
- **.html** (HTML files)

## How to Use These Samples

### Option 1: Upload to S3 After Deployment

```bash
# Get bucket name from Terraform output
BUCKET_NAME=$(terraform output -raw s3_bucket_name)

# Upload samples
aws s3 cp sample-recipes/ s3://${BUCKET_NAME}/ --recursive --exclude "README.md"
```

### Option 2: Use as Templates

Copy and modify these recipes to create your own recipe collection.

## Creating Your Own Recipes

### Tips for AI-Friendly Recipes

1. **Use Clear Structure**: Headers, lists, and sections help the AI understand
2. **Include Context**: Add serving sizes, dietary info, cuisine type
3. **Provide Details**: Measurements, temperatures, timing are important
4. **Add Variations**: Different options help answer more questions
5. **Include Troubleshooting**: Common issues help the AI provide better advice

### Example Structure

```markdown
# Recipe Name

Brief description

## Information
- Prep Time: X minutes
- Cook Time: X minutes
- Servings: X
- Difficulty: Easy/Medium/Hard

## Ingredients
- Item 1
- Item 2

## Instructions
1. Step 1
2. Step 2

## Tips
- Tip 1
- Tip 2
```

## After Uploading

Remember to trigger a Knowledge Base sync after uploading new recipes:

```bash
KB_ID=$(terraform output -raw knowledge_base_id)
DATA_SOURCE_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' --output text)

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

## Testing Your Recipes

After ingestion completes, try queries like:
- "How do I make chocolate chip cookies?"
- "What ingredients do I need for carbonara?"
- "Show me the cookie recipe"
- "What temperature should I bake cookies at?"

## Recipe Collection Ideas

Build themed collections:
- **Baking**: Breads, cakes, cookies, pastries
- **Quick Meals**: 30-minute dinners, one-pot recipes
- **Healthy**: Low-calorie, high-protein, vegetarian
- **Cuisines**: Italian, Mexican, Asian, Indian
- **Special Diets**: Gluten-free, vegan, keto, paleo
- **Occasions**: Holiday meals, party appetizers, desserts

## Quality Tips

✅ **Good Recipe Characteristics**:
- Clear measurements (cups, grams, teaspoons)
- Specific temperatures (350°F / 180°C)
- Detailed timing (cook for 10-12 minutes)
- Step-by-step instructions
- Troubleshooting section
- Ingredient substitutions

❌ **Avoid**:
- Vague measurements ("a pinch", "some")
- Missing cooking times or temperatures
- Unclear instructions
- No ingredient list
- Recipes without context

## Contributing Your Own Recipes

Feel free to add your family recipes, tested favorites, or restaurant recreations to build your personal cookbook!

## License

These sample recipes are provided as examples for the CookBook Chatbot project.
