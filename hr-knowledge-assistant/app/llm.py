"""LLM factory: one function returns a LangChain chat model for any provider.

Because every provider implements LangChain's `BaseChatModel` interface
(`invoke`, `stream`, `ainvoke` ...), the rest of the code never changes when
we swap Groq for Azure OpenAI or Gemini -- that is the main value LangChain
adds here.
"""
import re
from typing import Any, Iterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.config import Settings

STOPWORDS = set(
    "a an the is are was were be been do does did i me my we our you your it its of to in on for "
    "and or how what when where which who whom why can could should would will shall may might "
    "much many any some there this that these those with at by from as about per have has had get "
    "tell please am".split()
)


def _stem(w: str) -> str:
    # deliberately naive: "leaves" -> "leave", "policies" -> "policy"
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in STOPWORDS and len(w) > 1}


class MockChatModel(BaseChatModel):
    """Offline stand-in for an LLM so the whole system runs with no API key.

    It recognises which step is calling it from the `TASK:` line in the system
    prompt. For answer generation it is *extractive*: it picks the context
    lines with the most keyword overlap with the question and cites them.
    It is deliberately simple -- it exists for demos, tests and CI.
    """

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _respond(self, messages: list[BaseMessage]) -> str:
        system = str(messages[0].content) if messages else ""
        human = str(messages[-1].content) if messages else ""
        if "TASK: route" in system:
            return _rule_route(human.split("Message:")[-1])
        if "TASK: grade" in system:
            return _keyword_grade(human)
        if "TASK: rewrite" in system:
            return _rewrite(human)
        if "TASK: answer" in system:
            return _extractive_answer(human)
        return "Hello! I'm the Nimbus HR assistant. Ask me about leave, benefits, onboarding or other HR policies."

    def _generate(self, messages, stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self._respond(messages)))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs: Any) -> Iterator[ChatGenerationChunk]:
        for token in re.findall(r"\S+\s*", self._respond(messages)):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                run_manager.on_llm_new_token(token, chunk=chunk)
            yield chunk


def _rewrite(prompt: str) -> str:
    """Resolve pronouns in a follow-up by borrowing the topic of the previous user turn."""
    follow_up = prompt.split("Follow-up question:")[-1].strip()
    users = [l[5:].strip() for l in prompt.split("Follow-up question:")[0].splitlines() if l.startswith("User:")]
    if users and re.search(r"\b(it|that|this|they|them|those|these)\b", follow_up.lower()):
        topic = " ".join(sorted(keywords(users[-1]) - keywords(follow_up)))
        return f"{follow_up} ({topic})"
    return follow_up


def _rule_route(message: str) -> str:
    m = message.lower()
    if re.search(r"\b(human|hr person|real person|raise (a )?ticket|escalate|talk to hr|contact hr|complain)\b", m):
        return "escalate"
    if re.search(r"\b(my|i have|do i have)\b.*\b(leave balance|leaves left|balance|remaining leave|leaves remaining)\b", m) or (
        "balance" in m and "my" in m
    ):
        return "leave_balance"
    if re.fullmatch(r"\s*(hi|hello|hey|thanks|thank you|good (morning|evening|afternoon)|bye)[!. ]*\s*", m):
        return "chitchat"
    return "policy_question"


GENERIC = {"policy", "nimbus", "company", "rule", "allowed", "eligible", "allowance", "leave", "day"}


def _keyword_grade(prompt: str) -> str:
    question = keywords(prompt.split("Question:")[-1]) - GENERIC
    context = keywords(prompt.split("Context:")[-1].split("Question:")[0])
    if not question:
        return "yes"
    return "yes" if len(question & context) / len(question) >= 0.5 else "no"


def _extractive_answer(prompt: str) -> str:
    question = prompt.split("Question:")[-1].strip()
    context = prompt.split("Context:")[-1].split("Question:")[0]
    q = keywords(question)
    scored: list[tuple[int, int, str]] = []
    current_src = 0
    skip_heading = False
    for line in context.splitlines():
        src = re.match(r"\[(\d+)\]", line)
        if src:
            current_src = int(src.group(1))
            skip_heading = True  # first line of every chunk is its heading path
            continue
        if skip_heading:
            skip_heading = False
            continue
        text = line.strip(" -#*")
        if len(text) < 15:
            continue
        overlap = len(q & keywords(text))
        if overlap:
            scored.append((overlap, current_src, text.replace("**", "")))
    if not scored:
        return "I couldn't find this in the HR policies. Please contact your HR Business Partner."
    scored.sort(key=lambda s: -s[0])
    best = [s for s in scored[:2] if s[0] >= max(1, scored[0][0] - 1)]
    return " ".join(f"{text} [{src}]" for _, src, text in best)


def get_llm(settings: Settings, streaming: bool = True) -> BaseChatModel:
    provider = settings.resolved_llm_provider()
    t = settings.llm_temperature
    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=settings.llm_model or "llama-3.3-70b-versatile", temperature=t, api_key=settings.groq_api_key)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.llm_model or "gpt-4o-mini", temperature=t, streaming=streaming)
    if provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.openai_api_version,
            temperature=t,
        )
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=settings.llm_model or "gemini-2.0-flash", temperature=t)
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.llm_model or "llama3.2", base_url=settings.ollama_base_url, temperature=t)
    if provider == "mock":
        return MockChatModel()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
