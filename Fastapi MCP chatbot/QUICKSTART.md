# ChatterBot MCP - Quick Start Guide

## Prerequisites

- Python 3.9 or higher
- pip package manager
- API keys (Groq, WeatherAPI, Alpha Vantage)

## Installation (5 minutes)

### Step 1: Navigate to Project

```bash
cd "C:\Users\khana\Downloads\Langgraph Agentic AI\Fastapi MCP chatbot"
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure API Keys

Copy the example environment file:

```bash
copy .env.example .env
```

Edit `.env` and add your API keys:

```env
GROQ_API_KEY=gsk_your_actual_key_here
WEATHER_API_KEY=your_weather_key_here
STOCK_API_KEY=your_stock_key_here
```

**Get API Keys:**
- Groq: https://console.groq.com/keys
- WeatherAPI: https://www.weatherapi.com/signup.aspx
- Alpha Vantage: https://www.alphavantage.co/support/#api-key

### Step 4: Verify Setup

```bash
python test_setup.py
```

Should show: `✓ ALL CHECKS PASSED!`

### Step 5: Start Server

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Manual:**
```bash
python main.py
```

### Step 6: Open in Browser

Navigate to: **http://localhost:8000**

## First Steps

1. **Start a chat** - Type "Hello" in the input box
2. **Try a tool** - Ask "What's the weather in London?"
3. **Watch the magic** - See tool usage indicators appear
4. **View history** - Previous chats appear in the sidebar

## Example Queries

### Weather
```
What's the current weather in Delhi?
Give me a 5-day forecast for Paris
When is sunrise in Tokyo tomorrow?
```

### Stocks
```
What's the current price of Apple stock?
Show me Tesla stock details
Get MSFT stock information
```

### Web Search
```
Search for latest AI news
Find information about Python 3.13
What's new with SpaceX?
```

### URL Analysis
```
Summarize https://www.example.com
Extract content from [any URL]
```

## Features to Explore

### Tool Usage Indicators
Watch as ChatterBot uses different tools:
- Yellow indicator appears
- Tool name shown (e.g., "Using tool: weather_updates_current")
- Result integrated into response

### Formatted Responses
ChatterBot formats responses with:
- **Bold text** for emphasis
- Bullet points for lists
- Proper paragraphs

### Conversation History
- All chats saved automatically
- Click any chat in sidebar to reload
- Start fresh with "New Chat" button

## Troubleshooting

### Server won't start

**Check:**
1. `.env` file exists with API keys
2. Port 8000 is available
3. All packages installed

**Solution:**
```bash
python test_setup.py
```

### Tools not working

**Error:** "StructuredTool does not support sync invocation"

**Solution:** Already fixed! We use async throughout.

**Error:** "MCP client initialization failed"

**Check:** MCP server path in `main.py` line ~60

### Can't connect to server

**Check:** Server is running on port 8000

**Verify:**
```bash
netstat -ano | findstr :8000
```

## Customization

### Change Port

Edit `main.py` last line:

```python
uvicorn.run(app, host="0.0.0.0", port=8080)  # Change 8000 to 8080
```

### Change UI Colors

Edit `index.html` CSS variables (around line 15):

```css
--accent-primary: #8b5cf6;  /* Purple accent */
--bg-primary: #0f0f0f;      /* Background color */
```

### Change LLM Model

Edit `main.py` line ~25:

```python
llm_model = ChatGroq(model="llama-3.1-8b-instant")  # Faster
```

## Project Structure

```
Fastapi MCP chatbot/
├── main.py              # FastAPI backend
├── index.html           # Frontend UI
├── requirements.txt     # Dependencies
├── .env                 # Your API keys
├── .env.example         # Template
├── test_setup.py        # Verification script
├── start.bat            # Windows launcher
├── start.sh             # Linux/Mac launcher
└── README.md            # Full documentation
```

## Next Steps

1. ✅ Test with different queries
2. ✅ Explore all available tools
3. ✅ Check conversation history
4. ✅ Try the WebSocket streaming
5. ✅ Read full README.md for advanced features

## Advanced Usage

### API Testing

Test the REST API directly:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "thread_id": null}'
```

### View All Threads

```bash
curl http://localhost:8000/api/threads
```

### Development Mode

Run with auto-reload:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Performance Tips

1. **First query slower** - MCP client initializes
2. **Subsequent queries faster** - Tools cached
3. **WebSocket preferred** - Better than HTTP for streaming
4. **Multiple tabs** - Each gets own WebSocket

## Support

**Issues?**

1. Run `python test_setup.py`
2. Check server logs in terminal
3. Verify API keys in `.env`
4. Review `README.md` troubleshooting section

## What Makes This Special?

✅ **No Streamlit** - Pure FastAPI + HTML/CSS/JS
✅ **Async throughout** - Proper async/await
✅ **No context manager error** - Fixed MCP client usage
✅ **Professional UI** - Dark theme, smooth animations
✅ **Tool visibility** - See what's happening
✅ **WebSocket streaming** - Real-time responses
✅ **Production-ready** - FastAPI best practices

## Learning Resources

- FastAPI: https://fastapi.tiangolo.com/
- LangGraph: https://langchain-ai.github.io/langgraph/
- MCP: https://github.com/anthropics/langchain-mcp-adapters
- WebSockets: https://websockets.readthedocs.io/

---

**Ready to chat? Start the server and open http://localhost:8000!**
