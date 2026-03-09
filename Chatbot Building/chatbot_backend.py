from langgraph.graph import StateGraph, START, END # pyright: ignore[reportMissingImports]
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage # pyright: ignore[reportMissingImports]
from langchain_groq.chat_models import ChatGroq # pyright: ignore[reportMissingImports]
from langgraph.checkpoint.memory import InMemorySaver # pyright: ignore[reportMissingImports]
from langgraph.graph.message import add_messages # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]

load_dotenv()

llm_model = ChatGroq(model="llama-3.3-70b-versatile")

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm_model.invoke(messages)
    return {"messages": [response]}

# Checkpointer
checkpointer = InMemorySaver()

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)
print("Chatbot backend is ready.")