import streamlit as st
from modules.auth import CareLogService
import gui

# --- Page Configuration ---
st.set_page_config(
    page_title="CareLog",
    page_icon="🩺",
    layout="wide"
)

# --- Service Initialization ---
@st.cache_resource
def get_carelog_service():
    """Initializes and returns the main service."""
    return CareLogService()

service = get_carelog_service()

# --- Session State Management ---
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# NEW: Add a state for the authentication page
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = 'welcome'


# --- Main App Router ---
if st.session_state.current_user:
    # If a user is logged in, show the main application.
    gui.show_main_app(service)
else:
    # If no user is logged in, route to the correct auth page
    if st.session_state.auth_page == 'welcome':
        gui.show_welcome_page()
    elif st.session_state.auth_page == 'login':
        gui.show_login_form(service)
    elif st.session_state.auth_page == 'register':
        gui.show_register_form(service)