

import logging
from pathlib import Path
from crewai.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)

@tool("search_faq")
def search_faq(query: str) -> str:
    """Searches the Weather FAQ policies knowledge base to answer questions."""
    print(f">>>> SEARCH FAQ CALLED WITH query={query}")
    try:
       embeddings = OpenAIEmbeddings(
           model="text-embedding-3-small",
           openai_api_key=settings.openai_api_key
       )
       save_path = Path(settings.data_dir) / "faiss_index"
       if not save_path.exists():
           return "FAQ Knowledge base is currently unavailable."
       
       vectorstore = FAISS.load_local(str(save_path), embeddings, allow_dangerous_deserialization=True)
       docs = vectorstore.similarity_search(query, k=3)
       if not docs:
           return "No relevant information found in the FAQ knowledge base."
       
       # Combine the text from the most relevant chunks
       results = [f"--- Excerpt {i+1} ---\n{doc.page_content}" for i, doc in enumerate(docs)]
       return "\n\n".join(results)
    except Exception as e:
       logger.error(f"Error searching FAQ: {e}")
       return f"Error searching FAQ knowledge base: {e}"