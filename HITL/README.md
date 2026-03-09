# 🤖 Chatterbot — LangGraph HITL Agentic AI

A multi-tool agentic chatbot built with **LangGraph**, **LangChain**, and **Streamlit** that supports **Human-in-the-Loop (HITL)** email approval, real-time data retrieval, PDF document chat, and more.

---

## 📁 Project Structure

```
HITL/
├── HITL_backend.py       # Agent graph, tool definitions, state, checkpointing
├── HITL_frontend.py      # Streamlit UI with HITL interrupt handling
├── chatbot.db            # SQLite database for LangGraph checkpointing
└── .env                  # Environment variables (API keys, SMTP config)
```

---

## ⚙️ Architecture Overview

The system is built on a **LangGraph StateGraph** with the following flow:

```
START → chat_node → [tools_condition] → tools → chat_node → END
```

- **`chat_node`**: The central LLM node (Llama 3.3 70B via Groq). Handles regular responses, HITL email approval logic, and tool invocations.
- **`tools`**: A `ToolNode` that executes all registered tools.
- **Checkpointing**: SQLite-backed via `SqliteSaver` for persistent multi-turn memory per thread.
- **HITL**: Implemented using LangGraph's `interrupt()` mechanism. Email sending is paused until the user explicitly approves, denies, or requests modification via the Streamlit UI.

---

## 🛠️ Agent Tools

### 1. 🔍 Web Search — `search_info`

| Property | Details |
|----------|---------|
| **Function** | `search_info(query: str)` |
| **Library** | `langchain_community.tools.DuckDuckGoSearchRun` |
| **Traced** | Yes (`@traceable(name="WebSearch")`) |

**Description:**  
Searches the internet for current or real-time information using DuckDuckGo. Returns up to 6,000 characters of search results.

**When it's triggered:**
- "What are the latest news about...?"
- "Search for current information on..."
- "What's happening with...?"
- Any query requiring up-to-date or live web data

**Example usage:**
```
User: "What are the latest developments in AI?"
→ Agent calls search_info("latest AI developments 2024")
```

---

### 2. 📈 Stock Details — `stock_details`

| Property | Details |
|----------|---------|
| **Function** | `stock_details(symbol: str)` |
| **API** | Alpha Vantage (`GLOBAL_QUOTE` endpoint) |
| **Env Variable** | `STOCK_API_KEY` |
| **Traced** | Yes (`@traceable(name="StockDetails")`) |

**Description:**  
Fetches real-time stock market data for a given ticker symbol. Returns price, change, percentage change, volume, and the latest trading day.

**When it's triggered:**
- "What is the current price of Apple stock?"
- "Show me TSLA stock performance today"
- "What's the share price of INFY?"
- Any query with stock ticker references or financial market data

**Input:** A valid stock symbol (e.g., `AAPL`, `TSLA`, `MSFT`, `RELIANCE`)

**Returns:**
```json
{
  "symbol": "AAPL",
  "price": "189.30",
  "change": "+1.50",
  "change_percent": "+0.80%",
  "volume": "52340000",
  "latest_trading_day": "2024-01-15"
}
```

---

### 3. 🌐 URL Metadata — `url_metadata`

| Property | Details |
|----------|---------|
| **Function** | `url_metadata(url: str)` |
| **API** | Jina AI Reader (`https://r.jina.ai/`) |
| **Traced** | Yes (`@traceable(name="UrlInfo")`) |

**Description:**  
Fetches and extracts clean, readable text content from any webpage URL using Jina AI's reader service. Returns up to 6,000 characters of extracted text.

**When it's triggered:**
- "Summarize this article: https://..."
- "What does this webpage say: https://..."
- "Extract key points from this URL"
- Any prompt containing a valid `http://` or `https://` URL

**Input:** A complete URL starting with `http` or `https`

**Example usage:**
```
User: "Summarize https://example.com/article"
→ Agent calls url_metadata("https://example.com/article")
```

---

### 4. 🌤️ Current Weather — `weather_updates_current`

| Property | Details |
|----------|---------|
| **Function** | `weather_updates_current(q: str)` |
| **API** | WeatherAPI (`/v1/current.json`) |
| **Env Variable** | `WEATHER_API_KEY` |
| **Traced** | Yes (`@traceable(name="CurrentWeather")`) |

**Description:**  
Retrieves live/current weather conditions for any city or location using the WeatherAPI service.

**When it's triggered:**
- "What's the weather in Delhi right now?"
- "Current temperature in London"
- "What are the live weather conditions in New York?"
- "Is it raining in Mumbai today?"

**Input:** A city name, region, or location (e.g., `Delhi`, `New York`, `London`)

**Returns:**
```json
{
  "location": "Delhi, Delhi, India",
  "temperature_c": 28.0,
  "temperature_f": 82.4,
  "condition": "Partly cloudy",
  "humidity": 65,
  "wind_kph": 15.0,
  "wind_dir": "NW",
  "feelslike_c": 30.2,
  "visibility_km": 10.0,
  "last_updated": "2024-01-15 14:30"
}
```

---

### 5. 🌙 Astronomical Updates — `astronomical_updates`

| Property | Details |
|----------|---------|
| **Function** | `astronomical_updates(q: str, dt: str)` |
| **API** | WeatherAPI (`/v1/astronomy.json`) |
| **Env Variable** | `WEATHER_API_KEY` |
| **Traced** | Yes (`@traceable(name="AstronomicalUpdates")`) |

**Description:**  
Fetches astronomical data for a given location and date including sunrise, sunset, moonrise, moonset, moon phase, and moon illumination percentage.

**When it's triggered:**
- "What time is sunset in Paris tomorrow?"
- "What is the moon phase in Tokyo on 2024-02-01?"
- "Tell me sunrise and moonrise time for Delhi today"
- Any query about astronomical events for a specific date

**Input:**
- `q`: Location name (e.g., `Mumbai`, `Paris`)
- `dt`: Date in `YYYY-MM-DD` format

**Returns:**
```json
{
  "location": "Mumbai, Maharashtra, India",
  "date": "2024-01-15",
  "sunrise": "07:12 AM",
  "sunset": "06:28 PM",
  "moonrise": "09:45 AM",
  "moonset": "08:32 PM",
  "moon_phase": "Waxing Crescent",
  "moon_illumination": "23"
}
```

---

### 6. 🌦️ Weather Forecast — `forecast_update`

| Property | Details |
|----------|---------|
| **Function** | `forecast_update(q: str, days: str)` |
| **API** | WeatherAPI (`/v1/forecast.json`) |
| **Env Variable** | `WEATHER_API_KEY` |
| **Traced** | Yes (`@traceable(name="ForecastWeather")`) |

**Description:**  
Retrieves a multi-day weather forecast (1–7 days) for a given location. Includes daily temperature ranges, rain chance, wind speed, humidity, UV index, and sunrise/sunset times.

**When it's triggered:**
- "What's the weather forecast for London for the next 5 days?"
- "Will it rain in Bangalore this week?"
- "Give me a 3-day forecast for Dubai"
- Any query asking about upcoming/future weather conditions

**Input:**
- `q`: City or location name
- `days`: Number of forecast days as a string (`"1"` to `"7"`)

**Returns:** A structured JSON object with per-day forecast including temperature min/max/avg, condition, rain chance percentage, wind speed, humidity, UV index, sunrise, and sunset.

---

### 7. 📄 RAG (Document Q&A) — `rag`

| Property | Details |
|----------|---------|
| **Function** | `rag(query: str, thread_id: Optional[str])` |
| **Embeddings** | HuggingFace `intfloat/e5-base-v2` |
| **Vector Store** | FAISS (in-memory, per-thread) |
| **Loader** | `PyPDFLoader` |
| **Splitter** | `RecursiveCharacterTextSplitter` (chunk=1000, overlap=200) |

**Description:**  
Enables Retrieval-Augmented Generation (RAG) over uploaded PDF documents. When a PDF is uploaded via the sidebar, it is parsed, split into chunks, embedded using HuggingFace embeddings, and stored in a FAISS vector index tied to the user's thread. This tool retrieves the top-4 most relevant document chunks for a given query.

**When it's triggered:**
- Any question about a document that has been uploaded in the current session
- "What does the document say about X?"
- "Summarize section 3 of the uploaded file"
- "Find information about Y in the PDF"

**PDF Ingestion flow (`ingest_pdf`):**
1. Save uploaded bytes to a temp file
2. Load pages using `PyPDFLoader`
3. Split with `RecursiveCharacterTextSplitter`
4. Build FAISS vector store with HuggingFace embeddings
5. Store retriever in-memory keyed by `thread_id`

**Returns:** Extracted document excerpts concatenated and passed to the LLM for answering.

> ⚠️ If no document has been uploaded for the thread, the tool returns an informative message asking the user to upload a PDF first.

---

### 8. 📧 Email Tool (HITL) — `email_tool`

| Property | Details |
|----------|---------|
| **Function** | `email_tool(user_message: str, config: RunnableConfig)` |
| **SMTP** | Gmail SMTP (`smtp.gmail.com:587`) |
| **Env Variables** | `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` |
| **HITL** | ✅ Yes — uses LangGraph `interrupt()` |
| **Traced** | Yes (`@traceable(name="EmailTool")`) |

**Description:**  
This is the most sophisticated tool, featuring full **Human-in-the-Loop (HITL)** control. When the user asks the agent to send an email, this tool:

1. **Extracts** the recipient email address from the user's message using regex
2. **Generates** a professional email draft (subject + body) using the LLM
3. **Stores** the draft in a pending state tied to the current `thread_id`
4. **Returns** the draft preview to the user — the email is **NOT sent yet**

The `chat_node` then detects the pending email and calls `interrupt()` to **pause the graph** and surface an approval UI in Streamlit with three options:

| Decision | Action |
|----------|--------|
| **YES** | Email is sent via SMTP and the draft is cleared |
| **NO** | Draft is discarded, no email is sent |
| **MODIFY** | User provides changes, the LLM regenerates the draft, and approval is requested again |

**When it's triggered:**
- "Send an email to john@example.com about the meeting tomorrow"
- "Draft and send an email to team@company.com with the project update"
- Any message containing an email address and intent to send

**HITL Flow Diagram:**
```
User → "Send email to X"
  → email_tool creates draft
  → chat_node detects pending email
  → interrupt() called → Graph paused
  → Streamlit shows YES / NO / MODIFY buttons
      YES  → SMTP send → ✅ Confirmation
      NO   → Draft discarded → 📭 Cancelled
      MODIFY → User edits → LLM regenerates → Back to approval
```

---

## 🌱 Environment Variables (`.env`)

Create a `.env` file in the project root with the following format:

```env
# ─────────────────────────────────────────────
# LLM Provider
# ─────────────────────────────────────────────
# Groq API key for running Llama 3.3 70B
GROQ_API_KEY=your_groq_api_key_here

# ─────────────────────────────────────────────
# Stock Market Data
# ─────────────────────────────────────────────
# Alpha Vantage API key for real-time stock quotes
# Get yours at: https://www.alphavantage.co/support/#api-key
STOCK_API_KEY=your_alpha_vantage_api_key_here

# ─────────────────────────────────────────────
# Weather & Astronomy Data
# ─────────────────────────────────────────────
# WeatherAPI key for current weather, forecast, and astronomy
# Get yours at: https://www.weatherapi.com/signup.aspx
WEATHER_API_KEY=your_weatherapi_key_here

# ─────────────────────────────────────────────
# Email (SMTP) — for HITL Email Tool
# ─────────────────────────────────────────────
# SMTP server hostname (default: Gmail)
SMTP_SERVER=smtp.gmail.com

# SMTP port (587 for TLS, 465 for SSL)
SMTP_PORT=587

# The email address that sends emails
SMTP_USERNAME=your_email@gmail.com

# Gmail App Password (NOT your regular Gmail password)
# Generate at: https://myaccount.google.com/apppasswords
SMTP_PASSWORD=your_gmail_app_password_here

# ─────────────────────────────────────────────
# LangSmith Tracing (Optional but recommended)
# ─────────────────────────────────────────────
# Enables tracing for all @traceable tools in LangSmith
# Get yours at: https://smith.langchain.com/
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=HITL-Chatterbot
```

> **Note on Gmail:** You must enable **2-Factor Authentication** on your Google account and generate an **App Password** specifically for this application. Your regular Gmail password will not work with SMTP.

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install langgraph langchain langchain-community langchain-groq \
            langchain-huggingface langsmith streamlit faiss-cpu \
            pypdf requests python-dotenv
```

### 2. Set up your `.env` file

Copy the template above and fill in all required API keys.

### 3. Run the application

```bash
streamlit run HITL_frontend.py
```

---

## 💡 Key Concepts

### Human-in-the-Loop (HITL)
LangGraph's `interrupt()` function pauses graph execution mid-run and yields control back to the application. The Streamlit frontend detects `__interrupt__` in the graph's result and renders approval buttons. When the user makes a decision, `Command(resume=<decision>)` is passed back to resume the graph from exactly where it paused.

### Thread-based Memory
Each conversation session gets a unique `thread_id` (UUID). The SQLite-backed `SqliteSaver` checkpointer persists the full message history per thread, enabling multi-turn conversations that survive page refreshes.

### Per-Thread RAG
Each thread maintains its own FAISS vector store in memory. Uploading a PDF in one chat session does not affect other sessions. The retriever is keyed by `thread_id` and automatically used by the `rag` tool when questions are asked about the document.
