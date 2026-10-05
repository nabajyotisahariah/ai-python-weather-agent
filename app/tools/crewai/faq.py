from pathlib import Path
import logging

from crewai.tools import tool
import httpx
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

from app.config import settings

logger = logging.getLogger(__name__)


@tool("search_faq")
def search_faq(query: str) -> str:
    """
    Searches the Weather FAQ knowledge base using RAG and
    returns a concise answer based only on retrieved FAQ content.
    """

    print(f">>>> SEARCH FAQ CALLED WITH query={query}")

    try:
        # 1. Create embeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key, http_client=httpx.Client()
        )

        # 2. Load FAISS knowledge base
        save_path = Path(settings.data_dir) / "faiss_index"

        if not save_path.exists():
            return "FAQ Knowledge base is currently unavailable."

        vectorstore = FAISS.load_local(
            str(save_path),
            embeddings,
            allow_dangerous_deserialization=True
        )

        # 3. Retrieve relevant FAQ chunks
        docs = vectorstore.similarity_search(query, k=3)

        if not docs:
            return "No relevant information found in the FAQ knowledge base."

        # 4. Build RAG context
        context = "\n\n".join(
            f"--- FAQ Excerpt {i + 1} ---\n{doc.page_content}"
            for i, doc in enumerate(docs)
        )
        print("context ",context)

        # 5. Generate answer using retrieved context
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.openai_api_key, http_client=httpx.Client()
        )

        prompt = f"""
You are a Weather FAQ assistant.

Answer the user's question using ONLY the information
provided in the FAQ context below.

If the answer cannot be found in the context, say:
"I couldn't find this information in the Weather FAQ."

Do not invent or assume information.

Keep the answer concise and within 100 words.

User Question:
{query}

FAQ Context:
{context}
"""

        # 6. RAG generation
        response = llm.invoke(prompt)

        return response.content.strip()

    except Exception as e:
        logger.error(f"Error searching FAQ: {e}", exc_info=True)
        return f"Error searching FAQ knowledge base: {e}"


@tool("search_faq_v2")
def search_faq_v2(query: str) -> str:
    """
    Searches the Weather FAQ knowledge base using RAG and
    returns a concise answer based only on retrieved FAQ content.
    """

    print(f">>>> SEARCH FAQ CALLED WITH query={query}")

    try:
        # 1. Create embeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key, http_client=httpx.Client()
        )

        # 2. Load FAISS knowledge base
        save_path = Path(settings.data_dir) / "faiss_index"

        if not save_path.exists():
            return "FAQ Knowledge base is currently unavailable."

        vectorstore = FAISS.load_local(
            str(save_path),
            embeddings,
            allow_dangerous_deserialization=True
        )

        # 3. Retrieve relevant FAQ chunks
        #docs = vectorstore.similarity_search(query, k=3)
        results = vectorstore.similarity_search_with_score(query, k=3)

        docs = [
            doc
            for doc, score in results
            if score < 0.8
        ]

        if not docs:
            return "No relevant information found in the FAQ knowledge base."

        # 4. Build RAG context
        context = "\n\n".join(
            f"--- FAQ Excerpt {i + 1} ---\n{doc.page_content}"
            for i, doc in enumerate(docs)
        )

        # 5. Generate answer using retrieved context
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.openai_api_key, http_client=httpx.Client()
        )

        prompt = f"""
You are a Weather FAQ assistant.

Answer the user's question using ONLY the information
provided in the FAQ context below.

If the answer cannot be found in the context, say:
"I couldn't find this information in the Weather FAQ."

Do not invent or assume information.

Keep the answer concise and within 100 words.

User Question:
{query}

FAQ Context:
{context}
"""

        # 6. RAG generation
        response = llm.invoke(prompt)

        return response.content.strip()

    except Exception as e:
        logger.error(f"Error searching FAQ: {e}", exc_info=True)
        return f"Error searching FAQ knowledge base: {e}"