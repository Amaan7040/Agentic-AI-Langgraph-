from langgraph.graph import StateGraph, START, END # pyright: ignore[reportMissingImports]
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # pyright: ignore[reportMissingImports]
from langchain_groq.chat_models import ChatGroq # pyright: ignore[reportMissingImports]
from langgraph.checkpoint.sqlite import SqliteSaver # pyright: ignore[reportMissingImports]
from langgraph.graph.message import add_messages # pyright: ignore[reportMissingImports]
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from langchain_mcp_adapters.client import MultiServerMCPClient
import sqlite3
import os
import asyncio

load_dotenv()

llm_model = ChatGroq(model="llama-3.3-70b-versatile")

# Initialize the model for chat name generation
model = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# Global variables to store chatbot components
_mcp_client = None
_chatbot = None
_checkpointer = None
_connection = None

async def initialize_mcp_client():
    """Initialize and return the MCP client with proper async context"""
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MultiServerMCPClient(
            {
                "chatterbot_tools": {
                    "transport": "stdio",
                    "command": "python",          
                    "args": [r"C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP\mcp-tools-local.py"],
                }
            }
        )
        
        # Enter the client context
        await _mcp_client.__aenter__()
        print("MCP client initialized and connected to server.")
    
    return _mcp_client

async def build_chatbot():
    """Build and return the chatbot with MCP tools - matches chatbot_tool_backend.py structure"""
    global _chatbot, _checkpointer, _connection
    
    # Initialize MCP client
    client = await initialize_mcp_client()
    
    # Get tools from MCP server
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} MCP tools: {[tool.name for tool in tools]}")
    
    # Bind tools to the LLM
    chatbot_with_tools = llm_model.bind_tools(tools)
    
    # Define the chat node - keeps sync to match original structure
    def chat_node(state: ChatState):
        messages = state['messages']
        response = chatbot_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Setup SQLite connection and checkpointer
    _connection = sqlite3.connect("chatbot_mcp.db", check_same_thread=False)
    _checkpointer = SqliteSaver(conn=_connection)
    
    # Create tool node
    tool_node = ToolNode(tools)
    
    # Build the graph - exact same structure as chatbot_tool_backend.py
    graph = StateGraph(ChatState)
    
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    
    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
    
    # Compile the graph with checkpointer
    _chatbot = graph.compile(checkpointer=_checkpointer)
    print("Chatbot backend is ready with MCP tools.")
    
    return _chatbot

def retrieve_chats():
    """Extract all the chat threads stored in the database - matches original function"""
    global _checkpointer
    
    if _checkpointer is None:
        return []
    
    all_chats = set()
    
    for chats_checkpoints in _checkpointer.list(None):
        all_chats.add(chats_checkpoints.config['configurable']['thread_id'])
    
    return list(all_chats)

async def get_chatbot():
    """
    Get or create the chatbot instance.
    This function can be imported by the frontend (Streamlit)
    Returns: (chatbot, checkpointer) tuple
    """
    global _chatbot, _checkpointer
    
    if _chatbot is None:
        await build_chatbot()
    
    return _chatbot, _checkpointer

# Initialize the chatbot when module is imported (for direct usage like chatbot_tool_backend.py)
async def _init_module():
    """Initialize the module-level chatbot instance"""
    global chatbot, checkpointer
    chatbot, checkpointer = await get_chatbot()

# Create event loop and initialize
def _sync_init():
    """Synchronous wrapper for initialization"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If loop is already running (e.g., in Streamlit), schedule the init
        asyncio.create_task(_init_module())
    else:
        # Otherwise, run it directly
        loop.run_until_complete(_init_module())

# Module-level variables (matching chatbot_tool_backend.py)
chatbot = None
checkpointer = None

# Only initialize if running as main module
if __name__ == '__main__':
    print("Initializing MCP Chatbot Backend...")
    asyncio.run(_init_module())
    print("\nChatbot is ready! You can now run the frontend.")
    print("Use: streamlit run mcp-chatbot-frontend.py")
else:
    # When imported, try to initialize (for Streamlit compatibility)
    try:
        _sync_init()
    except Exception as e:
        print(f"Note: Chatbot will be initialized on first use. ({e})")
