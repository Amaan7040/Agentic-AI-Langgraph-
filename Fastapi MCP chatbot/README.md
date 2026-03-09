# ChatterBot - FastAPI MCP Chatbot

A professional AI chatbot powered by FastAPI, LangGraph, and Model Context Protocol (MCP) with a sleek dark-themed web interface.

## Features

- **Async MCP Integration** - Properly implements MCP client without deprecated context managers
- **WebSocket Streaming** - Real-time token streaming for responsive chat experience
- **Tool Call Visualization** - Shows which tools are being used during processing
- **Professional Dark UI** - Clean, aesthetic interface with smooth animations
- **Conversation History** - Persistent chat threads with SQLite storage
- **Multiple Tools** - Web search, stock prices, weather, astronomical data, and more

## Architecture

```
┌─────────────────────┐
│   HTML/CSS/JS       │
│   Frontend          │
└──────────┬──────────┘
           │ WebSocket/HTTP
           ▼
┌─────────────────────┐
│   FastAPI           │
│   Backend           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   LangGraph         │
│   (State Machine)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   MCP Client        │
└──────────┬──────────┘
           │ stdio
           ▼
┌─────────────────────┐
│   MCP Server        │
│   (FastMCP Tools)   │
└─────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd "C:\Users\khana\Downloads\Langgraph Agentic AI\Fastapi MCP chatbot"
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
WEATHER_API_KEY=your_weather_api_key_here
STOCK_API_KEY=your_stock_api_key_here
```

### 3. Run the Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open in Browser

Navigate to: `http://localhost:8000`

## API Endpoints

### REST API

- **GET /** - Serve HTML frontend
- **GET /api/threads** - Get all conversation threads
- **GET /api/thread/{thread_id}** - Get specific thread messages
- **POST /api/chat** - Send a chat message (HTTP fallback)
- **DELETE /api/thread/{thread_id}** - Delete a thread (not implemented)

### WebSocket

- **WS /ws/chat** - Real-time chat with streaming responses

## WebSocket Protocol

### Client → Server

```json
{
    "message": "What's the weather in Delhi?",
    "thread_id": "optional-thread-id"
}
```

### Server → Client

**Thread ID Assignment:**
```json
{
    "type": "thread_id",
    "thread_id": "uuid-here"
}
```

**Tool Call Notification:**
```json
{
    "type": "tool_call",
    "tool_name": "weather_updates_current",
    "args": {"q": "Delhi"}
}
```

**Streaming Tokens:**
```json
{
    "type": "token",
    "content": "The current "
}
```

**Completion:**
```json
{
    "type": "done"
}
```

**Error:**
```json
{
    "type": "error",
    "content": "Error message"
}
```

## MCP Tools Available

1. **DuckDuckGo Search** - Web search capability
2. **Stock Details** - Real-time stock prices (Alpha Vantage)
3. **URL Metadata** - Extract content from URLs
4. **Current Weather** - Live weather conditions
5. **Astronomical Updates** - Sunrise/sunset times
6. **Weather Forecast** - Multi-day weather predictions

## Frontend Features

### UI Components

- **Sidebar** - Conversation list and new chat button
- **Chat Area** - Message display with formatting
- **Input Area** - Multi-line input with auto-resize
- **Tool Indicators** - Shows active tool usage
- **Typing Animation** - Smooth loading states

### Message Formatting

The frontend automatically formats:
- **Bold text** with `**text**`
- Lists with `- item` or `* item`
- Line breaks and paragraphs
- Code blocks

### Keyboard Shortcuts

- `Enter` - Send message
- `Shift + Enter` - New line in input

## Configuration

### Change LLM Model

Edit `main.py`:

```python
llm_model = ChatGroq(model="llama-3.3-70b-versatile")  # Current
# llm_model = ChatGroq(model="llama-3.1-8b-instant")  # Faster
# llm_model = ChatGroq(model="mixtral-8x7b-32768")    # More capable
```

### Change MCP Server Path

Edit `main.py` line ~60:

```python
"args": [r"C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP\mcp-tools-local.py"],
```

### Customize UI Colors

Edit `index.html` CSS variables:

```css
:root {
    --bg-primary: #0f0f0f;
    --accent-primary: #8b5cf6;
    /* ... more variables ... */
}
```

## Technical Details

### MCP Client Implementation

Following langchain-mcp-adapters 0.1.0, the client is initialized **without** context manager:

```python
# CORRECT (0.1.0+)
_mcp_client = MultiServerMCPClient({...})
_tools = await _mcp_client.get_tools()

# DEPRECATED (throws error)
async with MultiServerMCPClient({...}) as client:
    tools = await client.get_tools()
```

### Async Flow

1. FastAPI receives request
2. Async invokes LangGraph chatbot
3. LangGraph calls MCP tools asynchronously
4. MCP server executes tool
5. Response streams back to client

### State Management

- **Frontend**: JavaScript manages UI state
- **Backend**: LangGraph manages conversation state
- **Database**: SQLite stores checkpoints

## Database

- **File**: `chatbot_fastapi_mcp.db`
- **Tables**: Auto-created by SqliteSaver
- **Checkpointing**: Every message turn saved
- **Thread Isolation**: Each conversation separate

## Troubleshooting

### "StructuredTool does not support sync invocation"

**Solution**: Already fixed! We use async throughout:
- MCP client: `await client.get_tools()`
- Chatbot: `await chatbot.ainvoke()`
- Streaming: `async for event in chatbot.astream_events()`

### WebSocket Connection Failed

**Cause**: Server not running or wrong port

**Solution**:
```bash
# Make sure server is running
python main.py

# Check if port 8000 is available
netstat -ano | findstr :8000
```

### MCP Tools Not Loading

**Cause**: MCP server path incorrect

**Solution**: Verify path in `main.py` points to `mcp-tools-local.py`

### CORS Errors

**Cause**: Running frontend from different origin

**Solution**: Already configured with `allow_origins=["*"]` in FastAPI

## Development

### Adding New Endpoints

```python
@app.post("/api/your-endpoint")
async def your_endpoint(data: YourModel):
    # Your logic here
    return {"result": "data"}
```

### Adding New Tools

Edit the MCP server file (`mcp-tools-local.py`):

```python
@mcp.tool()
def your_tool(param: str) -> dict:
    """Tool description"""
    # Implementation
    return {"result": "output"}
```

Tools are automatically loaded by the client!

### Testing API

Use curl or Postman:

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "thread_id": null}'

# Get threads
curl http://localhost:8000/api/threads
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t chatterbot-mcp .
docker run -p 8000:8000 --env-file .env chatterbot-mcp
```

### Environment Variables

For production, set:

```env
ENVIRONMENT=production
LOG_LEVEL=info
MAX_CONNECTIONS=100
```

## Performance Optimization

### Caching

Add Redis caching for frequent queries:

```python
import redis
cache = redis.Redis(host='localhost', port=6379)
```

### Rate Limiting

Add rate limiting middleware:

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(request: Request, ...):
    ...
```

### Connection Pooling

SQLite is single-threaded. For production, consider PostgreSQL:

```python
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver(connection_string)
```

## Security Considerations

1. **API Key Management** - Never commit .env file
2. **Input Validation** - FastAPI validates with Pydantic
3. **CORS** - Restrict origins in production
4. **Rate Limiting** - Implement per-user limits
5. **Authentication** - Add JWT or OAuth for production

## Monitoring

### Logging

FastAPI automatically logs requests. Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### LangSmith Integration

Already configured! Set in `.env`:

```env
LANGSMITH_API_KEY=your_key
LANGCHAIN_TRACING_V2=true
```

View traces at: https://smith.langchain.com

## License

MIT License - Free to use and modify

## Credits

- **FastAPI** - Web framework
- **LangGraph** - State machine for chat
- **LangChain** - Tool integration
- **FastMCP** - MCP server implementation
- **Groq** - LLM inference

## Support

For issues or questions:
1. Check troubleshooting section
2. Review FastAPI logs
3. Verify environment variables
4. Test with curl/Postman

## Changelog

### Version 1.0.0
- Initial release
- FastAPI backend with WebSocket streaming
- Professional dark-themed frontend
- MCP tool integration
- Conversation persistence
- Real-time tool usage indicators

---

**Built with ❤️ using FastAPI and Model Context Protocol**
