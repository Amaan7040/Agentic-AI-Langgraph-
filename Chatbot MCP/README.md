# MCP Chatbot - Setup and Usage Guide

## 📁 Project Structure

```
Chatbot MCP/
├── mcp-tools-local.py              # MCP Server (FastMCP) - Contains all tools
├── mcp-chatbot-backend-client.py   # MCP Client Backend (LangGraph + MCP)
└── mcp-chatbot-frontend.py         # Streamlit UI
```

## 🔧 Setup Instructions

### 1. Install Required Packages

```bash
pip install langgraph langchain-groq langchain-community langchain-core
pip install fastmcp langchain-mcp-adapters
pip install streamlit python-dotenv requests langsmith
```

### 2. Set Up Environment Variables

Create a `.env` file in the `Chatbot MCP` folder:

```env
GROQ_API_KEY=your_groq_api_key_here
STOCK_API_KEY=your_alphavantage_api_key_here
WEATHER_API_KEY=your_weatherapi_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here  # Optional
```

## 🚀 How to Run

### Method 1: Run Frontend (Recommended)

The frontend will automatically initialize the backend and MCP connection:

```bash
cd "C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP"
streamlit run mcp-chatbot-frontend.py
```

### Method 2: Test Backend Only

```bash
cd "C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP"
python mcp-chatbot-backend-client.py
```

## 🏗️ Architecture

### Flow Diagram:
```
┌─────────────────────┐
│  Streamlit UI       │
│  (Frontend)         │
└──────────┬──────────┘
           │
           │ imports & calls
           ▼
┌─────────────────────┐
│  MCP Backend Client │
│  (LangGraph Graph)  │
└──────────┬──────────┘
           │
           │ stdio connection
           ▼
┌─────────────────────┐
│  MCP Server         │
│  (FastMCP Tools)    │
└─────────────────────┘
```

### Components:

1. **MCP Server** (`mcp-tools-local.py`)
   - Runs as a subprocess via stdio
   - Contains 6 tools:
     * DuckDuckGo Search
     * Stock Details (Alpha Vantage)
     * URL Metadata Extraction
     * Current Weather
     * Astronomical Data
     * Weather Forecast

2. **MCP Backend Client** (`mcp-chatbot-backend-client.py`)
   - Initializes MCP client
   - Connects to MCP server
   - Builds LangGraph with MCP tools
   - Manages SQLite checkpointing
   - Exports `chatbot` and `checkpointer`

3. **Frontend** (`mcp-chatbot-frontend.py`)
   - Streamlit UI
   - Imports chatbot from backend
   - Manages conversation history
   - Streaming responses
   - Chat name generation

## 🛠️ Available MCP Tools

| Tool | Function | Example Query |
|------|----------|---------------|
| 🔍 Web Search | `search_info()` | "Search for latest AI news" |
| 📈 Stock Details | `stock_details()` | "What's the price of AAPL?" |
| 🌐 URL Metadata | `url_metadata()` | "Summarize https://example.com" |
| 🌤️ Current Weather | `weather_updates_current()` | "What's the weather in Delhi?" |
| 🌙 Astronomical | `astronomical_updates()` | "Sunrise time in Mumbai on 2024-12-25" |
| 📅 Forecast | `forecast_update()` | "7-day forecast for New York" |

## 💾 Database

- **File**: `chatbot_mcp.db` (created automatically)
- **Purpose**: Stores conversation history
- **Checkpointing**: Enabled for all conversations
- **Thread Management**: Each conversation has a unique thread_id

## 🎯 Key Features

✅ **Async/Await** - Proper async implementation for MCP
✅ **Dynamic Queries** - User types queries at runtime (no hardcoded queries)
✅ **Conversation History** - Persisted in SQLite
✅ **Chat Names** - Auto-generated based on first message
✅ **Streaming Responses** - Real-time token streaming
✅ **Tool Calling** - Automatic tool selection by LLM
✅ **Multi-threading** - Separate conversation threads
✅ **LangSmith Tracing** - Optional observability

## 🔍 How It Works

1. **User sends a message** in Streamlit UI
2. **Frontend** passes message to backend chatbot
3. **LLM analyzes** the message and decides if tools are needed
4. **If tools needed**:
   - LLM generates tool call
   - Backend sends request to MCP server via stdio
   - MCP server executes the tool
   - Result returns to LLM
5. **LLM generates** final response with tool results
6. **Response streams** back to UI
7. **Conversation saved** in SQLite database

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'mcp_chatbot_backend_client'"

**Solution**: Make sure the file is named exactly `mcp-chatbot-backend-client.py` (with hyphens)

### Issue: "MCP client connection timeout"

**Solution**: 
- Check that `mcp-tools-local.py` path is correct
- Ensure Python is in PATH
- Try using full Python path: `C:\\Python311\\python.exe`

### Issue: "WEATHER_API_KEY not configured"

**Solution**: Add all API keys to `.env` file

### Issue: Database locked error

**Solution**: Close all running instances and delete `chatbot_mcp.db`, it will be recreated

## 📝 Testing Queries

Try these queries to test different tools:

```
1. "Search for latest news about SpaceX"
2. "What's the current stock price of Tesla?"
3. "What's the weather in London right now?"
4. "Give me a 5-day weather forecast for Paris"
5. "What time is sunrise in Tokyo on 2024-12-31?"
6. "Summarize this URL: https://www.anthropic.com"
```

## 🎨 Customization

### Add More Tools

Edit `mcp-tools-local.py` and add:

```python
@mcp.tool()
def your_new_tool(param: str) -> dict:
    """Tool description"""
    # Your implementation
    return {"result": "data"}
```

### Change LLM Model

Edit `mcp-chatbot-backend-client.py`:

```python
llm_model = ChatGroq(model="llama-3.1-8b-instant")  # Faster, less capable
# or
llm_model = ChatGroq(model="mixtral-8x7b-32768")   # More capable
```

## 📊 LangSmith Integration

To enable tracing:

1. Set environment variables:
```env
LANGSMITH_API_KEY=your_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=mcp-chatbot
```

2. View traces at: https://smith.langchain.com/

## ✨ Differences from Original Chatbot

| Feature | Original | MCP Version |
|---------|----------|-------------|
| Tools | Defined in backend | Defined in MCP server |
| Connection | Direct function calls | stdio MCP protocol |
| Async | Synchronous | Async/Await |
| Database | `chatbot.db` | `chatbot_mcp.db` |
| Tool Management | Manual binding | MCP client auto-fetch |

## 🚀 Production Deployment

For production use:

1. Use environment-based MCP server path
2. Implement proper error handling
3. Add authentication to Streamlit
4. Use production database (PostgreSQL)
5. Enable LangSmith monitoring
6. Add rate limiting
7. Implement caching for API calls

## 📚 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Anthropic MCP Adapters](https://github.com/anthropics/langchain-mcp-adapters)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

**Created**: 2024
**Version**: 1.0
**License**: MIT
