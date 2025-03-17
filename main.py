from utils.database import init_mongodb, find_similar_chunks
from utils.ai_services import (
    get_embedding,
    get_gemini_response,
    process_gemini_response,
)
from utils.ui_components import (
    authenticate,
    setup_page_config,
    add_custom_css,
    init_session_state,
    check_authentication,
    format_message,
    # redirect_page,
)
from utils.display_utils import display_chunk_content
import streamlit as st

# from dotenv import load_dotenv
import os

# Load environment variables
# load_dotenv()


def process_query(question, collection):
    """Process a query and return response with all necessary updates to the UI"""
    # Ensure examples are hidden when processing any query
    st.session_state.show_examples = False
    # Add to conversation history
    st.session_state.conversation_history.append({"role": "user", "content": question})

    # Show user message
    with st.chat_message("user"):
        st.markdown(question)

    # Show assistant message and perform query
    with st.chat_message("assistant"):
        with st.spinner("מחפש בנהלים..."):
            query_embedding = get_embedding(question)
            similar_chunks = find_similar_chunks(collection, query_embedding, question)

            if not similar_chunks:
                response_text = "לא נמצא מידע רלוונטי בנהלים."
                used_chunks = []
                st.markdown(response_text)
            else:
                # Create a placeholder for the streaming response
                response_placeholder = st.empty()
                complete_response = ""

                # Get and display streaming response
                for chunk in get_gemini_response(
                    question, similar_chunks, st.session_state.conversation_history
                ):
                    complete_response += chunk
                    # Update the placeholder with accumulated response
                    response_placeholder.markdown(
                        format_message(complete_response), unsafe_allow_html=True
                    )

                # Process the complete response to get used chunks
                response_text, used_chunks = process_gemini_response(
                    complete_response, similar_chunks
                )

            if used_chunks:
                with st.expander("📚 מקורות"):
                    for chunk in used_chunks:
                        st.markdown(
                            f"**{chunk['metadata']['filename']}** (עמוד {chunk.get('pages', ['לא ידוע'])[0]})"
                        )
                        display_chunk_content(chunk)

            st.session_state.conversation_history.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "sources": [
                        {
                            "filename": chunk["metadata"]["filename"],
                            "page": chunk.get("pages", ["לא ידוע"])[0],
                            "content": chunk["chunk_text"],
                        }
                        for chunk in used_chunks
                    ],
                }
            )


def create_example_questions(collection):
    example_questions = [
        "מהו תהליך קליטת עובד חדש?",
        "מה נוהל החזר הוצאות?",
        "איך מגישים בקשה לחופשה?",
        "מהם שעות העבודה הגמישות?",
    ]

    st.write("")
    st.markdown("##### שאלות לדוגמה:")

    # Create a placeholder for storing the clicked question
    if "clicked_question" not in st.session_state:
        st.session_state.clicked_question = None

    cols = st.columns(2)

    for idx, question in enumerate(example_questions):
        with cols[idx % 2]:
            if st.button(question, key=f"example_q_{idx}", use_container_width=True):
                st.session_state.clicked_question = question

    st.write("")

    # Process the clicked question outside the column layout
    if st.session_state.clicked_question:
        question = st.session_state.clicked_question
        st.session_state.clicked_question = None  # Reset for next time
        process_query(question, collection)
        st.rerun()


def main():
    setup_page_config()
    add_custom_css()
    init_session_state()

    # Enforce authentication
    if not check_authentication():
        st.warning("Please log in to access this page.")
        authenticate()
        st.stop()
        # redirect_page()

    st.title("📚 צ'אטבוט נהלי קמביום")
    collection = init_mongodb()

    # Initialize show_examples in init_session_state instead
    if "show_examples" not in st.session_state:
        st.session_state.show_examples = True

    # Display conversation history
    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "sources" in message:
                st.markdown(message["content"])
                with st.expander("📚 מקורות"):
                    for source in message["sources"]:
                        st.markdown(f"**{source['filename']}** (עמוד {source['page']})")
                        st.markdown(source["content"])
            else:
                st.markdown(message["content"])

    # Show example questions only if there's no conversation history
    if st.session_state.show_examples and not st.session_state.conversation_history:
        create_example_questions(collection)

    # Chat input
    if question := st.chat_input("שאל שאלה על נהלי קמביום..."):
        process_query(question, collection)
        st.rerun()  # Force a rerun to update the UI immediately


if __name__ == "__main__":
    main()
