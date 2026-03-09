import streamlit as st # pyright: ignore[reportMissingImports]
from chatbot_with_db_backend import chatbot, retrieve_chats
from langchain_core.messages import HumanMessage, AIMessage # pyright: ignore[reportMissingImports]
from chatbot_with_db_backend import model
import uuid

def generate_chat_name_from_conversation(thread_id):
    """Generate a chat name based on the first user message and AI response"""
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
    
    try:
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
        if user_message:
            words = user_message.split()[:4]
            return ' '.join(words) + '...'
        return "Chat Conversation"

def generate_thread_id():
    thread_id = uuid.uuid4()
    return str(thread_id)

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    # Don't add to chat_threads immediately - only add after first real message
    st.session_state['message_history'] = []
    # Initialize as new chat
    if 'chat_names' not in st.session_state:
        st.session_state['chat_names'] = {}
    st.session_state['chat_names'][thread_id] = "New Chat"

def add_thread_to_history(thread_id):
    """Add a thread to the history only if it has real conversations"""
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    
    # Check if this thread has real conversations
    messages = load_conversation(thread_id)
    user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
    
    # Only add if it has at least one user message (real conversation)
    if user_count > 0 and thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        return state.values.get('messages', [])
    except Exception as e:
        print(f"Error loading conversation: {e}")
        return []

def update_chat_name_if_needed(thread_id):
    """Update chat name if it's still "New Chat" and there's at least one exchange"""
    if ('chat_names' in st.session_state and 
        thread_id in st.session_state['chat_names']):
        
        current_name = st.session_state['chat_names'][thread_id]
        
        # Only update if it's "New Chat" or hasn't been named yet
        if current_name == "New Chat" or current_name.startswith("Chat_"):
            messages = load_conversation(thread_id)
            # Check if we have at least one user message and one AI message
            user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
            ai_count = sum(1 for msg in messages if isinstance(msg, AIMessage))
            
            if user_count >= 1 and ai_count >= 1:
                chat_name = generate_chat_name_from_conversation(thread_id)
                st.session_state['chat_names'][thread_id] = chat_name
                # Also add to chat_threads if not already there
                add_thread_to_history(thread_id)
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
        if user_count > 0:
            real_chats.append(thread_id)
    
    return real_chats

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
            # Skip non-conversations - don't add to chat_names
            continue

# Initialize current thread
if st.session_state['thread_id'] not in st.session_state['chat_names']:
    st.session_state['chat_names'][st.session_state['thread_id']] = "New Chat"

# Update chat name for current thread if needed
update_chat_name_if_needed(st.session_state['thread_id'])

# Adding sidebar
st.sidebar.title("ChatterBot")
st.sidebar.button("New Chat +", on_click=reset_chat)
st.sidebar.header("Conversation History")

# Filter to show only real chats
real_chats = filter_real_chats(st.session_state['chat_threads'])

# Display chat history in sidebar
for thread_id in real_chats[::-1]:  # Show most recent first
    # Get the chat name
    chat_name = st.session_state['chat_names'].get(thread_id, "Chat Conversation")
    
    # Skip if it's a placeholder name
    if chat_name == "New Chat":
        continue
    
    # Create a clean button label
    button_label = chat_name[:40] + "..." if len(chat_name) > 40 else chat_name
    
    if st.sidebar.button(button_label, key=f"chat_{thread_id}"):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_message_history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = 'user'
            else:
                role = 'assistant'
            temp_message_history.append({'role': role, 'content': msg.content})
        
        st.session_state['message_history'] = temp_message_history
        # Rerun to update the display
        st.rerun()

# Display current conversation
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

user_input = st.chat_input('Type here')

if user_input:
    # Add user message to history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    # Stream AI response

    # this will enables the langsmith to trace chat turns and show it in its UI to give better observability like what chats being done in each thread or seperate chats sections.
    CONFIG = {
        'configurable': {'thread_id': st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chatbot_run"}
    
    with st.chat_message('assistant'):
        message_placeholder = st.empty()
        full_response = ""
        
        # Stream the response
        for message_chunk, metadata in chatbot.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='messages'
        ):
            if hasattr(message_chunk, 'content'):
                full_response += message_chunk.content
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
    
    # Add AI response to history
    st.session_state['message_history'].append({'role': 'assistant', 'content': full_response})
    
    # Update chat name after first exchange
    if len([m for m in st.session_state['message_history'] if m['role'] == 'user']) == 1:
        update_chat_name_if_needed(st.session_state['thread_id'])
        # Rerun to update sidebar with new chat name
        st.rerun()