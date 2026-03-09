# 🚀 Quick Start Guide - MCP Chatbot

## Prerequisites

Make sure you have:
- Python 3.9 or higher
- pip package manager
- Required API keys (Groq, WeatherAPI, Alpha Vantage)

## Step-by-Step Setup

### 1️⃣ Install Dependencies

Open terminal/command prompt and run:

```bash
pip install langgraph langchain-groq langchain-community langchain-core
pip install fastmcp langchain-mcp-adapters
pip install streamlit python-dotenv requests langsmith
```

### 2️⃣ Configure Environment Variables

Create a file named `.env` in the `Chatbot MCP` folder:

```env
GROQ_API_KEY=your_groq_api_key_here
STOCK_API_KEY=your_alphavantage_api_key_here
WEATHER_API_KEY=your_weatherapi_key_here
```

**How to get API keys:**
- **Groq**: https://console.groq.com/ (Free)
- **WeatherAPI**: https://www.weatherapi.com/ (Free tier available)
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key (Free)

### 3️⃣ Test Your Setup

```bash
cd "C:\Users\khana\Downloads\Langgraph Agentic AI\Chatbot MCP"
python test_setup.py
```

This will verify:
- ✅ All packages installed
- ✅ Environment variables configured
- ✅ MCP server accessible
- ✅ Chatbot builds correctly
- ✅ Query works

### 4️⃣ Run the Chatbot

```bash
streamlit run mcp-chatbot-frontend.py
```

Your browser will open automatically at `http://localhost:8501`

## 🎯 First Steps in the UI

1. **Start chatting** - Type a message in the input box
2. **Try different tools**:
   - "What's the weather in Delhi?"
   - "Search for latest AI news"
   - "What's Apple's stock price?"
3. **Create new chats** - Click "✨ New Chat +" button
4. **View history** - Previous conversations appear in sidebar

## 💡 Example Queries

### Weather Queries
```
- What's the current weather in London?
- Give me a 7-day forecast for New York
- What time is sunrise in Tokyo tomorrow?
```

### Stock Queries
```
- What's the price of TSLA stock?
- Show me Apple stock details
- Current price of Microsoft shares
```

### Web Search
```
- Search for latest SpaceX news
- Find information about Python 3.13
- Latest developments in AI
```

### URL Analysis
```
- Summarize https://www.example.com
- Extract content from [any URL]
```

## 🔧 Troubleshooting

### Problem: "Module not found" error
**Solution**: Reinstall packages
```bash
pip install --upgrade langgraph langchain-groq streamlit
```

### Problem: "MCP connection failed"
**Solution**: Check file paths in `mcp-chatbot-backend-client.py`
- Line 32: Verify MCP server path is correct

### Problem: "API key not configured"
**Solution**: Check your `.env` file
- Make sure there are no quotes around the API keys
- File should be in the same folder as the Python files

### Problem: "Chatbot is slow"
**Solution**: 
- First query takes longer (initializing MCP connection)
- Subsequent queries are faster
- Consider using a faster model in backend

## 📁 File Structure

```
Chatbot MCP/
├── .env                              # Your API keys (create this)
├── mcp-tools-local.py                # MCP Server with tools
├── mcp-chatbot-backend-client.py     # Backend (LangGraph + MCP)
├── mcp-chatbot-frontend.py           # Streamlit UI
├── test_setup.py                     # Setup verification script
├── README.md                         # Full documentation
├── QUICKSTART.md                     # This file
└── chatbot_mcp.db                    # Database (auto-created)
```

## 🎨 Customizing

### Change the Model

Edit `mcp-chatbot-backend-client.py`, line 13:

```python
# Faster, less capable
llm_model = ChatGroq(model="llama-3.1-8b-instant")

# Original (balanced)
llm_model = ChatGroq(model="llama-3.3-70b-versatile")

# More capable, slower
llm_model = ChatGroq(model="mixtral-8x7b-32768")
```

### Add More Tools

Edit `mcp-tools-local.py` and add:

```python
@mcp.tool()
def my_custom_tool(input: str) -> dict:
    """Description of what this tool does"""
    # Your code here
    return {"result": "output"}
```

The tool will automatically be available in the chatbot!

## ✅ Verification Checklist

Before reporting issues, verify:

- [ ] Python 3.9+ installed
- [ ] All pip packages installed
- [ ] `.env` file created with API keys
- [ ] `test_setup.py` passes all tests
- [ ] MCP server path is correct
- [ ] No other Python processes using port 8501

## 🆘 Getting Help

If you encounter issues:

1. Run `python test_setup.py` - it will tell you what's wrong
2. Check the console output for error messages
3. Verify all file paths are correct
4. Make sure API keys are valid

## 🎉 Success!

If everything works, you should see:
- Streamlit UI opens in browser
- Sidebar shows "ChatterBot MCP"
- You can type messages and get responses
- Tools are called automatically when needed
- Conversation history is saved

**Enjoy your MCP-powered chatbot!** 🤖✨

---

Need more details? Check `README.md` for complete documentation.
