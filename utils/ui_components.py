"""UI components and styling for the Streamlit app"""

import streamlit as st
import html as html_lib
from typing import List, Dict

# from dotenv import load_dotenv
from time import sleep
import os
import re

# Load environment variables
# load_dotenv()


def redirect_page():
    """Redirect to a different page"""
    sleep(0.5)
    st.switch_page("Home.py")


def setup_page_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="נהלי קמביום - צ'אטבוט",
        page_icon="📚",
        layout="wide",
    )


def add_custom_css():
    """Add custom CSS for RTL support and styling"""
    st.markdown(
        """
        <style>
        /* RTL Support */
        .element-container, .stMarkdown, .stButton {
            direction: rtl;
        }

        /* Chat message styling */
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            max-width: 80%;
        }

        .user-message {
            background-color: #f0f2f6;
            margin-left: auto;
        }

        .assistant-message {
            background-color: #e3f2fd;
            margin-right: auto;
        }

        /* Source citation styling */
        .source-citation {
            border-left: 3px solid #1976d2;
            padding-left: 1rem;
            margin: 1rem 0;
            background-color: #f8f9fa;
        }

        /* Table styling */
        table {
            direction: rtl;
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }

        th {
            background-color: #f3f3f3;
            border: 1px solid #ddd;
            padding: 8px;
            text-align: right;
        }

        td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: right;
        }

        tr:nth-child(even) {
            background-color: #f9f9f9;
        }

        tr:hover {
            background-color: #f5f5f5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "show_examples" not in st.session_state:
        st.session_state.show_examples = True


def check_authentication() -> bool:
    """Check if user is authenticated"""
    return st.session_state.authenticated


def authenticate() -> bool:
    """Handle password authentication"""
    if st.session_state.authenticated:
        return True

    st.title("🔒 password protected")
    password = st.text_input("Enter password :", type="password")

    if st.button("Enter"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("סיסמה שגויה!")
            return False
    return False


def format_message(text: str, is_hebrew: bool = True) -> str:
    """Format message with appropriate text direction"""
    direction = "rtl" if is_hebrew else "ltr"
    return f'<div dir="{direction}">{text}</div>'
