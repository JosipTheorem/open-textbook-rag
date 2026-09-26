"""LangGraph agent backed by the local Qwen model and one retrieval tool."""

from __future__ import annotations

from langchain.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from textbook_agent.config import AgentSettings
from textbook_agent.tools import search_textbook

SYSTEM_PROMPT = """You are a grounded learning assistant for an open textbook.

For every factual question about the textbook, you MUST call search_textbook before
answering. Search again with a better query if the first evidence is insufficient.
The indexed textbook is in English. Every search_textbook query must be in
English: translate non-English questions before searching, and do not mix in
the original Croatian words. Preserve proper names, formulas, and code terms.
For example, for "Što je strojno učenje?" search "What is machine learning?"
Answer in the same language the user used.
Use only facts supported by the returned evidence. If the evidence does not answer
the question, say that the available textbook content is insufficient.

Write a clear teaching-oriented answer. End with a Sources section containing the
section title and exact source URL for every excerpt used. Never invent a source or
citation. Do not expose raw relevance scores unless the user asks for them.
"""


def build_agent(settings: AgentSettings | None = None) -> CompiledStateGraph:
    """Build the local tool-calling LangGraph agent."""
    active_settings = settings or AgentSettings()
    model = ChatOllama(
        model=active_settings.ollama_llm_model,
        base_url=active_settings.ollama_llm_url,
        temperature=0,
        num_ctx=active_settings.ollama_llm_context_length,
    )
    model_with_tools = model.bind_tools([search_textbook])

    def call_model(state: MessagesState) -> dict[str, list[object]]:
        response = model_with_tools.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode([search_textbook]))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile()
