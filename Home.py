import streamlit as st
from utils.env import load_secrets
from utils.ui_components import (
    setup_page_config,
    add_custom_css,
    init_session_state,
    authenticate,
)

load_secrets()


def main():
    setup_page_config()
    # add_custom_css()
    init_session_state()

    # Check if not authenticated and not on the home page
    if not st.session_state.authenticated:
        authenticate()

    st.title("🏢 Cambium Dashboard")

    st.markdown(
        """
    ### Welcome to the Cambium Internal Dashboard

    This dashboard provides access to:

    1. 📊 **Employee Status** - Track and manage employee work hours using TimeCamp integration
    2. 📚 **Procedures Chat** - Interactive chatbot for accessing company procedures

    Select a page from the sidebar to get started.
    """
    )

    # Add company logo or additional welcome content here
    st.sidebar.success("Select a page above.")


if __name__ == "__main__":
    main()
