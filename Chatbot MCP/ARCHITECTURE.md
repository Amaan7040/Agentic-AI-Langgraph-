# MCP Chatbot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Streamlit Frontend                          │  │
│  │      (mcp-chatbot-frontend.py)                       │  │
│  │                                                       │  │
│  │  Features:                                           │  │
│  │  • Chat interface                                    │  │
│  │  • Message history                                   │  │
│  │  • Thread management                                 │  │
│  │  • Auto-naming                                       │  │
│  │  • Sidebar navigation                                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ imports & calls
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND CLIENT                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         LangGraph Agent                              │  │
│  │     (mcp_chatbot_backend_client.py)                  │  │
│  │                                                       │  │
│  │  Components:                                         │  │
│  │  • ChatGroq LLM (llama-3.3-70b)                     │  │
│  │  • StateGraph (conversation flow)                   │  │
│  │  • ToolNode (tool execution)                        │  │
│  │  • SqliteSaver (checkpointing)                      │  │
│  │  • Async/await handling                             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ async calls
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP CLIENT LAYER                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      MultiServerMCPClient                            │  │
│  │                                                       │  │
│  │  Functions:                                          │  │
│  │  • Connect to MCP servers                           │  │
│  │  • Fetch available tools                            │  │
│  │  • Manage tool lifecycle                            │  │
│  │  • Handle stdio communication                       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ stdio transport
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP SERVER                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           FastMCP Server                             │  │
│  │        (mcp-tools-local.py)                          │  │
│  │                                                       │  │
│  │  Tools Available:                                    │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 1. 🔍 search_info()                           │ │  │
│  │  │    • DuckDuckGo web search                    │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 2. 📈 stock_details()                         │ │  │
│  │  │    • Alpha Vantage API                        │ │  │
│  │  │    • Real-time stock prices                   │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 3. 🌐 url_metadata()                          │ │  │
│  │  │    • Jina AI reader                           │ │  │
│  │  │    • Webpage content extraction               │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 4. 🌤️ weather_updates_current()              │ │  │
│  │  │    • WeatherAPI current conditions            │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 5. 🌙 astronomical_updates()                  │ │  │
│  │  │    • Sunrise/sunset times                     │ │  │
│  │  │    • Moon phases                              │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 6. 📅 forecast_update()                       │ │  │
│  │  │    • Multi-day weather forecasts              │ │  │
│  │  │    • Up to 7 days                             │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ API calls
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL SERVICES                          │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Groq API  │  │ Alpha Vantage│  │ WeatherAPI   │      │
│  │             │  │              │  │              │      │
│  │ LLM Model   │  │ Stock Data   │  │ Weather Data │      │
│  └─────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ DuckDuckGo  │  │   Jina AI    │  │  LangSmith   │      │
│  │             │  │              │  │              │      │
│  │ Web Search  │  │ URL Reader   │  │   Tracing    │      │
│  └─────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  DATA PERSISTENCE                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SQLite Database                         │  │
│  │           (chatbot_mcp.db)                           │  │
│  │                                                       │  │
│  │  Stores:                                             │  │
│  │  • Conversation threads                              │  │
│  │  • Message history                                   │  │
│  │  • Checkpoints                                       │  │
│  │  • Thread metadata                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════

COMMUNICATION FLOW:

1. User Input → Frontend
2. Frontend → Backend (via get_chatbot())
3. Backend → MCP Client (get_tools())
4. MCP Client → MCP Server (stdio)
5. MCP Server → External APIs
6. Response: External APIs → MCP Server → MCP Client → Backend
7. Backend → SQLite (save state)
8. Backend → Frontend (stream response)
9. Frontend → User (display)

════════════════════════════════════════════════════════════════

KEY TECHNOLOGIES:

• LangGraph: Agent orchestration & workflow
• FastMCP: Model Context Protocol server
• Streamlit: Web-based UI
• LangChain: LLM integration & tool calling
• Groq: Fast LLM inference
• SQLite: Local data persistence
• Async/Await: Non-blocking operations

════════════════════════════════════════════════════════════════
