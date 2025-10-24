# carelog/app.py

import streamlit as st
from modules.auth import CareLogService
import gui

# --- Page Configuration ---
st.set_page_config(
    page_title="CareLog",
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
if 'hospital_id' not in st.session_state:
    st.session_state.hospital_id = None
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = 'welcome'

# --- Main App Router ---
if st.session_state.current_user and st.session_state.hospital_id:
    # If a user is logged in AND a hospital is selected, show the main application.
    gui.show_main_app(service)
else:
    # Route to the correct multi-step authentication page
    if st.session_state.auth_page == 'welcome':
        gui.show_welcome_page()
    elif st.session_state.auth_page == 'login':
        gui.show_login_form(service)
    elif st.session_state.auth_page == 'register':
        gui.show_register_form(service)