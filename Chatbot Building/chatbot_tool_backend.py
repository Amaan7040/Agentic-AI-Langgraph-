from langgraph.graph import StateGraph, START, END # pyright: ignore[reportMissingImports]
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage # pyright: ignore[reportMissingImports]
from langchain_groq.chat_models import ChatGroq # pyright: ignore[reportMissingImports]
from langgraph.checkpoint.sqlite import SqliteSaver # pyright: ignore[reportMissingImports]
from langgraph.graph.message import add_messages # pyright: ignore[reportMissingImports]
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langsmith import traceable
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
import sqlite3
import os
import requests

load_dotenv()

llm_model = ChatGroq(model="llama-3.3-70b-versatile")

# adding tools to the chatbot

#Tool1
@traceable(name="DuckDuckGOSearch")
def search_info():
   search = DuckDuckGoSearchRun(name="web_search",
    description="Search the internet for current or real-time information")
   
   return search.text[:6000]

#Tool2
@tool
@traceable(name="Stock Details")
def stock_details(symbol: str)-> dict:
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

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={os.environ["STOCK_API_KEY"]}"
    stocks_info = requests.get(url=url)

    return stocks_info.json()

#Tool3
@tool
@traceable(name="Url info")
def url_metadata(url: str) -> dict:
    """
    Use this tool when the user provides a URL and asks to:
    - summarize the webpage
    - extract key points
    - understand website content
    - analyze an article or blog

    Input must be a valid URL starting with http or https.

    Returns cleaned textual content in a safe JSON format.
    """

    try:
        response = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )

        content_type = response.headers.get("Content-Type", "")

        # Always return JSON-safe output
        return {
            "url": url,
            "status_code": response.status_code,
            "content_type": content_type,
            "text": response.text[:4000]  # prevent token explosion
        }

    except Exception as e:
        return {
            "url": url,
            "error": str(e)
        }

#Tool4
@tool
@traceable(name="Current Weather")
def weather_updates_current(q:str)-> dict:
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

    url = "https://api.weatherapi.com/v1/current.json"
    querystring = {"q": q,"key": os.environ["WEATHER_API_KEY"]}
    headers = {"Accept": "application/json, application/xml"}
    response = requests.get(url, headers=headers, params=querystring)

    return response.json()

#Tool5
@tool
@traceable(name="Astronomical Updates")
def astronomical_updates(q: str, dt: str)-> dict:
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

    url = "https://api.weatherapi.com/v1/astronomy.json"
    querystring = {"q": q,"dt": dt,"key": os.environ["WEATHER_API_KEY"]}
    headers = {"Accept": "application/json, application/xml"}
    response = requests.get(url, headers=headers, params=querystring)
    
    return response.json()

#Tool6
@tool
@traceable(name="Forecast Weather")
def forecast_update(q: str, days)-> dict:
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
        days = int(days)  # 🔑 FIX: force-cast
    except (ValueError, TypeError):
        return {
            "error": "Invalid 'days' parameter. It must be a number like 1, 3, or 7."
        }

    days = max(1, min(days, 7))  # safety bounds

    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {"error": "WEATHER_API_KEY not set"}

    url = "https://api.weatherapi.com/v1/forecast.json"
    params = {
        "q": q,
        "days": days,
        "key": api_key,
        "alerts": "no",
        "aqi": "no"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

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

        return {
            "location": {
                "city": data["location"]["name"],
                "region": data["location"]["region"],
                "country": data["location"]["country"],
                "local_time": data["location"]["localtime"]
            },
            "forecast_days": forecast_days
        }

    except Exception as e:
        return {
            "error": "Unable to fetch forecast data",
            "details": str(e)
        }

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = chatbot_with_tools.invoke(messages)
    return {"messages": [response]}

tools = [stock_details, stock_details, url_metadata, weather_updates_current, astronomical_updates, forecast_update]

chatbot_with_tools = llm_model.bind_tools(tools)

connection = sqlite3.connect("chatbot.db", check_same_thread=False)

# Checkpointer
checkpointer = SqliteSaver(conn=connection)

tool_node = ToolNode(tools)

graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")


chatbot = graph.compile(checkpointer=checkpointer)
print("Chatbot backend is ready.")

#Extract all the chats threads stored in the database.
def retrieve_chats():

    all_chats = set()

    for chats_checkpoints in checkpointer.list(None):
        all_chats.add(chats_checkpoints.config['configurable']['thread_id'])

    return list(all_chats)

# Initialize the model for chat name generation
model = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)