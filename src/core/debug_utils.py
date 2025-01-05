import streamlit as st

def add_debug_message(message):
    """Add a message to the debug log"""
    try:
        if 'debug_messages' not in st.session_state:
            st.session_state.debug_messages = []
        st.session_state.debug_messages.append(message)
    except:
        # Fallback to print when not in Streamlit
        print(f"Debug: {message}")

def clear_debug_messages():
    """Clear all debug messages"""
    try:
        if 'debug_messages' in st.session_state:
            st.session_state.debug_messages = []
    except:
        pass

def display_debug_messages():
    """Display all debug messages"""
    try:
        if 'debug_messages' in st.session_state:
            for message in st.session_state.debug_messages:
                st.text(message)
    except:
        pass

def initialize_debug():
    """Initialize debug state"""
    try:
        if 'debug_messages' not in st.session_state:
            st.session_state.debug_messages = []
    except:
        pass 