from typing import Any
import httpx
import logging
from pathlib import Path

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

from app.services.weather_service import WeatherService
from app.services.weather_forecast_service import WeatherForecastService
from app.config import settings
from app.schema.weather import AgentResponse

logger = logging.getLogger(__name__)

weather_service = WeatherService()
weather_forecast_service = WeatherForecastService()


async def get_weather(city: str) -> AgentResponse:
    """
    Get current weather information for a city.

    Args:
        city: City name such as London, Delhi, New York or Tokyo.

    Returns:
        Current weather information.
    """

    city = city.strip()

    if not city:
        raise ValueError("City is required")

    return await weather_service.get_current_weather(city)


async def get_weather_forecast(
    city: str,
    days: int = 3,
) -> AgentResponse:
    """
    Get weather forecast for a city.

    Args:
        city: City name such as London, Delhi, New York or Tokyo.
        days: Number of forecast days, from 1 to 7.

    Returns:
        Weather forecast information.
    """

    city = city.strip()

    if not city:
        raise ValueError("City is required")

    if days < 1 or days > 7:
        raise ValueError("days must be between 1 and 7")

   
    return await weather_forecast_service.get_weather_forecast(city, days)


async def search_faq(query: str) -> str:
    """
    Searches the Weather FAQ knowledge base using RAG and
    returns a concise answer based only on retrieved FAQ content.

    Args:
        query: The user's question about weather services or FAQs.

    Returns:
        A concise answer based on the FAQ content.
    """
    logger.info(f">>>> SEARCH FAQ CALLED WITH query={query}")

    try:
        # 1. Create embeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key,
            http_client=httpx.Client()
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
        results = vectorstore.similarity_search_with_score(query, k=3)

        for i, (doc, score) in enumerate(results, start=1):
            logger.info(
                f"FAQ Result {i}: score={score:.4f}, "
                f"content={doc.page_content[:200]}"
            )

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
            openai_api_key=settings.openai_api_key,
            http_async_client=httpx.AsyncClient()
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
        response = await llm.ainvoke(prompt)

        return response.content.strip()

    except Exception as e:
        logger.error(f"Error searching FAQ: {e}", exc_info=True)
        return f"Error searching FAQ knowledge base: {e}"


