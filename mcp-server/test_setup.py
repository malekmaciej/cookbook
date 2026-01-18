"""
Simple test script to verify MCP server functionality
"""
import sys
import os

# Test 1: Import FastMCP
try:
    from fastmcp import FastMCP
    print("✓ FastMCP module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import FastMCP: {e}")
    sys.exit(1)

# Test 2: Import PyGithub
try:
    from github import Github
    print("✓ PyGithub module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import PyGithub: {e}")
    sys.exit(1)

# Test 3: Verify server module structure
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("server", "server.py")
    server_module = importlib.util.module_from_spec(spec)
    
    # Mock the environment to avoid errors during module execution
    os.environ.setdefault("GITHUB_TOKEN", "test_token")
    os.environ.setdefault("GITHUB_REPO", "test/repo")
    
    # Execute the module to catch any syntax or import errors
    spec.loader.exec_module(server_module)
    print("✓ Server module structure is valid and all imports work")
except Exception as e:
    print(f"✗ Failed to load server module: {e}")
    sys.exit(1)
finally:
    # Clean up test environment variables if they were set by us
    if os.getenv("GITHUB_TOKEN") == "test_token":
        os.environ.pop("GITHUB_TOKEN", None)
    if os.getenv("GITHUB_REPO") == "test/repo":
        os.environ.pop("GITHUB_REPO", None)

# Test 4: Check required environment variables documentation
required_vars = ["GITHUB_TOKEN", "GITHUB_REPO"]
print("\nRequired environment variables:")
for var in required_vars:
    value = os.getenv(var)
    if value:
        masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
        print(f"  ✓ {var}: {masked}")
    else:
        print(f"  ⚠ {var}: Not set (required for server to run)")

# Test 5: Optional environment variables
optional_vars = ["RECIPES_PATH", "MCP_HOST", "MCP_PORT", "MCP_PATH"]
print("\nOptional environment variables:")
for var in optional_vars:
    value = os.getenv(var)
    if value:
        print(f"  ✓ {var}: {value}")
    else:
        print(f"  - {var}: Using default")

print("\n" + "="*60)
print("All basic tests passed!")
print("="*60)
print("\nTo run the server, ensure GITHUB_TOKEN is set and run:")
print("  python server.py")
print("\nOr use Docker:")
print("  docker-compose up")
