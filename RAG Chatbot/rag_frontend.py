import streamlit as st
from rag_backend import chatbot, retrieve_chats, ingest_pdf, thread_has_document, thread_document_metadata
from langchain_core.messages import HumanMessage, AIMessage
from rag_backend import model
import uuid
from typing import Optional, Dict, Any
import tempfile
import os
import time

def generate_chat_name_from_conversation(thread_id):
    """Generate a chat name based on the first user message and AI response"""
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        messages = state.values.get('messages', [])
        
        # Find the first user message
        user_message = None
        for msg in messages:
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break
        
        if user_message:
            # Truncate long messages for the prompt
            truncated_message = user_message[:200] + "..." if len(user_message) > 200 else user_message
            prompt_content = f"Generate a very short, descriptive chat name (3-6 words max) based on this user query: '{truncated_message}'. Return only the name, nothing else. Make it catchy and relevant."
        else:
            return "New Chat"
        
        # Call the model with proper message format
        response = model.invoke([HumanMessage(content=prompt_content)])
        # The response is an AIMessage object, access content directly
        chat_name = response.content.strip('"\'').strip()
        
        # Clean up the response - ensure it's not too long
        if len(chat_name) > 60:
            # If the response is too long, create a shorter name from the user message
            words = user_message.split()[:6]
            chat_name = ' '.join(words) + '...'
        
        return chat_name
    except Exception as e:
        print(f"Error generating chat name: {e}")
        # Fallback: create a name from the user message
        if 'user_message' in locals() and user_message:
            words = user_message.split()[:4]
            return ' '.join(words) + '...'
        return "Chat Conversation"

def generate_thread_id():
    thread_id = uuid.uuid4()
    return str(thread_id)

def reset_chat():
    """Reset chat and create new thread"""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []
    st.session_state['uploaded_file_info'] = None
    st.session_state['tool_usage_info'] = {}
    
    # Initialize as new chat
    if 'chat_names' not in st.session_state:
        st.session_state['chat_names'] = {}
    st.session_state['chat_names'][thread_id] = "New Chat"
    
    # Add to chat threads immediately so it appears in history
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def add_thread_to_history(thread_id):
    """Add a thread to the history"""
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    """Load conversation messages for a thread"""
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        messages = state.values.get('messages', [])
        
        # Filter out system messages
        filtered_messages = []
        for msg in messages:
            if hasattr(msg, 'content') and msg.content:
                filtered_messages.append(msg)
        
        return filtered_messages
    except Exception as e:
        print(f"Error loading conversation for thread {thread_id}: {e}")
        return []

def update_chat_name_if_needed(thread_id):
    """Update chat name if it's still 'New Chat'"""
    if ('chat_names' in st.session_state and 
        thread_id in st.session_state['chat_names']):
        
        current_name = st.session_state['chat_names'][thread_id]
        
        # Only update if it's "New Chat"
        if current_name == "New Chat":
            messages = load_conversation(thread_id)
            # Check if we have at least one user message
            user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
            
            if user_count >= 1:
                chat_name = generate_chat_name_from_conversation(thread_id)
                st.session_state['chat_names'][thread_id] = chat_name
                return chat_name
    return None

def filter_real_chats(chat_threads):
    """Filter out threads that don't have real conversations"""
    real_chats = []
    if 'chat_names' not in st.session_state:
        return chat_threads
    
    for thread_id in chat_threads:
        # Skip if it's marked as "New Chat" (not started yet)
        chat_name = st.session_state['chat_names'].get(thread_id, "New Chat")
        
        # Also check if it has actual messages
        messages = load_conversation(thread_id)
        user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        
        # Only include if it has at least one user message
        if user_count > 0 and chat_name != "New Chat":
            real_chats.append(thread_id)
    
    return real_chats

def upload_pdf_to_thread(file_bytes, filename: str, thread_id: str) -> Optional[Dict[str, Any]]:
    """Upload PDF to the current thread and return metadata"""
    try:
        with st.spinner(f"Processing {filename}..."):
            summary = ingest_pdf(file_bytes, thread_id, filename)
            if summary:
                # Store file info in session state
                st.session_state['uploaded_file_info'] = summary
                return summary
    except Exception as e:
        st.error(f"Error uploading PDF: {str(e)}")
        return None

def get_tool_display_name(tool_name: str) -> str:
    """Convert tool function name to display-friendly name"""
    tool_display_map = {
        'stock_details': 'Stock Details',
        'url_metadata': 'URL Analysis',
        'weather_updates_current': 'Current Weather',
        'astronomical_updates': 'Astronomical Data',
        'forecast_update': 'Weather Forecast',
        'rag': 'Document RAG',
        'search_info': 'Web Search'
    }
    return tool_display_map.get(tool_name, tool_name.replace('_', ' ').title())

def extract_tool_name_from_content(content: str) -> Optional[str]:
    """Extract tool name from AI response content if it mentions tool usage"""
    import re
    
    # Look for tool mentions in the content
    tool_patterns = [
        (r'using (?:the )?(\w+) tool', 1),
        (r'calling (?:the )?(\w+)', 1),
        (r'tool[:\s]+(\w+)', 1),
        (r'(\w+_update)', 1),
        (r'(\w+_details)', 1),
        (r'(\w+_metadata)', 1),
    ]
    
    for pattern, group in tool_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return get_tool_display_name(match.group(group))
    
    return None

# Initialize session state
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    # Get all chats from database
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

# Initialize chat names for existing threads
for thread_id in st.session_state['chat_threads']:
    if thread_id not in st.session_state['chat_names']:
        # Check if this is a real conversation
        messages = load_conversation(thread_id)
        user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        
        if user_count > 0:
            # Generate a name for real conversations
            chat_name = generate_chat_name_from_conversation(thread_id)
            st.session_state['chat_names'][thread_id] = chat_name
        else:
            # Set as New Chat for empty conversations
            st.session_state['chat_names'][thread_id] = "New Chat"

# Initialize current thread
if st.session_state['thread_id'] not in st.session_state['chat_names']:
    st.session_state['chat_names'][st.session_state['thread_id']] = "New Chat"
    add_thread_to_history(st.session_state['thread_id'])

# Check if current thread has uploaded document
current_thread_id = st.session_state['thread_id']
if thread_has_document(current_thread_id) and not st.session_state.get('uploaded_file_info'):
    doc_metadata = thread_document_metadata(current_thread_id)
    if doc_metadata:
        st.session_state['uploaded_file_info'] = doc_metadata

# Page configuration
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .file-info-box {
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 5px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
    }
    .tool-usage-box {
        padding: 8px 12px;
        background-color: #e6f3ff;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #0066cc;
        font-size: 0.9em;
    }
    .tool-name {
        font-weight: bold;
        color: #0066cc;
    }
    .chat-history-button {
        text-align: left;
        padding: 8px;
        margin: 2px 0;
        border-radius: 5px;
        border: 1px solid #ddd;
        background-color: white;
    }
    .chat-history-button:hover {
        background-color: #f5f5f5;
    }
    .document-indicator {
        color: #28a745;
        font-weight: bold;
        margin-left: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar layout
st.sidebar.title("RAG Chatbot")

# New Chat button
col1, col2 = st.sidebar.columns([3, 1])
with col1:
    if st.button("New Chat", use_container_width=True, type="primary"):
        reset_chat()
        st.rerun()

with col2:
    if st.button("Refresh", help="Refresh chat list", use_container_width=True):
        st.rerun()

st.sidebar.divider()

# Document Upload Section
st.sidebar.header("Document Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload a PDF file for RAG",
    type=['pdf'],
    key=f"file_uploader_{st.session_state['file_uploader_key']}",
    label_visibility="collapsed"
)

if uploaded_file is not None:
    # Check file size (limit to 10MB)
    if uploaded_file.size > 10 * 1024 * 1024:
        st.sidebar.error("File size too large. Please upload a file smaller than 10MB.")
    else:
        file_bytes = uploaded_file.read()
        file_info = upload_pdf_to_thread(file_bytes, uploaded_file.name, current_thread_id)
        if file_info:
            # Success message with auto-clear
            success_placeholder = st.sidebar.empty()
            success_placeholder.success(f"✅ {uploaded_file.name} uploaded successfully!")
            
            # Increment uploader key to reset the file uploader
            st.session_state['file_uploader_key'] += 1
            
            # Clear success message after 3 seconds
            time.sleep(3)
            success_placeholder.empty()
            
            st.rerun()

# Display uploaded file info
if st.session_state.get('uploaded_file_info'):
    file_info = st.session_state['uploaded_file_info']
    st.sidebar.markdown(f"""
    <div class="file-info-box">
        <strong>Current Document:</strong><br>
        <strong>File:</strong> {file_info.get('filename', 'N/A')}<br>
        <strong>Pages:</strong> {file_info.get('documents', 0)}<br>
        <strong>Chunks:</strong> {file_info.get('chunks', 0)}
    </div>
    """, unsafe_allow_html=True)
    
    if st.sidebar.button("Remove Document", type="secondary", use_container_width=True):
        st.session_state['uploaded_file_info'] = None
        # Note: The backend retriever remains, but UI won't show it
        st.rerun()

# Available Tools Information
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
    """)

# Conversation History
st.sidebar.divider()
st.sidebar.header("Conversation History")

# Filter to show only real chats
real_chats = filter_real_chats(st.session_state['chat_threads'])

# Display chat history in sidebar
if not real_chats:
    st.sidebar.info("No previous conversations")
else:
    for thread_id in real_chats[::-1]:  # Show most recent first
        # Get the chat name
        chat_name = st.session_state['chat_names'].get(thread_id, "Chat Conversation")
        
        # Check if this thread had a document
        thread_doc_info = thread_document_metadata(thread_id)
        has_doc = bool(thread_doc_info)
        
        # Create button label
        button_label = chat_name[:35] + "..." if len(chat_name) > 35 else chat_name
        if has_doc:
            button_label = f"{button_label} 📄"
        
        # Use a unique key for each button
        button_key = f"history_{thread_id}"
        
        if st.sidebar.button(button_label, key=button_key, use_container_width=True):
            st.session_state['thread_id'] = thread_id
            
            # Load conversation messages
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
            
            # Update uploaded file info for the selected thread
            if thread_doc_info:
                st.session_state['uploaded_file_info'] = thread_doc_info
            else:
                st.session_state['uploaded_file_info'] = None
            
            # Rerun to update the display
            st.rerun()

# Main chat area
st.title("RAG Chatbot with Multiple Tools")

# Display current document status
if st.session_state.get('uploaded_file_info'):
    file_info = st.session_state['uploaded_file_info']
    st.info(f"**Document Loaded:** {file_info.get('filename', 'N/A')} (Pages: {file_info.get('documents', 0)}, Chunks: {file_info.get('chunks', 0)})")
else:
    st.info("No document loaded. You can upload a PDF or ask general questions using other tools.")

# Tool usage indicator area
if st.session_state.get('tool_usage_info'):
    tool_info = st.session_state['tool_usage_info']
    if tool_info.get('active'):
        st.markdown(f"""
        <div class="tool-usage-box">
            <span class="tool-name">{tool_info.get('name', 'Tool')}</span> processing...
        </div>
        """, unsafe_allow_html=True)

# Display current conversation
st.divider()

# Chat message display
for idx, message in enumerate(st.session_state['message_history']):
    with st.chat_message(message['role']):
        st.markdown(message['content'])
        
        # Show tool usage after assistant messages if available
        if message['role'] == 'assistant' and idx > 0:
            tool_key = f"tool_used_{idx}"
            if tool_key in st.session_state['tool_usage_info']:
                tool_name = st.session_state['tool_usage_info'][tool_key]
                st.caption(f"*Used tool: {tool_name}*")

# Chat input
user_input = st.chat_input('Type your message here...')

if user_input:
    # Add user message to history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)
    
    # Clear previous tool usage indicators
    st.session_state['tool_usage_info'] = {'active': False}

    # LangSmith configuration for tracing
    CONFIG = {
        'configurable': {'thread_id': st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chatbot_run"
    }
    
    with st.chat_message('assistant'):
        message_placeholder = st.empty()
        full_response = ""
        
        # Track tool usage
        last_tool_used = None
        tool_usage_detected = False
        
        try:
            # Stream the response
            for chunk in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            ):
                # Handle different chunk types
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    message_chunk, metadata = chunk
                else:
                    message_chunk = chunk
                
                # Check for tool calls
                if hasattr(message_chunk, 'additional_kwargs'):
                    tool_calls = message_chunk.additional_kwargs.get('tool_calls', [])
                    if tool_calls:
                        for tool_call in tool_calls:
                            if isinstance(tool_call, dict):
                                tool_name = tool_call.get('function', {}).get('name', '')
                                if tool_name:
                                    display_name = get_tool_display_name(tool_name)
                                    last_tool_used = display_name
                                    tool_usage_detected = True
                                    
                                    # Update tool usage indicator
                                    st.session_state['tool_usage_info'] = {
                                        'active': True,
                                        'name': display_name
                                    }
                                    
                                    # Show tool usage in UI
                                    with message_placeholder.container():
                                        if full_response:
                                            st.markdown(full_response)
                                        st.markdown(f"""
                                        <div class="tool-usage-box">
                                            <span class="tool-name">{display_name}</span> processing...
                                        </div>
                                        """, unsafe_allow_html=True)
                
                # Handle message content
                if hasattr(message_chunk, 'content') and message_chunk.content:
                    full_response += message_chunk.content
                    
                    # Clear tool usage indicator if we're getting content
                    if full_response.strip() and tool_usage_detected:
                        st.session_state['tool_usage_info']['active'] = False
                    
                    message_placeholder.markdown(full_response + "▌")
        
        except Exception as e:
            st.error(f"Error during response generation: {str(e)}")
            full_response = "Sorry, I encountered an error. Please try again."
        
        for message_chunk, metadata in chatbot.stream(
        {'messages': [HumanMessage(content=user_input)]},
        config=CONFIG,
        stream_mode='messages'
    ):
            if isinstance(message_chunk, AIMessage):
                full_response += message_chunk.content
                message_placeholder.markdown(full_response + "▌")
        
                
            message_placeholder.markdown(full_response)
        
        # Store tool usage info for this response
        if last_tool_used:
            tool_key = f"tool_used_{len(st.session_state['message_history'])}"
            st.session_state['tool_usage_info'][tool_key] = last_tool_used
            
            # Show which tool was used
            st.caption(f"*Used tool: {last_tool_used}*")
        else:
            # Try to extract tool name from content
            extracted_tool = extract_tool_name_from_content(full_response)
            if extracted_tool:
                tool_key = f"tool_used_{len(st.session_state['message_history'])}"
                st.session_state['tool_usage_info'][tool_key] = extracted_tool
                st.caption(f"*Used tool: {extracted_tool}*")
    
    # Add AI response to history
    st.session_state['message_history'].append({'role': 'assistant', 'content': full_response})
    
    # Update chat name after first exchange
    user_messages = [m for m in st.session_state['message_history'] if m['role'] == 'user']
    if len(user_messages) == 1:
        update_chat_name_if_needed(st.session_state['thread_id'])
        # Rerun to update sidebar with new chat name
        st.rerun()

# Footer
st.divider()
st.caption(f"Thread ID: {current_thread_id[:8]}...")