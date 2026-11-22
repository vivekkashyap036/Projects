"""Phase 5: explanation agent.

Input: ONLY the /score output. Output: a short plain-language explanation for the
vendor in English and Hindi.

Safety design
* `build_llm_input` whitelists fields from the score output. No vendor_id, no raw
  income series, no loan amount: nothing personal reaches the LLM.
* The LLM must return JSON {"en": ..., "hi": ...}.
* `validate` rejects any output that contains a number not present in the input,
  promises approval, gives advice on gaming the score, or mentions facts the input
  does not contain (bureau, collateral, interest rate, ...). Rejected output falls
  back to the deterministic template, which passes the same validator.
"""
from __future__ import annotations

import json
import re
from typing import Any

from vendorscore.agents.llm import LLMProvider, LLMUnavailable, get_provider
from vendorscore.logging_setup import get_logger

log = get_logger(__name__)

MAX_CHARS = 1400

SYSTEM_PROMPT = """You write short, kind, plain-language explanations of a cash-flow credit score for a small street vendor in India.

You receive a JSON object. It is the ONLY source of facts. Rules:
1. Use only the reasons and numbers given in the JSON. Do not add any other number, date, amount, percentage or fact.
2. Do not promise or predict approval, a loan, a limit or a rate. The lender makes the decision; a person reviews the application.
3. Do not give advice on how to raise or change the score, and do not suggest changing how payments are received.
4. Do not mention credit bureaus, collateral, interest rates, documents, or anything else that is not in the JSON.
5. Write 4 to 6 short sentences. Simple words. No headings, no bullet points.
6. Write the same content twice: English in "en" and simple Hindi (Devanagari) in "hi". Keep digits as digits.
Return ONLY a JSON object: {"en": "...", "hi": "..."}"""

BAND_TEXT = {
    "approve": ("The score is in the range where the lender usually moves the application forward. The lender still makes the final decision.",
                "स्कोर उस दायरे में है जहाँ आम तौर पर ऋणदाता आवेदन को आगे बढ़ाता है। अंतिम निर्णय ऋणदाता ही लेता है।"),
    "review": ("A person at the lender will look at the application more closely before any decision.",
               "किसी भी निर्णय से पहले ऋणदाता का एक व्यक्ति आवेदन को ध्यान से देखेगा।"),
    "decline": ("The score is in a lower range. A person at the lender will look at the application and make the decision.",
                "स्कोर निचले दायरे में है। ऋणदाता का एक व्यक्ति आवेदन देखकर निर्णय लेगा।"),
}

# ---- validator vocabulary ----------------------------------------------------
PROMISE_PATTERNS = [
    r"\bapproved\b", r"\bapproval\b", r"\bguarantee", r"\bassured\b", r"\bdefinitely\b", r"\bcertainly\b",
    r"\bwill (?:get|receive|be given) (?:the|a|your)? ?loan", r"\bsanction", r"\beligible\b",
    r"गारंटी", r"पक्का", r"मंज़ूर", r"मंजूर", r"स्वीकृत", r"ज़रूर मिलेगा", r"जरूर मिलेगा", r"निश्चित",
]
GAMING_PATTERNS = [
    r"\b(?:raise|increase|improve|boost|lift|game|beat)\b[^.]{0,40}\bscore", r"\btrick", r"\bsplit\b",
    r"\bself[- ]transfer", r"\bsend money to yourself\b", r"\bask (?:friends|family|relatives|customers)\b",
    r"\bfake\b", r"\bmore (?:upi )?transactions\b", r"\bto get a (?:better|higher) score\b", r"\byou should\b",
    r"\btry to\b", r"स्कोर बढ़ा", r"स्कोर सुधार", r"नकली", r"खुद को पैसे",
]
EXTERNAL_TERMS = [
    "cibil", "bureau", "collateral", "guarantor", "interest rate", "gst", "aadhaar", "pan card", "bank statement",
    "income tax", "credit history", "ब्याज", "गारंटर", "सिबिल",
]
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[float]:
    out: set[float] = set()
    for m in _NUM_RE.findall(text.translate(_DEVANAGARI_DIGITS)):
        m = m.rstrip(",.")
        try:
            out.add(round(float(m.replace(",", "")), 4))
        except ValueError:
            continue
    return out


# ---- input -------------------------------------------------------------------
def build_llm_input(score_output: dict[str, Any]) -> dict[str, Any]:
    """Whitelist only what the explanation needs. Nothing personal is passed on."""

    def slim(items: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [{"code": str(r["code"]), "text_en": str(r["text_en"]), "text_hi": str(r["text_hi"])} for r in items]

    return {
        "score": int(score_output["score"]),
        "score_scale": "300 to 900",
        "band": str(score_output["band"]),
        "band_meaning_en": BAND_TEXT[str(score_output["band"])][0],
        "band_meaning_hi": BAND_TEXT[str(score_output["band"])][1],
        "reasons_that_raise_risk": slim(score_output.get("reasons", [])),
        "things_that_helped": slim(score_output.get("strengths", [])),
    }


# ---- validator ---------------------------------------------------------------
def validate(output: dict[str, Any], llm_input: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    if not isinstance(output, dict) or set(output) != {"en", "hi"}:
        return {"ok": False, "problems": ["output must be a JSON object with exactly 'en' and 'hi'"]}
    en, hi = output["en"], output["hi"]
    if not (isinstance(en, str) and isinstance(hi, str) and en.strip() and hi.strip()):
        return {"ok": False, "problems": ["'en' and 'hi' must be non-empty strings"]}
    if len(en) > MAX_CHARS or len(hi) > MAX_CHARS:
        problems.append("too long")
    if not re.search(r"[ऀ-ॿ]", hi):
        problems.append("'hi' is not in Devanagari")

    source = json.dumps(llm_input, ensure_ascii=False)
    allowed = _numbers(source)
    for lang, text in (("en", en), ("hi", hi)):
        extra = sorted(_numbers(text) - allowed)
        if extra:
            problems.append(f"{lang}: numbers not in the input: {extra}")
        low = text.lower()
        for pat in PROMISE_PATTERNS:
            if re.search(pat, low):
                problems.append(f"{lang}: promise/approval language ({pat})")
        for pat in GAMING_PATTERNS:
            if re.search(pat, low):
                problems.append(f"{lang}: advice on changing the score ({pat})")
        for term in EXTERNAL_TERMS:
            if term in low and term not in source.lower():
                problems.append(f"{lang}: mentions '{term}', which is not in the input")
    if str(llm_input["score"]) not in en.translate(_DEVANAGARI_DIGITS):
        problems.append("en: does not state the score")
    return {"ok": not problems, "problems": problems}


# ---- template ----------------------------------------------------------------
def template_explanation(llm_input: dict[str, Any]) -> dict[str, str]:
    band = llm_input["band"]
    en = [f"Your cash-flow score is {llm_input['score']}, on a scale of 300 to 900.", llm_input["band_meaning_en"]]
    hi = [f"आपका कैश-फ़्लो स्कोर {llm_input['score']} है (300 से 900 के पैमाने पर)।", llm_input["band_meaning_hi"]]
    if llm_input["reasons_that_raise_risk"]:
        en.append("What lowered the score: " + " ".join(r["text_en"] for r in llm_input["reasons_that_raise_risk"]))
        hi.append("स्कोर कम होने के कारण: " + " ".join(r["text_hi"] for r in llm_input["reasons_that_raise_risk"]))
    if llm_input["things_that_helped"]:
        en.append("What helped: " + " ".join(r["text_en"] for r in llm_input["things_that_helped"]))
        hi.append("जिससे मदद मिली: " + " ".join(r["text_hi"] for r in llm_input["things_that_helped"]))
    if band != "approve":
        en.append("You can ask the lender to explain any of these points.")
        hi.append("आप इनमें से किसी भी बात के बारे में ऋणदाता से पूछ सकते हैं।")
    return {"en": " ".join(en), "hi": " ".join(hi)}


def _parse(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start : end + 1])


# ---- agent -------------------------------------------------------------------
def explain(score_output: dict[str, Any], provider: LLMProvider | None = None) -> dict[str, Any]:
    llm_input = build_llm_input(score_output)
    provider = provider or get_provider()
    attempt: dict[str, Any] = {"provider": provider.name, "used": False}
    if provider.name != "none":
        try:
            raw = provider.generate(SYSTEM_PROMPT, json.dumps(llm_input, ensure_ascii=False))
            parsed = _parse(raw)
            check = validate(parsed, llm_input)
            attempt.update(used=True, validator=check)
            if check["ok"]:
                return {"en": parsed["en"], "hi": parsed["hi"], "source": "llm", "provider": provider.name,
                        "validator": check, "llm_input": llm_input}
            log.warning("LLM explanation rejected by validator: %s", check["problems"])
        except (LLMUnavailable, ValueError, KeyError, TypeError) as exc:
            attempt.update(used=True, error=str(exc)[:200])
            log.warning("LLM explanation failed (%s); using template", exc)

    tpl = template_explanation(llm_input)
    check = validate(tpl, llm_input)
    if not check["ok"]:  # should never happen; tests guard this
        log.error("template failed validation: %s", check["problems"])
    return {**tpl, "source": "template", "provider": "template", "validator": check,
            "llm_attempt": attempt, "llm_input": llm_input}
