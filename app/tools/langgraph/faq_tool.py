from pathlib import Path

import httpx
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.guardrails.tool_guardrails import validate_tool_call


@tool
async def search_faq(query: str) -> str:
    """Search the Weather FAQ and return excerpts relevant to the question."""
    validate_tool_call("search_faq", {"query": query})
    query = validate_query(query)

    index_path = Path(settings.data_dir) / "faiss_index"
    if not index_path.exists():
        return "FAQ knowledge base is currently unavailable."

    async with httpx.AsyncClient(
        timeout=settings.weather_timeout_seconds
    ) as http_client:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
            http_async_client=http_client,
        )
        query_vector = await embeddings.aembed_query(query)

    vectorstore = FAISS.load_local(
        str(index_path), embeddings, allow_dangerous_deserialization=True
    )
    documents = vectorstore.similarity_search_by_vector(query_vector, k=3)
    if not documents:
        return "No relevant information found in the FAQ knowledge base."

    return "\n\n".join(
        f"--- FAQ Excerpt {index} ---\n{document.page_content}"
        for index, document in enumerate(documents, start=1)
    )
