from typing import Annotated, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    SystemMessage,
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def message_text(message: BaseMessage) -> str:
    if not isinstance(message.content, str):
        raise TypeError("LangGraph agent returned a non-text response")
    return message.content


def build_agent_graph(
    llm: ChatOpenAI,
    agent_tools: list[BaseTool],
    system_prompt: str,
):
    llm_with_tools = llm.bind_tools(agent_tools)

    async def agent(state: AgentState) -> dict[str, list[BaseMessage]]:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(agent_tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile(), SystemMessage(content=system_prompt)
