from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Optional, Dict, Any, List
import operator

from langgraph.types import interrupt, Command
from langchain_core.runnables.config import RunnableConfig 
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_groq.chat_models import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_huggingface.embeddings import HuggingFaceEmbeddings # pyright: ignore[reportMissingImports]
from langsmith import traceable
from dotenv import load_dotenv
import re
import smtplib
from email.message import EmailMessage
import sqlite3
import tempfile
import os
import requests
import json

load_dotenv()

llm_model = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

embeddings = HuggingFaceEmbeddings(model="intfloat/e5-base-v2")

_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}
_PENDING_EMAILS: Dict[str, dict] = {}

def _get_retriever(thread_id: Optional[str]):
    """Fetch the retriever for a thread if available."""
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None

def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """Build a FAISS retriever for the uploaded PDF and store it for the thread."""
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)

        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )

        _THREAD_RETRIEVERS[str(thread_id)] = retriever
        _THREAD_METADATA[str(thread_id)] = {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(chunks),
        }

        return {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(chunks),
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

# Tool Definitions (Non-email tools remain the same)
# Tool 1: Web Search
@tool
@traceable(name="WebSearch")
def search_info(query: str) -> str:
    """
    Use this tool to search the internet for current or real-time information.
    
    Trigger keywords include:
    - current events
    - latest news
    - recent information
    - web search
    - search online
    
    Returns search results as text.
    """
    try:
        search = DuckDuckGoSearchRun()
        result = search.run(query)
        return result[:6000] if result else "No results found."
    except Exception as e:
        return f"Search failed: {str(e)}"


# Tool 2: Stock Details
@tool
@traceable(name="StockDetails")
def stock_details(symbol: str) -> str:
    """
    Use this tool when the user asks about stock prices, stock performance,
    market value, trading price, or financial data of a company.

    Trigger keywords include:
    - stock price
    - share price
    - market price
    - trading value
    - company stock today

    Input must be a valid stock ticker symbol such as:
    AAPL, TSLA, MSFT, INFY, TCS, RELIANCE.

    Returns real-time stock market data.
    """
    try:
        api_key = os.getenv("STOCK_API_KEY")
        if not api_key:
            return "STOCK_API_KEY not set in environment variables."

        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
        response = requests.get(url)
        data = response.json()

        if "Global Quote" in data:
            quote = data["Global Quote"]
            return json.dumps({
                "symbol": symbol,
                "price": quote.get("05. price", "N/A"),
                "change": quote.get("09. change", "N/A"),
                "change_percent": quote.get("10. change percent", "N/A"),
                "volume": quote.get("06. volume", "N/A"),
                "latest_trading_day": quote.get("07. latest trading day", "N/A")
            })
        else:
            return f"Could not fetch stock data for {symbol}. Error: {data.get('Error Message', 'Unknown error')}"
    except Exception as e:
        return f"Error fetching stock data: {str(e)}"


# Tool 3: URL Metadata
@tool
@traceable(name="UrlInfo")
def url_metadata(url: str) -> str:
    """
    Use this tool when the user provides a URL and asks to:
    - summarize the webpage
    - extract key points
    - understand website content
    - analyze an article or blog

    Input must be a valid URL starting with http or https.

    Returns cleaned textual content.
    """
    try:
        response = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        
        if response.status_code == 200:
            return response.text[:6000]  # Limit response size
        else:
            return f"Failed to fetch URL. Status code: {response.status_code}"
    except Exception as e:
        return f"Error fetching URL: {str(e)}"


# Tool 4: Current Weather
@tool
@traceable(name="CurrentWeather")
def weather_updates_current(q: str) -> str:
    """
    Use this tool to get the current weather conditions of a location.

    Trigger when the user asks about:
    - current weather
    - temperature now
    - weather today
    - live weather conditions

    Input should be a city name, region, or location such as:
    Delhi, Mumbai, New York, London.

    Returns real-time weather data.
    """
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            return "WEATHER_API_KEY not set in environment variables."

        url = "https://api.weatherapi.com/v1/current.json"
        params = {"q": q, "key": api_key}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "error" in data:
            return f"Weather API error: {data['error'].get('message', 'Unknown error')}"

        current = data.get("current", {})
        location = data.get("location", {})

        result = {
            "location": f"{location.get('name', 'N/A')}, {location.get('region', 'N/A')}, {location.get('country', 'N/A')}",
            "temperature_c": current.get("temp_c", "N/A"),
            "temperature_f": current.get("temp_f", "N/A"),
            "condition": current.get("condition", {}).get("text", "N/A"),
            "humidity": current.get("humidity", "N/A"),
            "wind_kph": current.get("wind_kph", "N/A"),
            "wind_dir": current.get("wind_dir", "N/A"),
            "feelslike_c": current.get("feelslike_c", "N/A"),
            "visibility_km": current.get("vis_km", "N/A"),
            "last_updated": current.get("last_updated", "N/A")
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error fetching weather data: {str(e)}"


# Tool 5: Astronomical Updates
@tool
@traceable(name="AstronomicalUpdates")
def astronomical_updates(q: str, dt: str) -> str:
    """
    Use this tool when the user asks about astronomical information for a location.

    Trigger keywords include:
    - sunrise
    - sunset
    - moonrise
    - moonset
    - moon phase
    - astronomical data

    Input:
    - q: location name (city or region)
    - dt: date in YYYY-MM-DD format

    Returns astronomy-related data for the given date and location.
    """
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            return "WEATHER_API_KEY not set in environment variables."

        url = "https://api.weatherapi.com/v1/astronomy.json"
        params = {"q": q, "dt": dt, "key": api_key}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "error" in data:
            return f"Astronomy API error: {data['error'].get('message', 'Unknown error')}"

        astronomy = data.get("astronomy", {}).get("astro", {})
        location = data.get("location", {})

        result = {
            "location": f"{location.get('name', 'N/A')}, {location.get('region', 'N/A')}, {location.get('country', 'N/A')}",
            "date": dt,
            "sunrise": astronomy.get("sunrise", "N/A"),
            "sunset": astronomy.get("sunset", "N/A"),
            "moonrise": astronomy.get("moonrise", "N/A"),
            "moonset": astronomy.get("moonset", "N/A"),
            "moon_phase": astronomy.get("moon_phase", "N/A"),
            "moon_illumination": astronomy.get("moon_illumination", "N/A")
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error fetching astronomical data: {str(e)}"


# Tool 6: Forecast Weather
@tool
@traceable(name="ForecastWeather")
def forecast_update(q: str, days: str) -> str:
    """
    Use this tool when the user asks about future weather forecasts.

    Trigger phrases include:
    - weather forecast
    - weather for next days
    - forecast for coming days
    - weather prediction

    Input:
    - q: city or location name
    - days: number of forecast days (e.g., 3, 5, 7)

    Returns multi-day weather forecast data.
    """
    try:
        days_int = int(days)
        if days_int < 1 or days_int > 7:
            return "Days parameter must be between 1 and 7."
    except (ValueError, TypeError):
        return "Invalid 'days' parameter. It must be a number like 1, 3, or 7."

    try:
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            return "WEATHER_API_KEY not set in environment variables."

        url = "https://api.weatherapi.com/v1/forecast.json"
        params = {
            "q": q,
            "days": days_int,
            "key": api_key,
            "alerts": "no",
            "aqi": "no"
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "error" in data:
            return f"Forecast API error: {data['error'].get('message', 'Unknown error')}"

        location = data.get("location", {})
        forecast_days = []

        for day in data.get("forecast", {}).get("forecastday", []):
            forecast_days.append({
                "date": day.get("date"),
                "temperature_c": {
                    "max": day["day"]["maxtemp_c"],
                    "min": day["day"]["mintemp_c"],
                    "avg": day["day"]["avgtemp_c"]
                },
                "condition": {
                    "text": day["day"]["condition"]["text"],
                    "icon": day["day"]["condition"]["icon"]
                },
                "rain_chance_percent": day["day"]["daily_chance_of_rain"],
                "wind_kph": day["day"]["maxwind_kph"],
                "humidity_avg": day["day"]["avghumidity"],
                "uv_index": day["day"]["uv"],
                "sunrise": day["astro"]["sunrise"],
                "sunset": day["astro"]["sunset"]
            })

        result = {
            "location": {
                "city": location.get("name", "N/A"),
                "region": location.get("region", "N/A"),
                "country": location.get("country", "N/A"),
                "local_time": location.get("localtime", "N/A")
            },
            "forecast_days": forecast_days
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error fetching forecast data: {str(e)}"


# Tool 7: RAG Tool
@tool
def rag(query: str, thread_id: Optional[str] = None) -> str:
    """
    Use this tool to answer questions based on uploaded PDF documents.
    
    This tool will retrieve relevant information from the uploaded document
    and provide context-aware answers.
    
    Trigger when the user asks questions about the uploaded document content.
    """
    retriever = _get_retriever(thread_id)

    if not retriever:
        return "No document has been uploaded for this chat. Please upload a PDF file first to ask questions about it."

    try:
        results = retriever.invoke(query)
        if not results:
            return "No relevant information found in the document for this query."

        context_parts = []
        for i, doc in enumerate(results, 1):
            content = doc.page_content
            # Clean and truncate the content
            content = ' '.join(content.split()[:200])  # Limit to ~200 words
            context_parts.append(f"[Document excerpt {i}]: {content}")

        context = "\n\n".join(context_parts)
        return f"Based on the document content:\n\n{context}\n\nPlease answer the user's query: {query}"
    except Exception as e:
        return f"Error retrieving document information: {str(e)}"

# Tool 8: Email draft + send with HITL on approval of user it will send email else not
@tool
@traceable(name="EmailTool")
def email_tool(user_message: str, config: RunnableConfig) -> str:
    """
    Create an email draft based on the user's request.
    The email will NOT be sent until you explicitly approve it.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: Could not determine thread ID."

    email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_message)
    if not email_match:
        return "Could not find recipient email address in the prompt."
    recipient = email_match.group(0)

    email_generation_prompt = f"""
    Generate a professional email based on the following request:
    "{user_message}"
    
    Format:
    Subject: <subject line>
    Body: <properly formatted professional email>
    """
    response = llm_model.invoke(email_generation_prompt)
    content = response.content

    subject_match = re.search(r"Subject:\s*(.*)", content)
    body_match = re.search(r"Body:\s*(.*)", content, re.DOTALL)

    subject = subject_match.group(1).strip() if subject_match else "No Subject"
    body = body_match.group(1).strip() if body_match else content

    _PENDING_EMAILS[thread_id] = {
        "to": recipient,
        "subject": subject,
        "body": body,
        "status": "awaiting_approval"
    }

    return f"""
📧 **EMAIL DRAFT CREATED - AWAITING HUMAN APPROVAL**

**To:** {recipient}
**Subject:** {subject}

**Body:**
{body}
"""

# State definition
class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def chat_node(state: ChatState, config=None):
    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")

    # ----- HITL: Check for pending email -----
    if thread_id and thread_id in _PENDING_EMAILS:
        email_data = _PENDING_EMAILS[thread_id]

        if email_data["status"] == "awaiting_approval":
            # --- INTERRUPT! Ask for approval with three options ---
            approval_request = {
                "type": "email_approval",
                "to": email_data["to"],
                "subject": email_data["subject"],
                "body": email_data["body"],
                "instruction": "Do you approve sending this email? Reply YES, NO, or MODIFY."
            }
            decision = interrupt(approval_request)   # decision is a string: "YES", "NO", "MODIFY"

            if decision == "YES":
                try:
                    msg = EmailMessage()
                    msg["From"] = os.getenv("SMTP_USERNAME")
                    msg["To"] = email_data["to"]
                    msg["Subject"] = email_data["subject"]
                    msg.set_content(email_data["body"])

                    with smtplib.SMTP(
                        os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                        int(os.getenv("SMTP_PORT", 587))
                    ) as server:
                        server.starttls()
                        server.login(
                            os.getenv("SMTP_USERNAME"),
                            os.getenv("SMTP_PASSWORD")
                        )
                        server.send_message(msg)

                    del _PENDING_EMAILS[thread_id]
                    return {"messages": [AIMessage(content=f"✅ Email sent successfully to {email_data['to']}!")]}
                except Exception as e:
                    del _PENDING_EMAILS[thread_id]
                    return {"messages": [AIMessage(content=f"❌ Failed to send email: {str(e)}")]}

            elif decision == "NO":
                del _PENDING_EMAILS[thread_id]
                return {"messages": [AIMessage(content="📭 Email sending cancelled.")]}

            elif decision == "MODIFY":
                # Change status to await modifications, ask user for changes
                _PENDING_EMAILS[thread_id]["status"] = "awaiting_modifications"
                return {"messages": [AIMessage(content="Please provide the modifications you'd like to make to the email draft.")]}

        elif email_data["status"] == "awaiting_modifications":
            # --- User has sent modifications – regenerate draft ---
            # The last message in state is the user's modification request
            user_modification = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_modification = msg.content
                    break

            if not user_modification:
                return {"messages": [AIMessage(content="No modification text found.")]}

            # Use LLM to regenerate email based on original request + modifications
            # To keep it simple, we reuse the email_tool logic
            # We'll construct a prompt that includes the original draft and the user's changes
            original_draft = _PENDING_EMAILS[thread_id]
            regenerate_prompt = f"""
            Original email request (for context): Send email to {original_draft['to']} with subject "{original_draft['subject']}" and body:
            {original_draft['body']}

            The user now requests these modifications:
            {user_modification}

            Please generate a new, complete professional email (Subject and Body) that incorporates these changes.
            Format:
            Subject: <subject line>
            Body: <email body>
            """
            response = llm_model.invoke(regenerate_prompt)
            content = response.content

            subject_match = re.search(r"Subject:\s*(.*)", content)
            body_match = re.search(r"Body:\s*(.*)", content, re.DOTALL)
            new_subject = subject_match.group(1).strip() if subject_match else original_draft["subject"]
            new_body = body_match.group(1).strip() if body_match else content

            # Update draft and reset status to awaiting approval
            _PENDING_EMAILS[thread_id] = {
                "to": original_draft["to"],
                "subject": new_subject,
                "body": new_body,
                "status": "awaiting_approval"
            }

            # Return the new draft to the user
            return {"messages": [AIMessage(content=f"📧 Updated email draft:\n\n**To:** {original_draft['to']}\n**Subject:** {new_subject}\n\n**Body:**\n{new_body}\n\nPlease approve (YES/NO/MODIFY).")]}

    # ----- END of HITL block -----

    # ----- Regular conversation (no pending email or already handled) -----
    system_content = """You are a helpful assistant with access to various tools.

EMAIL RULES:
- When the user asks to send an email, call the `email_tool` with the user's request.
- The tool will create a draft and then the system will ask for human approval.
- Do NOT try to send the email yourself – the approval step is automatic.

Other tools (search, stocks, weather, RAG) can be used normally.
"""
    if thread_id and thread_has_document(thread_id):
        system_content += f"\nYou can use the RAG tool to answer questions about uploaded documents (thread_id: {thread_id})."

    system_message = SystemMessage(content=system_content)
    messages = [system_message] + state['messages']

    try:
        response = chatbot_with_tools.invoke(messages, config=config)
        return {"messages": [response]}
    except Exception as e:
        error_message = AIMessage(content=f"I encountered an error: {str(e)}. Please try again.")
        return {"messages": [error_message]}

# Define all tools - note only ONE email tool now
tools = [
    search_info,
    stock_details,
    url_metadata,
    weather_updates_current,
    astronomical_updates,
    forecast_update,
    rag,
    email_tool  
]

# Bind tools to LLM
chatbot_with_tools = llm_model.bind_tools(tools)

# Database connection
connection = sqlite3.connect("chatbot.db", check_same_thread=False)

# Checkpointer
checkpointer = SqliteSaver(conn=connection)

# Tool node
tool_node = ToolNode(tools)

# Build the graph
graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)
print("Chatbot backend is ready with proper HITL implementation.")

# Utility functions
def retrieve_chats():
    """Extract all chat threads stored in the database."""
    all_chats = set()
    try:
        for chats_checkpoints in checkpointer.list(None):
            config = chats_checkpoints.config.get('configurable', {})
            thread_id = config.get('thread_id')
            if thread_id:
                all_chats.add(thread_id)
    except Exception as e:
        print(f"Error retrieving chats: {e}")
    
    return list(all_chats)

def thread_has_document(thread_id: str) -> bool:
    """Check if a thread has an uploaded document."""
    return str(thread_id) in _THREAD_RETRIEVERS

def thread_document_metadata(thread_id: str) -> dict:
    """Get document metadata for a thread."""
    return _THREAD_METADATA.get(str(thread_id), {})

# Initialize model for chat name generation
model = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)