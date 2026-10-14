import json
import logging
import re
import uuid

from sqlalchemy.orm import Session

from app.agent import prompts
from app.agent.state import AgentState
from app.core.config import settings
from app.services.providers.embeddings import embed_texts
from app.services.providers.llm import LLMError, generate
from app.services.retrieval import search_chunks

log = logging.getLogger(__name__)


INJECTION_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"ignore (all |any |the )?(previous|prior|above|earlier|your) (instructions|prompts|rules)",
        r"disregard (all |any |the )?(previous|prior|above|system|your)\b",
        r"(reveal|show|print|repeat|output) (me )?(your|the) (system |hidden |initial )?(prompt|instructions|rules)",
        r"you are now (in )?(dan|developer mode)",
        r"\bjailbreak\b",
    )
]

HUMAN_REQUEST = re.compile(
    r"\b(talk|speak|chat|connect|transfer|escalate)\b.{0,30}\b(human|person|agent|representative|someone|manager|staff)\b"
    r"|\b(human|live|real) (agent|person|support|being)\b|\bcustomer service rep",
    re.I,
)

INTENTS = {
    "knowledge_question",
    "human_request",
    "complaint",
    "smalltalk",
    "out_of_scope",
}

NO_ANSWER_TEXT = (
    "I'm sorry, I couldn't find that in our knowledge base. Could you rephrase your question? "
    "If you'd prefer, ask me to connect you with a human team member."
)

ESCALATE_TEXT = (
    "I'm connecting you with a member of our support team. They'll reply in this chat as soon as they can. "
    "You can leave your email below so we can reach you if you close this page."
)


def guardrails(state: AgentState) -> dict:
    """Block common prompt-injection attempts."""
    if any(p.search(state["question"]) for p in INJECTION_PATTERNS):
        return {
            "outcome": "blocked",
            "reply": (
                "I can only help with questions about our products and services. "
                "How can I help with that?"
            ),
        }
    return {}


def intent(state: AgentState) -> dict:
    """Classify the message, using a safe default if classification fails."""
    question = state["question"]

    if HUMAN_REQUEST.search(question):
        return {
            "intent": "human_request",
            "reason": "Customer asked for a human",
        }

    label = "knowledge_question"

    try:
        raw = generate(
            prompts.INTENT_SYSTEM,
            [{"role": "user", "content": question}],
            max_tokens=40,
            temperature=0,
        )
        match = re.search(r"\{.*?\}", raw, re.S)
        candidate = json.loads(match.group(0)).get("intent") if match else None

        if candidate in INTENTS:
            label = candidate

    except (LLMError, ValueError, AttributeError):
        # Classification is best-effort. Fall back to the knowledge base.
        pass

    reason = (
        "Customer appears frustrated or reported a serious problem"
        if label == "complaint"
        else ""
    )

    return {"intent": label, "reason": reason}


def rewrite(state: AgentState) -> dict:
    """Rewrite follow-up questions using recent conversation history."""
    history = state.get("history") or []

    if not history:
        return {"query": state["question"]}

    transcript = "\n".join(
        f"{m['role']}: {m['content'][:300]}"
        for m in history[-6:]
    )

    try:
        out = generate(
            prompts.REWRITE_SYSTEM,
            [
                {
                    "role": "user",
                    "content": (
                        f"Conversation:\n{transcript}\n\n"
                        f"Latest message: {state['question']}"
                    ),
                }
            ],
            max_tokens=80,
            temperature=0,
        )

        query = out.strip().strip('"')

        return {
            "query": (
                query
                if 0 < len(query) <= 300
                else state["question"]
            )
        }

    except LLMError:
        return {"query": state["question"]}


def make_retrieve(db: Session, org_id: uuid.UUID):
    """Create a retrieval node scoped to the current organization."""

    def retrieve(state: AgentState) -> dict:
        vector = embed_texts(
            [state["query"]],
            is_query=True,
        )[0]

        chunks = search_chunks(
            db,
            org_id,
            vector,
            settings.retrieval_top_k,
        )

        return {"retrieved": [c.to_dict() for c in chunks]}

    return retrieve


def relevance(state: AgentState) -> dict:
    """Keep retrieved chunks above the configured relevance threshold."""
    retrieved = state.get("retrieved") or []

    relevant = [
        chunk
        for chunk in retrieved
        if chunk["score"] >= settings.relevance_threshold
    ]

    return {
        "relevant": relevant,
        "top_score": retrieved[0]["score"] if retrieved else 0.0,
    }


def _clean_attr(value: str) -> str:
    """Make source metadata safer to include in source delimiters."""
    return value.replace('"', "'").replace("<", "").replace(">", "")


_CITATION = re.compile(r"[ \t]*\[\s*(\d+(?:\s*[,;]\s*\d+)*)\s*\]")


def _cited_numbers(answer: str, source_count: int) -> set[int]:
    """Source numbers the answer cites, e.g. [1], [2] or [1, 2]."""
    numbers = {
        int(num)
        for match in _CITATION.finditer(answer)
        for num in re.findall(r"\d+", match.group(1))
    }
    return {num for num in numbers if 1 <= num <= source_count}


def _strip_citations(answer: str, source_count: int) -> str:
    """Remove [n] markers from the visible text; the UI lists sources separately.

    Any bracketed number under 100 counts as a citation, including invented ones like [9].
    Larger numbers such as the year [2024] are left alone."""

    def drop(match: re.Match) -> str:
        nums = [int(num) for num in re.findall(r"\d+", match.group(1))]
        return "" if all(num < 100 for num in nums) else match.group(0)

    text = _CITATION.sub(drop, answer)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r" +([,.;!?])", r"\1", text).strip()


def generate_answer(state: AgentState) -> dict:
    """Generate a grounded answer and preserve its source metadata."""
    chunks = state.get("relevant") or []

    if not chunks:
        return {"outcome": "no_answer"}

    blocks = []

    for index, chunk in enumerate(chunks, 1):
        body = chunk["content"].replace(
            "</source",
            "< /source",
        )

        title = _clean_attr(chunk["title"])
        page = chunk.get("page") or ""

        blocks.append(
            f'<source id="{index}" title="{title}" page="{page}">\n'
            f"{body}\n"
            f"</source>"
        )

    user_turn = (
        "<sources>\n"
        + "\n".join(blocks)
        + "\n</sources>\n\n"
        + f"Customer question: {state['question']}"
    )

    history = (
        state.get("history") or []
    )[-settings.max_history_messages :]

    try:
        answer = generate(
            prompts.ANSWER_SYSTEM.replace(
                "{bot_name}",
                state.get("bot_name", "Support Assistant"),
            ),
            history + [{"role": "user", "content": user_turn}],
        )
    except LLMError as exc:
        # A provider failure is NOT "the knowledge base has no answer".
        log.warning("Answer generation failed: %s", exc)
        return {"outcome": "error"}

    if (
        not answer
        or answer.strip().upper().startswith("NO_ANSWER")
        or len(answer.strip()) < 3
    ):
        return {"outcome": "no_answer"}

    # Work out which sources were cited, then hide the [n] markers from the text.
    cited = _cited_numbers(answer, len(chunks))
    answer = _strip_citations(answer, len(chunks))

    used = (
        [
            index
            for index in range(1, len(chunks) + 1)
            if index in cited
        ]
        or list(range(1, len(chunks) + 1))
    )

    sources = [
        {
            "id": index,
            "document_id": chunks[index - 1]["document_id"],
            "title": chunks[index - 1]["title"],
            "page": chunks[index - 1]["page"],
            "snippet": chunks[index - 1]["content"][:220],
        }
        for index in used
    ]

    return {
        "outcome": "answered",
        "reply": answer,
        "sources": sources,
    }


def smalltalk(state: AgentState) -> dict:
    """Handle greetings and casual messages without document retrieval."""
    try:
        reply = generate(
            prompts.SMALLTALK_SYSTEM.replace(
                "{bot_name}",
                state.get("bot_name", "Support Assistant"),
            ),
            [{"role": "user", "content": state["question"]}],
            max_tokens=100,
            temperature=0.5,
        )
    except LLMError:
        reply = "Hi! How can I help you today?"

    return {
        "outcome": "smalltalk",
        "reply": reply or "Hi! How can I help you today?",
    }


def out_of_scope(state: AgentState) -> dict:
    """Politely redirect questions unrelated to the supported business."""
    return {
        "outcome": "out_of_scope",
        "reply": (
            "I can only help with questions about this business and its services. "
            "Is there something about those I can help with?"
        ),
    }


def no_answer(state: AgentState) -> dict:
    """Return a helpful response when the knowledge base cannot answer."""
    return {
        "outcome": "no_answer",
        "reply": NO_ANSWER_TEXT,
    }


def escalate(state: AgentState) -> dict:
    """Route a conversation to a human support agent."""
    reason = state.get("reason") or (
        "AI could not answer after repeated attempts"
    )

    return {
        "outcome": "escalate",
        "reply": ESCALATE_TEXT,
        "reason": reason,
    }


def service_error(state: AgentState) -> dict:
    """The AI provider failed. Apologise; do not count it as a knowledge gap."""
    return {
        "outcome": "error",
        "reply": (
            "Sorry, I'm having trouble answering right now. "
            "Please try again in a moment."
        ),
    }


def finalize(state: AgentState) -> dict:
    """Ensure the graph returns a consistent result shape."""
    return {
        "reply": state.get("reply") or NO_ANSWER_TEXT,
        "sources": state.get("sources") or [],
        "outcome": state.get("outcome") or "no_answer",
    }