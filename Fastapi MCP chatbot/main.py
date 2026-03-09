from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_groq.chat_models import ChatGroq
from dotenv import load_dotenv
from typing_extensions import TypedDict, Annotated
import aiosqlite
import os
import uuid
import json
import asyncio

load_dotenv()

app = FastAPI(title="ChatterBot MCP API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM
llm_model = ChatGroq(model="llama-3.3-70b-versatile")

# Chat state definition
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

# Global variables
_mcp_client = None
_chatbot = None
_checkpointer = None
_connection = None
_tools = None

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    tool_calls: List[Dict[str, Any]] = []

class ThreadResponse(BaseModel):
    thread_id: str
    messages: List[Dict[str, str]]

async def initialize_mcp_client():
    """Initialize MCP client without context manager - per langchain-mcp-adapters 0.1.0"""
    global _mcp_client, _tools
    
    if _mcp_client is None:
        _mcp_client = MultiServerMCPClient(
            {
                "chatterbot_tools": {
                    "transport": "stdio",
                    "command": "python",
                    "args": [r"C:/Users/khana/Downloads/Langgraph Agentic AI/Chatbot MCP/mcp-tools-local.py"],
                }
            }
        )
        
        # Get tools directly without context manager
        _tools = await _mcp_client.get_tools()
        print(f"MCP client initialized with {len(_tools)} tools")
        
    return _mcp_client, _tools

async def build_chatbot():
    """Build the chatbot graph with MCP tools"""
    global _chatbot, _checkpointer, _connection
    
    if _chatbot is not None:
        return _chatbot
    
    # Initialize MCP client and get tools
    client, tools = await initialize_mcp_client()
    
    print(f"Building chatbot with tools: {[tool.name for tool in tools]}")
    
    # Bind tools to LLM
    chatbot_with_tools = llm_model.bind_tools(tools)
    
    # Define chat node
    async def chat_node(state: ChatState):
        messages = state['messages']
        response = await chatbot_with_tools.ainvoke(messages)
        return {"messages": [response]}
    
    # Setup SQLite
    _connection = await aiosqlite.connect("chatbot_fastapi_mcp.db")
    _checkpointer = AsyncSqliteSaver(_connection)
    
    # Create tool node
    tool_node = ToolNode(tools)
    
    # Build graph
    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    
    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
    
    _chatbot = graph.compile(checkpointer=_checkpointer)
    print("Chatbot compiled successfully!")
    
    return _chatbot

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize chatbot on startup"""
    print("Starting ChatterBot MCP API...")
    await build_chatbot()
    print("ChatterBot MCP API ready!")

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("index.html")

@app.get("/api/threads")
async def get_threads():
    """Get all conversation threads"""
    if _checkpointer is None:
        return {"threads": []}

    try:
        all_threads = set()

        async for checkpoint in _checkpointer.alist(None):
            thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
            if thread_id:
                all_threads.add(thread_id)

        return {"threads": list(all_threads)}

    except Exception as e:
        print(f"Error fetching threads: {e}")
        return {"threads": []}


@app.get("/api/thread/{thread_id}")
async def get_thread(thread_id: str):
    """Get messages from a specific thread"""
    if _chatbot is None:
        raise HTTPException(status_code=500, detail="Chatbot not initialized")
    
    try:
        state = _chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        messages = state.values.get('messages', [])
        
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
        
        return {"thread_id": thread_id, "messages": formatted_messages}
    except Exception as e:
        return {"thread_id": thread_id, "messages": []}

@app.post("/api/chat")
async def chat(chat_message: ChatMessage):
    """Process a chat message and return response"""
    if _chatbot is None:
        raise HTTPException(status_code=500, detail="Chatbot not initialized")
    
    # Generate thread_id if not provided
    thread_id = chat_message.thread_id or str(uuid.uuid4())
    
    config = {
        'configurable': {'thread_id': thread_id},
        'metadata': {'thread_id': thread_id}
    }
    
    # Invoke chatbot
    result = await _chatbot.ainvoke(
        {'messages': [HumanMessage(content=chat_message.message)]},
        config=config
    )
    
    # Extract response and tool calls
    response_message = result['messages'][-1]
    response_text = response_message.content
    
    # Extract tool calls from message history
    tool_calls = []
    for msg in result['messages']:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_calls.append({
                    "name": tool_call.get('name', 'Unknown'),
                    "args": tool_call.get('args', {})
                })
    
    return {
        "response": response_text,
        "thread_id": thread_id,
        "tool_calls": tool_calls
    }

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses"""
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message = message_data.get("message")
            thread_id = message_data.get("thread_id", str(uuid.uuid4()))

            if _chatbot is None:
                await websocket.send_json({
                    "type": "error",
                    "content": "Chatbot not initialized"
                })
                continue

            config = {
                "configurable": {"thread_id": thread_id},
                "metadata": {"thread_id": thread_id}
            }

            # Send thread_id to frontend
            await websocket.send_json({
                "type": "thread_id",
                "thread_id": thread_id
            })

            tool_calls_seen = set()
            final_answer_sent = False

            # 🔥 STREAM EVENTS
            async for event in _chatbot.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                version="v2"
            ):
                event_type = event.get("event", "")
                data = event.get("data", {})

                # --------------------------------------------------
                # 1️⃣ STREAMING TOKENS
                # --------------------------------------------------
                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        await websocket.send_json({
                            "type": "token",
                            "content": chunk.content
                        })
                        final_answer_sent = True

                # --------------------------------------------------
                # 2️⃣ TOOL CALL DETECTION
                # --------------------------------------------------
                elif event_type == "on_chat_model_end":
                    output = data.get("output")

                    # Tool calls
                    if output and hasattr(output, "tool_calls") and output.tool_calls:
                        for tool_call in output.tool_calls:
                            tool_name = tool_call.get("name", "Unknown Tool")
                            if tool_name not in tool_calls_seen:
                                tool_calls_seen.add(tool_name)

                                await websocket.send_json({
                                    "type": "tool_call",
                                    "tool_name": tool_name,
                                    "args": tool_call.get("args", {})
                                })

                    # --------------------------------------------------
                    # 3️⃣ FINAL RESPONSE (Non-stream fallback)
                    # --------------------------------------------------
                    if output and hasattr(output, "content") and output.content:
                        # If streaming didn't send content
                        if not final_answer_sent:
                            await websocket.send_json({
                                "type": "final",
                                "content": output.content
                            })

            # Completion signal
            await websocket.send_json({
                "type": "done"
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")

    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })
        except:
            pass

@app.delete("/api/thread/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a conversation thread"""
    # Note: SqliteSaver doesn't have built-in delete, would need custom implementation
    return {"message": "Thread deletion not implemented yet"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)