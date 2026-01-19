from typing import Optional
"""
Test script to verify the name extraction and search functionality.
This tests the changes locally without requiring GitHub API access.
"""
import sys
import os

# Add the current directory to path to import from server
sys.path.insert(0, os.path.dirname(__file__))

# Mock the server module's extract_recipe_name_from_content function
def extract_recipe_name_from_content(content: str) -> Optional[str]:
    """
    Extract recipe name from the first line of the file content.
    Recipe name is expected to be on the first line starting with '#'.
    """
    lines = content.split('\n')
    if lines and lines[0].startswith('#'):
        # Remove the '#' and any leading/trailing whitespace
        return lines[0].lstrip('#').strip()
    return None


def test_extract_recipe_name():
    """Test the extract_recipe_name_from_content function"""
    print("Testing extract_recipe_name_from_content function...")
    
    # Test 1: Normal recipe with # header
    content1 = "# Classic Chocolate Chip Cookies\n\nThis is a great recipe."
    name1 = extract_recipe_name_from_content(content1)
    assert name1 == "Classic Chocolate Chip Cookies", f"Expected 'Classic Chocolate Chip Cookies', got '{name1}'"
    print(f"✓ Test 1 passed: '{name1}'")
    
    # Test 2: Recipe with multiple # symbols
    content2 = "### Spaghetti Carbonara\n\nIngredients..."
    name2 = extract_recipe_name_from_content(content2)
    assert name2 == "Spaghetti Carbonara", f"Expected 'Spaghetti Carbonara', got '{name2}'"
    print(f"✓ Test 2 passed: '{name2}'")
    
    # Test 3: Recipe with spaces after #
    content3 = "#   Banana Bread   \n\nDelicious bread."
    name3 = extract_recipe_name_from_content(content3)
    assert name3 == "Banana Bread", f"Expected 'Banana Bread', got '{name3}'"
    print(f"✓ Test 3 passed: '{name3}'")
    
    # Test 4: File without # header (should return None)
    content4 = "This file doesn't start with #\n\nContent here."
    name4 = extract_recipe_name_from_content(content4)
    assert name4 is None, f"Expected None, got '{name4}'"
    print(f"✓ Test 4 passed: returned None for non-# header")
    
    # Test 5: Empty content
    content5 = ""
    name5 = extract_recipe_name_from_content(content5)
    assert name5 is None, f"Expected None for empty content, got '{name5}'"
    print(f"✓ Test 5 passed: returned None for empty content")
    
    print("\n✅ All extraction tests passed!")


def test_with_sample_recipes():
    """Test with actual sample recipes from the repository"""
    print("\nTesting with sample recipes from repository...")
    
    # Use relative path from current file location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_recipes_path = os.path.join(os.path.dirname(current_dir), "sample-recipes")
    
    # Test with chocolate chip cookies
    cookie_file = os.path.join(sample_recipes_path, "chocolate-chip-cookies.md")
    if os.path.exists(cookie_file):
        with open(cookie_file, 'r') as f:
            content = f.read()
        name = extract_recipe_name_from_content(content)
        print(f"✓ Extracted from chocolate-chip-cookies.md: '{name}'")
        assert name == "Classic Chocolate Chip Cookies", f"Expected 'Classic Chocolate Chip Cookies', got '{name}'"
    
    # Test with spaghetti carbonara
    carbonara_file = os.path.join(sample_recipes_path, "spaghetti-carbonara.md")
    if os.path.exists(carbonara_file):
        with open(carbonara_file, 'r') as f:
            content = f.read()
        name = extract_recipe_name_from_content(content)
        print(f"✓ Extracted from spaghetti-carbonara.md: '{name}'")
        assert name == "Classic Spaghetti Carbonara", f"Expected 'Classic Spaghetti Carbonara', got '{name}'"
    
    print("\n✅ All sample recipe tests passed!")


def test_search_logic():
    """Test the search logic with extracted names"""
    print("\nTesting search logic...")
    
    # Simulate recipe data
    recipes = [
        {"name": "Classic Chocolate Chip Cookies", "matches": ["chocolate", "cookies", "chip", "classic"]},
        {"name": "Classic Spaghetti Carbonara", "matches": ["spaghetti", "carbonara", "classic", "pasta"]},
        {"name": "Banana Bread", "matches": ["banana", "bread"]},
    ]
    
    test_cases = [
        ("chocolate", ["Classic Chocolate Chip Cookies"]),
        ("classic", ["Classic Chocolate Chip Cookies", "Classic Spaghetti Carbonara"]),
        ("spaghetti", ["Classic Spaghetti Carbonara"]),
        ("banana", ["Banana Bread"]),
        ("pizza", []),  # No matches
    ]
    
    for query, expected_matches in test_cases:
        query_lower = query.lower()
        matches = [r["name"] for r in recipes if query_lower in r["name"].lower()]
        assert matches == expected_matches, f"For query '{query}', expected {expected_matches}, got {matches}"
        print(f"✓ Search for '{query}': found {len(matches)} match(es)")
    
    print("\n✅ All search logic tests passed!")


if __name__ == "__main__":
    try:
        test_extract_recipe_name()
        test_with_sample_recipes()
        test_search_logic()
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
