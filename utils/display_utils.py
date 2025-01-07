"""Utilities for displaying content in Streamlit"""

import streamlit as st
from typing import Dict
from utils.table_utils import is_markdown_table, format_table_html


def display_chunk_content(chunk: Dict):
    """Display chunk content, handling both tables and regular text"""
    text = chunk["chunk_text"]

    if is_markdown_table(text):
        table_html = format_table_html(text)
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.markdown(text)
