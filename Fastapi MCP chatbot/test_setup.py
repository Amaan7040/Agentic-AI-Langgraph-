"""
Test script to verify ChatterBot MCP setup
Run this before starting the server
"""

import sys
import os
from pathlib import Path

print("=" * 70)
print("ChatterBot MCP - Setup Verification")
print("=" * 70)

# Test 1: Check Python version
print("\n[1/7] Checking Python version...")
version = sys.version_info
if version.major == 3 and version.minor >= 9:
    print(f"   ✓ Python {version.major}.{version.minor}.{version.micro}")
else:
    print(f"   ✗ Python {version.major}.{version.minor} (need 3.9+)")
    sys.exit(1)

# Test 2: Check environment file
print("\n[2/7] Checking environment file...")
if Path(".env").exists():
    print("   ✓ .env file found")
    from dotenv import load_dotenv
    load_dotenv()
    
    required_keys = ["GROQ_API_KEY", "WEATHER_API_KEY", "STOCK_API_KEY"]
    missing = []
    for key in required_keys:
        if os.getenv(key):
            print(f"   ✓ {key} is set")
        else:
            print(f"   ✗ {key} is missing")
            missing.append(key)
    
    if missing:
        print(f"\n   Warning: Missing API keys: {', '.join(missing)}")
else:
    print("   ✗ .env file not found")
    print("   Copy .env.example to .env and add your API keys")
    sys.exit(1)

# Test 3: Check required packages
print("\n[3/7] Checking required packages...")
required_packages = [
    "fastapi",
    "uvicorn",
    "langchain_core",
    "langchain_groq",
    "langgraph",
    "langchain_mcp_adapters",
    "fastmcp",
    "websockets"
]

missing_packages = []
for package in required_packages:
    try:
        __import__(package)
        print(f"   ✓ {package}")
    except ImportError:
        print(f"   ✗ {package}")
        missing_packages.append(package)

if missing_packages:
    print(f"\n   Install missing packages:")
    print(f"   pip install {' '.join(missing_packages)}")
    sys.exit(1)

# Test 4: Check MCP server file
print("\n[4/7] Checking MCP server file...")
mcp_server_path = Path(r"C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP\mcp-tools-local.py")
if mcp_server_path.exists():
    print(f"   ✓ MCP server found: {mcp_server_path}")
else:
    print(f"   ✗ MCP server not found: {mcp_server_path}")
    print("   Update the path in main.py")
    sys.exit(1)

# Test 5: Check main.py
print("\n[5/7] Checking main.py...")
if Path("main.py").exists():
    print("   ✓ main.py found")
else:
    print("   ✗ main.py not found")
    sys.exit(1)

# Test 6: Check index.html
print("\n[6/7] Checking index.html...")
if Path("index.html").exists():
    print("   ✓ index.html found")
else:
    print("   ✗ index.html not found")
    sys.exit(1)

# Test 7: Test MCP client initialization
print("\n[7/7] Testing MCP client (this may take a moment)...")
try:
    import asyncio
    from langchain_mcp_adapters.client import MultiServerMCPClient
    
    async def test_mcp():
        try:
            client = MultiServerMCPClient({
                "test": {
                    "transport": "stdio",
                    "command": "python",
                    "args": [str(mcp_server_path)],
                }
            })
            
            # Get tools without context manager (correct for 0.1.0)
            tools = await client.get_tools()
            print(f"   ✓ MCP client works! Loaded {len(tools)} tools:")
            for tool in tools:
                print(f"      - {tool.name}")
            return True
        except Exception as e:
            print(f"   ✗ MCP client error: {e}")
            return False
    
    success = asyncio.run(test_mcp())
    if not success:
        print("\n   Check that mcp-tools-local.py is accessible")
        sys.exit(1)
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success!
print("\n" + "=" * 70)
print("✓ ALL CHECKS PASSED!")
print("=" * 70)
print("\nYour ChatterBot MCP setup is ready!")
print("\nTo start the server:")
print("  Windows: start.bat")
print("  Linux/Mac: ./start.sh")
print("  Manual: python main.py")
print("\nThen open: http://localhost:8000")
print("=" * 70)
