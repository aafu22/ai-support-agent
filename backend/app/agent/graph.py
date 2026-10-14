"""The support agent as a LangGraph state machine.

guardrails -> intent -> (human/complaint -> escalate | smalltalk | out_of_scope | rewrite)
rewrite -> retrieve -> relevance -> (relevant -> generate | else no_answer/escalate)
generate -> (answered -> finalize | provider error -> service_error | NO_ANSWER -> no_answer/escalate)
"""
import uuid

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agent import nodes
from app.agent.state import AgentState


def _after_guardrails(state: AgentState) -> str:
    return "finalize" if state.get("outcome") == "blocked" else "intent"


def _after_intent(state: AgentState) -> str:
    return {
        "human_request": "escalate",
        "complaint": "escalate",
        "smalltalk": "smalltalk",
        "out_of_scope": "out_of_scope",
    }.get(state.get("intent", ""), "rewrite")


def _unknown_route(state: AgentState) -> str:
    # First miss: say "I don't know". Second consecutive miss: hand over to a human.
    return "escalate" if state.get("prev_unanswered") else "no_answer"


def _after_relevance(state: AgentState) -> str:
    return "generate" if state.get("relevant") else _unknown_route(state)


def _after_generate(state: AgentState) -> str:
    outcome = state.get("outcome")
    if outcome == "answered":
        return "finalize"
    if outcome == "error":  # provider failure: apologise, never escalate
        return "service_error"
    return _unknown_route(state)


def build_graph(db: Session, org_id: uuid.UUID):
    g = StateGraph(AgentState)
    g.add_node("guardrails", nodes.guardrails)
    g.add_node("intent", nodes.intent)
    g.add_node("smalltalk", nodes.smalltalk)
    g.add_node("out_of_scope", nodes.out_of_scope)
    g.add_node("rewrite", nodes.rewrite)
    g.add_node("retrieve", nodes.make_retrieve(db, org_id))
    g.add_node("relevance", nodes.relevance)
    g.add_node("generate", nodes.generate_answer)
    g.add_node("no_answer", nodes.no_answer)
    g.add_node("service_error", nodes.service_error)
    g.add_node("escalate", nodes.escalate)
    g.add_node("finalize", nodes.finalize)

    g.set_entry_point("guardrails")
    g.add_conditional_edges("guardrails", _after_guardrails, {"finalize": "finalize", "intent": "intent"})
    g.add_conditional_edges(
        "intent",
        _after_intent,
        {"escalate": "escalate", "smalltalk": "smalltalk", "out_of_scope": "out_of_scope", "rewrite": "rewrite"},
    )
    g.add_edge("rewrite", "retrieve")
    g.add_edge("retrieve", "relevance")
    g.add_conditional_edges(
        "relevance", _after_relevance, {"generate": "generate", "escalate": "escalate", "no_answer": "no_answer"}
    )
    g.add_conditional_edges(
        "generate",
        _after_generate,
        {
            "finalize": "finalize",
            "service_error": "service_error",
            "escalate": "escalate",
            "no_answer": "no_answer",
        },
    )
    for terminal in ("smalltalk", "out_of_scope", "no_answer", "service_error", "escalate"):
        g.add_edge(terminal, "finalize")
    g.add_edge("finalize", END)
    return g.compile()