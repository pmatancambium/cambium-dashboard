"""MongoDB database operations"""

from pymongo import MongoClient
import streamlit as st
from typing import List, Dict

# from dotenv import load_dotenv
import os

# Load environment variables
# load_dotenv()


def init_mongodb():
    """Initialize MongoDB connection"""
    client = MongoClient(st.secrets["MONGODB_URI"])
    return client["cambium-procedures"].document_chunks


def find_similar_chunks(
    collection,
    query_embedding: List[float],
    query_text: str,
    search_params: Dict = None,
) -> List[Dict]:
    """
    Hybrid search function combining vector and text search

    Args:
        collection: MongoDB collection
        query_embedding: Vector embedding of the query
        query_text: Original query text
        search_params: Dictionary containing search parameters like filters, sort, limit
    """
    if not search_params:
        search_params = {"limit": 100}

    try:
        # Vector search pipeline
        vector_pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": search_params.get("limit", 100),
                }
            },
            {
                "$addFields": {
                    "search_score": {"$meta": "vectorSearchScore"},
                    "vector_score": {"$meta": "vectorSearchScore"},
                    "text_score": {"$literal": 0},
                }
            },
        ]

        # Add filters if specified
        if "filter" in search_params:
            vector_pipeline.insert(1, {"$match": search_params["filter"]})

        # Add sorting if specified
        if "sort" in search_params:
            vector_pipeline.append({"$sort": dict(search_params["sort"])})

        vector_results = list(collection.aggregate(vector_pipeline))

        # Text search with the same parameters
        text_query = query_text
        if "additional_terms" in search_params:
            text_query = f"{text_query} {' '.join(search_params['additional_terms'])}"

        text_pipeline = [
            {
                "$search": {
                    "index": "text_index",
                    "text": {
                        "query": text_query,
                        "path": {"wildcard": "*"},
                        "score": {"boost": {"value": 0.9}},
                    },
                }
            },
            {
                "$addFields": {
                    "search_score": {"$meta": "searchScore"},
                    "vector_score": {"$literal": 0},
                    "text_score": {"$meta": "searchScore"},
                }
            },
        ]

        # Add filters if specified
        if "filter" in search_params:
            text_pipeline.insert(1, {"$match": search_params["filter"]})

        # Add sorting and limit if specified
        if "sort" in search_params:
            text_pipeline.append({"$sort": dict(search_params["sort"])})
        if "limit" in search_params:
            text_pipeline.append({"$limit": search_params["limit"]})

        text_results = list(collection.aggregate(text_pipeline))

        # Combine and deduplicate results
        all_results = vector_results + text_results

        # Group by chunk ID and take highest score
        grouped_results = {}
        for result in all_results:
            chunk_id = result["_id"]
            if (
                chunk_id not in grouped_results
                or result["search_score"] > grouped_results[chunk_id]["search_score"]
            ):
                grouped_results[chunk_id] = result

        # Convert back to list and sort
        final_results = list(grouped_results.values())

        # Apply final sorting
        if "sort" in search_params:
            sort_field = search_params["sort"][0][0]
            sort_direction = search_params["sort"][0][1]
            final_results.sort(
                key=lambda x: x[sort_field], reverse=sort_direction == -1
            )

        # Apply final limit
        if "limit" in search_params:
            final_results = final_results[: search_params["limit"]]

        return final_results

    except Exception as e:
        print(f"Search error: {e}")
        return []
