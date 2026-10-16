from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from app.orchestrator.langgraph.agent_graph import build_agent_graph, message_text
from app.tools.langgraph.faq_tool import search_faq


def build_weather_faq_delegate(llm: ChatOpenAI) -> BaseTool:
    agent, prompt = build_agent_graph(
        llm,
        [search_faq],
        (
            "You are the weather FAQ specialist. Use only information returned "
            "by the FAQ search tool. If it does not contain the answer, say so."
        ),
    )

    @tool("delegate_to_weather_faq")
    async def delegate_to_weather_faq(question: str) -> str:
        """Delegate an application, pricing, subscription, or usage question to the FAQ specialist."""
        result = await agent.ainvoke(
            {
                "messages": [
                    prompt,
                    HumanMessage(content=question),
                ]
            }
        )
        return message_text(result["messages"][-1])

    return delegate_to_weather_faq
