import streamlit as st # pyright: ignore[reportMissingImports]
from chatbot_backend import chatbot
from langchain_core.messages import HumanMessage, AIMessage # pyright: ignore[reportMissingImports]
import uuid

def generate_chat_name_from_conversation(thread_id):
    """Generate a chat name based on the first user message and AI response"""
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    messages = state.values.get('messages', [])
    
    # Find the first user message and AI response
    user_message = None
    ai_message = None
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    # Look for the first AI response after the first user message
    if user_message:
        for msg in messages:
            if isinstance(msg, AIMessage):
                ai_message = msg.content
                break
    
    if user_message and ai_message:
        # Create a prompt using both messages
        prompt_content = f"User: {user_message}\nAI: {ai_message[:100] if len(ai_message) > 100 else ai_message}\n\nGenerate a very short, descriptive chat name (3-6 words max) based on this conversation. Return only the name, nothing else."
    elif user_message:
        prompt_content = f"Generate a very short chat name (3-6 words max) based on this user query: '{user_message}'. Return only the name, nothing else."
    else:
        return "New Chat"
    
    initial_prompt = {"messages": [HumanMessage(content=prompt_content)]}
    try:
        # Use a temporary thread for chat name generation to avoid polluting the main conversation
        temp_thread_id = uuid.uuid4()
        chat_name_response = chatbot.invoke(
            initial_prompt, 
            config={'configurable': {'thread_id': temp_thread_id}}
        )
        return chat_name_response['messages'][1].content.strip('"\'')
    except Exception as e:
        print(f"Error generating chat name: {e}")
        return "Chat Conversation"
      
def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []


def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get('messages', [])

def update_chat_name_if_needed(thread_id):
    """Update chat name if it's still "New Chat" and there's at least one exchange"""
    if ('chat_names' in st.session_state and 
        thread_id in st.session_state['chat_names'] and 
        st.session_state['chat_names'][thread_id] == "New Chat"):
        
        messages = load_conversation(thread_id)
        # Check if we have at least one user message and one AI message
        user_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        ai_count = sum(1 for msg in messages if isinstance(msg, AIMessage))
        
        if user_count >= 1 and ai_count >= 1:
            chat_name = generate_chat_name_from_conversation(thread_id)
            st.session_state['chat_names'][thread_id] = chat_name
            return chat_name
    return None

# st.session_state -> will hold the conversation history until the page of the app is refreshed
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

if 'chat_names' not in st.session_state:
    st.session_state['chat_names'] = {}

# Initialize current thread in chat_threads and chat_names
if st.session_state['thread_id'] not in st.session_state['chat_threads']:
    add_thread(st.session_state['thread_id'])

if st.session_state['thread_id'] not in st.session_state['chat_names']:
    st.session_state['chat_names'][st.session_state['thread_id']] = "New Chat"

# add_thread(st.session_state['thread_id'])
update_chat_name_if_needed(st.session_state['thread_id'])

# Adding side bar
st.sidebar.title("ChatterBot")
st.sidebar.button("New Chat +", on_click=reset_chat)
st.sidebar.header("Converation History")

# stores the name of the thread and display it in sidebar
# Display chat history in sidebar
for thread_id in st.session_state['chat_threads'][::-1]:
    # Update chat name for this thread if needed
    update_chat_name_if_needed(thread_id)
    
    chat_name = st.session_state['chat_names'].get(thread_id, "Chat Conversation")
    
    # Create a clean button label (remove quotes and limit length)
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

# stores thread and display its list in sidebar
# for thread_id in st.session_state['chat_threads'][::-1]:
#     if st.sidebar.button(str(thread_id), key=thread_id):
#         st.session_state['thread_id'] = thread_id
#         messages = load_conversation(thread_id)

#         temp_message_history = []

#         for msg in messages:
#             if isinstance(msg, HumanMessage):
#                 role = 'user'
#             else:
#                 role = 'assistant'
#             temp_message_history.append({'role': role, 'content': msg.content})
        
#         st.session_state['message_history'] = temp_message_history

# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here')

if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # st.session_state -> dict -> 
    CONFIG = {'configurable': {'thread_id': st.session_state["thread_id"]}}

    # first add the message to message_history
    with st.chat_message('assistant'):

        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config= CONFIG,
                stream_mode= 'messages'
            )
        )

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})