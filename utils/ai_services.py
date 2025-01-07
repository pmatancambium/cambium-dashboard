"""AI service operations using Google's Generative AI"""

from google import genai
import google.generativeai as genaiEmb
from typing import List, Dict, Tuple, Generator
import streamlit as st
import re

# from dotenv import load_dotenv
import os
import json
from datetime import datetime
from google.genai.types import GenerateContentResponse, GenerateContentConfig

# Load environment variables
# load_dotenv()

# Configure API clients
genaiEmb.configure(api_key=st.secrets["GEMINI_API_KEY"])
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL_ID = "gemini-2.0-flash-exp"  # or your specific model ID


def get_embedding(text: str) -> List[float]:
    """Get text embedding using Gemini"""
    result = genaiEmb.embed_content(
        model="models/text-embedding-004", content=text, task_type="retrieval_query"
    )
    return result["embedding"]


def get_gemini_response(
    question: str, chunks: List[Dict], history: List[Dict]
) -> Generator[str, None, None]:
    """Get streaming response from Gemini model"""
    context_texts = [
        f"""[{i}] מתוך {chunk['metadata']['filename']} (עמוד {chunk.get('pages', ['לא ידוע'])[0]}):\n{chunk['chunk_text']}"""
        for i, chunk in enumerate(chunks, 1)
    ]

    context = "\n\n".join(context_texts)
    prompt = create_gemini_prompt(question, context)

    try:
        response = client.models.generate_content_stream(
            model=MODEL_ID,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )

        for chunk in response:
            if hasattr(chunk, "text"):
                yield chunk.text
            elif isinstance(chunk, tuple):
                yield str(chunk[0])
            else:
                yield str(chunk)

    except Exception as e:
        print(f"Error generating response: {e}")
        yield "Error generating response"


def process_gemini_response(
    response_text: str, chunks: List[Dict]
) -> Tuple[str, List[Dict]]:
    """Process the complete Gemini response to extract used sources"""
    used_source_numbers = set(re.findall(r"\[(\d+)\]", response_text))
    used_chunks = [
        chunks[int(num) - 1] for num in used_source_numbers if int(num) <= len(chunks)
    ]
    return response_text, used_chunks


def create_gemini_prompt(question: str, context: str) -> str:
    """Create the prompt for Gemini"""
    return f"""
    בהתבסס על הקטעים הבאים מנהלי קמביום:

    {context}

    שאלה: {question}

    הנחיות:
    1. ענה על השאלה בהתבסס על המידע מהנהלים בלבד. ענה בהרחבה בהתאם לשאלה ובאופן מנומק.
    2. בסוף כל טענה, הוסף מספר בסוגריים מרובעות המציין את מספר המקור [1], [2] וכו'
    3. אם אין מידע רלוונטי בקטעים שסופקו, ציין זאת
    4. בסוף התשובה, הוסף רק את המקורות שהשתמשת בהם בתשובה, בפורמט:

    מקורות:
    [X] מתוך <שם הקובץ> (עמוד Y)

    חשוב: השתמש במספרי המקורות כפי שהם מופיעים בקטעי המקור למעלה.
    """
