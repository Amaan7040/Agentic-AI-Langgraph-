import streamlit as st
from HITL_backend import chatbot, retrieve_chats, ingest_pdf, thread_has_document, thread_document_metadata
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from HITL_backend import model
import uuid
from typing import Optional, Dict, Any, List
import tempfile
import os
import time

from langgraph.types import Command

# -------------------------------------------------------------------
# Helper functions – unchanged from your original code
# -------------------------------------------------------------------
def generate_chat_name_from_conversation(thread_id):
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        messages = state.values.get('messages', [])
        user_message = None
        for msg in messages:
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break
        if user_message:
            truncated_message = user_message[:200] + "..." if len(user_message) > 200 else user_message
            prompt_content = f"Generate a very short, descriptive chat name (3-6 words max) based on this user query: '{truncated_message}'. Return only the name, nothing else. Make it catchy and relevant."
        else:
            return "New Chat"
        response = model.invoke([HumanMessage(content=prompt_content)])
        chat_name = response.content.strip('"\'').strip()
        if len(chat_name) > 60:
            words = user_message.split()[:6]
            chat_name = ' '.join(words) + '...'
        return chat_name
    except Exception as e:
        print(f"Error generating chat name: {e}")
        if 'user_message' in locals() and user_message:
            words = user_message.split()[:4]
            return ' '.join(words) + '...'
        return "Chat Conversation"

def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []
    st.session_state['uploaded_file_info'] = None
    st.session_state['tool_usage_info'] = {}
    st.session_state['current_tool_indicator'] = None
    if 'chat_names' not in st.session_state:
        st.session_state['chat_names'] = {}
    st.session_state['chat_names'][thread_id] = "New Chat"
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def add_thread_to_history(thread_id):
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        messages = state.values.get('messages', [])
        filtered_messages = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                filtered_messages.append(msg)
        return filtered_messages
    except Exception as e:
        print(f"Error loading conversation for thread {thread_id}: {e}")
        return []

def update_chat_name_if_needed(thread_id):
    if ('chat_names' in st.session_state and 
        thread_id in st.session_state['chat_names']):
        current_name = st.session_state['chat_names'][thread_id]
        if current_name == "New Chat":
            messages = load_conversation(thread_id)
            user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
            if user_count >= 1:
                chat_name = generate_chat_name_from_conversation(thread_id)
                st.session_state['chat_names'][thread_id] = chat_name
                return chat_name
    return None

def filter_real_chats(chat_threads):
    real_chats = []
    if 'chat_names' not in st.session_state:
        return chat_threads
    for thread_id in chat_threads:
        chat_name = st.session_state['chat_names'].get(thread_id, "New Chat")
        messages = load_conversation(thread_id)
        user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        if user_count > 0 and chat_name != "New Chat":
            real_chats.append(thread_id)
    return real_chats

def upload_pdf_to_thread(file_bytes, filename: str, thread_id: str) -> Optional[Dict[str, Any]]:
    try:
        with st.spinner(f"Processing {filename}..."):
            summary = ingest_pdf(file_bytes, thread_id, filename)
            if summary:
                st.session_state['uploaded_file_info'] = summary
                return summary
    except Exception as e:
        st.error(f"Error uploading PDF: {str(e)}")
        return None

def get_tool_display_name(tool_name: str) -> str:
    tool_display_map = {
        'stock_details': 'Stock Details',
        'url_metadata': 'URL Analysis',
        'weather_updates_current': 'Current Weather',
        'astronomical_updates': 'Astronomical Data',
        'forecast_update': 'Weather Forecast',
        'rag': 'Document RAG',
        'search_info': 'Web Search',
        'email_tool': 'Email Tool'
    }
    return tool_display_map.get(tool_name, tool_name.replace('_', ' ').title())

# -------------------------------------------------------------------
# Session state initialization
# -------------------------------------------------------------------
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    all_threads = retrieve_chats()
    st.session_state['chat_threads'] = all_threads

if 'chat_names' not in st.session_state:
    st.session_state['chat_names'] = {}

if 'uploaded_file_info' not in st.session_state:
    st.session_state['uploaded_file_info'] = None

if 'tool_usage_info' not in st.session_state:
    st.session_state['tool_usage_info'] = {}

if 'file_uploader_key' not in st.session_state:
    st.session_state['file_uploader_key'] = 0

if 'current_tool_indicator' not in st.session_state:
    st.session_state['current_tool_indicator'] = None

# ---------- NEW: HITL session state variables ----------
if 'pending_interrupt' not in st.session_state:
    st.session_state['pending_interrupt'] = None
if 'pending_thread_id' not in st.session_state:
    st.session_state['pending_thread_id'] = None
if 'decision_made' not in st.session_state:
    st.session_state['decision_made'] = False
if 'pending_command' not in st.session_state:
    st.session_state['pending_command'] = None
# -------------------------------------------------------

for thread_id in st.session_state['chat_threads']:
    if thread_id not in st.session_state['chat_names']:
        messages = load_conversation(thread_id)
        user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        if user_count > 0:
            chat_name = generate_chat_name_from_conversation(thread_id)
            st.session_state['chat_names'][thread_id] = chat_name
        else:
            st.session_state['chat_names'][thread_id] = "New Chat"

if st.session_state['thread_id'] not in st.session_state['chat_names']:
    st.session_state['chat_names'][st.session_state['thread_id']] = "New Chat"
    add_thread_to_history(st.session_state['thread_id'])

current_thread_id = st.session_state['thread_id']
if thread_has_document(current_thread_id) and not st.session_state.get('uploaded_file_info'):
    doc_metadata = thread_document_metadata(current_thread_id)
    if doc_metadata:
        st.session_state['uploaded_file_info'] = doc_metadata

# -------------------------------------------------------------------
# Page configuration – renamed to Chatterbot
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Chatterbot",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS (unchanged)
st.markdown("""
<style>
    .stButton button { width: 100%; }
    .file-info-box {
        padding: 12px; background-color: #2c3e50; color: #ecf0f1; border-radius: 8px; margin-bottom: 10px;
        border: 1px solid #34495e; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .file-info-box strong { color: #3498db; }
    .tool-usage-indicator {
        padding: 8px 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border-radius: 6px; margin: 5px 0; border-left: 4px solid #4a00e0; font-size: 0.85em;
        animation: pulse 2s infinite;
    }
    .tools-used-box {
        padding: 10px; background-color: #f8f9fa; border-radius: 8px; margin: 10px 0;
        border: 1px solid #dee2e6; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .tool-badge {
        display: inline-block; padding: 4px 8px; margin: 2px 4px 2px 0;
        background-color: #e3f2fd; border-radius: 12px; font-size: 0.8em;
        color: #1565c0; border: 1px solid #bbdefb;
    }
    .chat-history-button {
        text-align: left; padding: 8px; margin: 2px 0; border-radius: 5px;
        border: 1px solid #ddd; background-color: white;
    }
    .chat-history-button:hover { background-color: #f5f5f5; }
    .document-indicator { color: #28a745; font-weight: bold; margin-left: 5px; }
    @keyframes pulse {
        0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; }
    }
    .tool-processing {
        background: linear-gradient(90deg, #4a00e0, #8e2de2); color: white;
        padding: 5px 10px; border-radius: 4px; margin: 5px 0; display: inline-block;
    }
    .email-pending {
        background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px;
        padding: 12px; margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Sidebar – renamed to Chatterbot, minimal icons
# -------------------------------------------------------------------
st.sidebar.title("Chatterbot")

col1, col2 = st.sidebar.columns([3, 1])
with col1:
    if st.button("New Chat", use_container_width=True, type="primary"):
        reset_chat()
        st.rerun()
with col2:
    if st.button("Refresh", help="Refresh chat list", use_container_width=True):
        st.rerun()

st.sidebar.divider()

st.sidebar.header("Document Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload a PDF file",
    type=['pdf'],
    key=f"file_uploader_{st.session_state['file_uploader_key']}",
    label_visibility="collapsed"
)

if uploaded_file is not None:
    if uploaded_file.size > 10 * 1024 * 1024:
        st.sidebar.error("File size too large. Please upload a file smaller than 10MB.")
    else:
        file_bytes = uploaded_file.read()
        file_info = upload_pdf_to_thread(file_bytes, uploaded_file.name, current_thread_id)
        if file_info:
            success_placeholder = st.sidebar.empty()
            success_placeholder.success(f"✅ {uploaded_file.name} uploaded successfully!")
            st.session_state['file_uploader_key'] += 1
            time.sleep(3)
            success_placeholder.empty()
            st.rerun()

if st.session_state.get('uploaded_file_info'):
    file_info = st.session_state['uploaded_file_info']
    st.sidebar.markdown(f"""
    <div class="file-info-box">
        <strong>📄 Current Document</strong><br><br>
        <strong>File:</strong> {file_info.get('filename', 'N/A')}<br>
        <strong>Pages:</strong> {file_info.get('documents', 0)}<br>
        <strong>Chunks:</strong> {file_info.get('chunks', 0)}
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("Remove Document", type="secondary", use_container_width=True):
        st.session_state['uploaded_file_info'] = None
        st.rerun()

st.sidebar.divider()
st.sidebar.header("Available Tools")
with st.sidebar.expander("View All Tools"):
    st.markdown("""
    **Document RAG**: Chat with uploaded PDFs  
    **Stock Details**: Get real-time stock prices  
    **URL Analysis**: Extract and summarize web content  
    **Current Weather**: Get weather conditions  
    **Weather Forecast**: Get future weather predictions  
    **Astronomical Data**: Sunrise, sunset, moon phases  
    **Web Search**: Search the internet for information  
    **Email Tool**: Draft and send emails (HITL enabled)
    """)

st.sidebar.divider()
st.sidebar.header("Conversation History")

real_chats = filter_real_chats(st.session_state['chat_threads'])
if not real_chats:
    st.sidebar.info("No previous conversations")
else:
    for thread_id in real_chats[::-1]:
        chat_name = st.session_state['chat_names'].get(thread_id, "Chat Conversation")
        thread_doc_info = thread_document_metadata(thread_id)
        has_doc = bool(thread_doc_info)
        button_label = chat_name[:35] + "..." if len(chat_name) > 35 else chat_name
        if has_doc:
            button_label = f"{button_label} 📄"
        button_key = f"history_{thread_id}"
        if st.sidebar.button(button_label, key=button_key, use_container_width=True):
            st.session_state['thread_id'] = thread_id
            messages = load_conversation(thread_id)
            temp_message_history = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    role = 'user'
                    content = msg.content
                elif isinstance(msg, AIMessage):
                    role = 'assistant'
                    content = msg.content
                else:
                    continue
                temp_message_history.append({'role': role, 'content': content})
            st.session_state['message_history'] = temp_message_history
            if thread_doc_info:
                st.session_state['uploaded_file_info'] = thread_doc_info
            else:
                st.session_state['uploaded_file_info'] = None
            st.session_state['current_tool_indicator'] = None
            st.rerun()

# -------------------------------------------------------------------
# MAIN CHAT AREA – THREE-STAGE HITL HANDLING
# -------------------------------------------------------------------
st.title("Chatterbot")

# ---- Document status ----
if st.session_state.get('uploaded_file_info'):
    file_info = st.session_state['uploaded_file_info']
    st.info(f"**Document Loaded:** {file_info.get('filename', 'N/A')} (Pages: {file_info.get('documents', 0)}, Chunks: {file_info.get('chunks', 0)})")
else:
    st.info("No document loaded. You can upload a PDF or ask general questions using other tools.")
st.divider()

# ---- Display conversation history ----
for idx, message in enumerate(st.session_state['message_history']):
    with st.chat_message(message['role']):
        st.markdown(message['content'])
        if message['role'] == 'assistant':
            tool_key = f"tools_used_{idx}"
            if tool_key in st.session_state['tool_usage_info']:
                tools_used = st.session_state['tool_usage_info'][tool_key]
                if tools_used:
                    with st.expander(f"Tools used ({len(tools_used)})"):
                        for tool_name in tools_used:
                            st.markdown(f"<div class='tool-badge'>{tool_name}</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# STAGE 1: If a decision was made in the previous run, resume the graph
# -------------------------------------------------------------------
if st.session_state['decision_made'] and st.session_state['pending_interrupt']:
    thread_id = st.session_state['pending_thread_id']
    config = {'configurable': {'thread_id': thread_id}}
    command = st.session_state['pending_command']

    try:
        final_result = chatbot.invoke(command, config=config)
        ai_response = None
        for msg in reversed(final_result['messages']):
            if isinstance(msg, AIMessage) and msg.content:
                ai_response = msg.content
                break
        if not ai_response:
            ai_response = "Email processed."

        with st.chat_message('assistant'):
            st.markdown(ai_response)
        st.session_state['message_history'].append({'role': 'assistant', 'content': ai_response})

        # Record tool usage
        tools_used_key = f"tools_used_{len(st.session_state['message_history'])}"
        st.session_state['tool_usage_info'][tools_used_key] = ["Email Tool"]

    except Exception as e:
        st.error(f"Error during resume: {str(e)}")

    # Clear HITL state
    st.session_state['pending_interrupt'] = None
    st.session_state['pending_thread_id'] = None
    st.session_state['decision_made'] = False
    st.session_state['pending_command'] = None

    st.rerun()

# -------------------------------------------------------------------
# STAGE 2: If an interrupt is pending but no decision yet, show YES/NO/MODIFY buttons
# -------------------------------------------------------------------
if st.session_state['pending_interrupt'] and not st.session_state['decision_made']:
    interrupt_info = st.session_state['pending_interrupt']
    thread_id = st.session_state['pending_thread_id']

    st.markdown("---")
    st.warning("Human Approval Required")
    st.markdown(f"""
    **Email Draft**
    - **To:** {interrupt_info['to']}
    - **Subject:** {interrupt_info['subject']}
    
    **Body:**
    ```
    {interrupt_info['body']}
    ```
    """)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("YES – Send", key=f"yes_{thread_id}"):
            st.session_state['pending_command'] = Command(resume="YES")
            st.session_state['decision_made'] = True
            st.rerun()
    with col2:
        if st.button("NO – Cancel", key=f"no_{thread_id}"):
            st.session_state['pending_command'] = Command(resume="NO")
            st.session_state['decision_made'] = True
            st.rerun()
    with col3:
        if st.button("MODIFY – Change", key=f"modify_{thread_id}"):
            st.session_state['pending_command'] = Command(resume="MODIFY")
            st.session_state['decision_made'] = True
            st.rerun()

# -------------------------------------------------------------------
# STAGE 3: Normal user input – first invoke
# -------------------------------------------------------------------
user_input = st.chat_input('Type your message here...')

if user_input:
    # Add user message to UI and session
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    thread_id = st.session_state['thread_id']
    config = {'configurable': {'thread_id': thread_id}}

    try:
        result = chatbot.invoke(
            {'messages': [HumanMessage(content=user_input)]},
            config=config
        )
    except Exception as e:
        st.error(f"Error during invoke: {str(e)}")
        st.stop()

    # --- Check for interrupt ---
    if '__interrupt__' in result:
        interrupt_info = result['__interrupt__'][0].value
        if interrupt_info.get('type') == 'email_approval':
            # Store interrupt and rerun – buttons will appear in the next run
            st.session_state['pending_interrupt'] = interrupt_info
            st.session_state['pending_thread_id'] = thread_id
            st.session_state['decision_made'] = False
            st.rerun()
        else:
            st.write("Received interrupt:", interrupt_info)
    else:
        # --- Normal AI response (no interrupt) ---
        ai_response = None
        for msg in reversed(result['messages']):
            if isinstance(msg, AIMessage) and msg.content:
                ai_response = msg.content
                break
        if ai_response:
            with st.chat_message('assistant'):
                st.markdown(ai_response)
            st.session_state['message_history'].append({'role': 'assistant', 'content': ai_response})
        else:
            st.error("No response from assistant.")

    # Update chat name after first exchange
    user_messages = [m for m in st.session_state['message_history'] if m['role'] == 'user']
    if len(user_messages) == 1:
        update_chat_name_if_needed(thread_id)
        st.rerun()

# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------
st.divider()
st.caption(f"Thread ID: {current_thread_id[:8]}...")