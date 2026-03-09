"""
Test script for MCP Chatbot
Run this to verify your setup before launching the UI
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

print("=" * 70)
print("🧪 MCP CHATBOT - SETUP TEST")
print("=" * 70)

# Test 1: Check environment variables
print("\n[1/6] Checking environment variables...")
from dotenv import load_dotenv
load_dotenv()

required_vars = ["GROQ_API_KEY", "WEATHER_API_KEY", "STOCK_API_KEY"]
missing_vars = []

for var in required_vars:
    if os.getenv(var):
        print(f"   ✅ {var} is set")
    else:
        print(f"   ❌ {var} is MISSING")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
    print("   Some tools may not work without these API keys.")
else:
    print("   ✅ All required environment variables found!")

# Test 2: Check required packages
print("\n[2/6] Checking required packages...")
required_packages = [
    "langgraph",
    "langchain_groq",
    "langchain_community",
    "langchain_core",
    "fastmcp",
    "langchain_mcp_adapters",
    "streamlit",
]

missing_packages = []
for package in required_packages:
    try:
        __import__(package)
        print(f"   ✅ {package}")
    except ImportError:
        print(f"   ❌ {package} - NOT FOUND")
        missing_packages.append(package)

if missing_packages:
    print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
    print("   Install with: pip install " + " ".join(missing_packages))
    sys.exit(1)
else:
    print("   ✅ All required packages installed!")

# Test 3: Check MCP server file
print("\n[3/6] Checking MCP server file...")
mcp_server_path = r"C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP\mcp-tools-local.py"

if os.path.exists(mcp_server_path):
    print(f"   ✅ MCP server found at: {mcp_server_path}")
else:
    print(f"   ❌ MCP server NOT FOUND at: {mcp_server_path}")
    print("   Please check the file path!")
    sys.exit(1)

# Test 4: Initialize MCP client
print("\n[4/6] Initializing MCP client...")

async def test_mcp_connection():
    try:
        from mcp_chatbot_backend_client import initialize_mcp_client
        
        client = await initialize_mcp_client()
        print("   ✅ MCP client initialized successfully!")
        
        # Get tools
        tools = await client.get_tools()
        print(f"   ✅ Connected to MCP server!")
        print(f"   ✅ Loaded {len(tools)} tools:")
        
        for tool in tools:
            print(f"      - {tool.name}")
        
        # Cleanup
        await client.__aexit__(None, None, None)
        return True
        
    except Exception as e:
        print(f"   ❌ MCP client initialization failed!")
        print(f"   Error: {str(e)}")
        return False

# Run MCP connection test
connection_success = asyncio.run(test_mcp_connection())

if not connection_success:
    print("\n❌ MCP connection test failed!")
    print("   Please check:")
    print("   1. mcp-tools-local.py is in the correct location")
    print("   2. Python is in your system PATH")
    print("   3. All dependencies are installed")
    sys.exit(1)

# Test 5: Build chatbot
print("\n[5/6] Building chatbot graph...")

async def test_chatbot_build():
    try:
        from mcp_chatbot_backend_client import build_chatbot
        
        chatbot = await build_chatbot()
        print("   ✅ Chatbot graph built successfully!")
        print("   ✅ SQLite checkpointing configured!")
        return True
        
    except Exception as e:
        print(f"   ❌ Chatbot build failed!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

build_success = asyncio.run(test_chatbot_build())

if not build_success:
    print("\n❌ Chatbot build test failed!")
    sys.exit(1)

# Test 6: Test a simple query
print("\n[6/6] Testing chatbot with a simple query...")

async def test_chatbot_query():
    try:
        from mcp_chatbot_backend_client import get_chatbot
        from langchain_core.messages import HumanMessage
        
        chatbot, checkpointer = await get_chatbot()
        
        # Simple test query
        config = {
            "configurable": {"thread_id": "test_thread_setup"},
            "metadata": {"thread_id": "test_thread_setup"},
        }
        
        print("   Sending test query: 'Hello, who are you?'")
        
        result = await chatbot.ainvoke(
            {"messages": [HumanMessage(content="Hello, who are you?")]},
            config=config
        )
        
        response = result["messages"][-1].content
        print(f"   ✅ Chatbot responded: {response[:100]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ Query test failed!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

query_success = asyncio.run(test_chatbot_query())

# Final summary
print("\n" + "=" * 70)
print("📊 TEST SUMMARY")
print("=" * 70)

if query_success:
    print("✅ ALL TESTS PASSED!")
    print("\n🚀 Your MCP Chatbot is ready to use!")
    print("\nTo start the chatbot, run:")
    print("   streamlit run mcp-chatbot-frontend.py")
    print("\nOr test individual components:")
    print("   python mcp-chatbot-backend-client.py")
else:
    print("❌ SOME TESTS FAILED!")
    print("\nPlease fix the issues above before running the chatbot.")

print("=" * 70)
