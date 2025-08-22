from langchain.embeddings import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter

from bson import ObjectId
from pymongo import MongoClient

from datetime import datetime
import os
import numpy as np

knowledge_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.users

embedding = OpenAIEmbeddings()

def embed(plot: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = text_splitter.split_text(plot)

    embeddings = embedding.embed_documents(chunks)
    
    return embeddings

def similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return similarity

def save_embedding(embeddings: list, user_id: ObjectId, agent_id: ObjectId) -> None:
    knowledge_db.embeddings.insert_one({
        "user_id": user_id,
        "agent_id": agent_id,
        "embeddings": embeddings,
        "created_at": datetime.utcnow()
    })

def get_embeddings(user_id: ObjectId, agent_id: ObjectId) -> list:
    result = knowledge_db.embeddings.find_one({
        "user_id": user_id,
        "agent_id": agent_id
    })

    if result:
        return result["embeddings"]
    
    return []

