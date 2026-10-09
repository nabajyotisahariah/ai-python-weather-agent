"""
This Script is used to index the weather.txt data in the FAISS Open Vector DB
"""

import os
import sys
from pathlib import Path

# Add the root directory to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings

def build_index():
    faq_path = Path(settings.data_dir) / "faq" / "weather.txt"
    if not faq_path.exists():
        print(f"Error: FAQ text file not found at {faq_path}")
        return

    print(f"Reading {faq_path}...")
    with open(faq_path, "r", encoding="utf-8") as f:
        text = f.read()

    print("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    docs = text_splitter.create_documents([text])
    print(f"Created {len(docs)} document chunks.")

    print("Generating embeddings and building FAISS index...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )
    
    vectorstore = FAISS.from_documents(docs, embeddings)
    
    save_path = Path(settings.data_dir) / "faiss_index"
    print(f"Saving vector store to {save_path}...")
    vectorstore.save_local(str(save_path))
    
    print("FAISS index successfully built!")

if __name__ == "__main__":
    build_index()

