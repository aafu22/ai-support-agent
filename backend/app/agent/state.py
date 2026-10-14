from typing import TypedDict


class AgentState(TypedDict, total=False):
    # inputs
    question: str
    history: list[dict]  # [{"role": "user"|"assistant", "content": str}]
    bot_name: str
    prev_unanswered: bool  # previous AI turn already failed to answer
    # working data
    intent: str
    query: str
    retrieved: list[dict]
    relevant: list[dict]
    top_score: float
    # outputs
    outcome: str  # answered | no_answer | escalate | smalltalk | out_of_scope | blocked
    reply: str
    sources: list[dict]
    reason: str
