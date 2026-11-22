"""Phase 5: explanation grounding, privacy, fallback behaviour."""
from __future__ import annotations

import json

import numpy as np
import pytest

from vendorscore.agents import explainer as ex
from vendorscore.agents.llm import LLMUnavailable, NoProvider


class FakeProvider:
    name = "fake"

    def __init__(self, reply: str | Exception) -> None:
        self.reply = reply
        self.seen: list[str] = []

    def generate(self, system: str, user: str) -> str:
        self.seen.append(user)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture(scope="module")
def outputs(trained):
    scorer, _, _ = trained
    rng = np.random.default_rng(5)
    outs = []
    for level, emi, gap in [(300, 9000, 15), (1500, 3000, 0), (800, 6000, 5), (2500, 2000, 0), (200, 12000, 25)]:
        s = level * np.exp(rng.normal(0, 0.35, 180))
        s[50 : 50 + gap] = 0
        s[-30:] *= 0.6 if gap else 1.1
        outs.append({"vendor_id": "PRIVATE-77", **scorer.score_one(s, emi)})
    return outs


def test_llm_input_has_no_personal_data(outputs):
    inp = ex.build_llm_input(outputs[0])
    blob = json.dumps(inp, ensure_ascii=False)
    assert "PRIVATE-77" not in blob and "vendor_id" not in blob
    assert set(inp) == {"score", "score_scale", "band", "band_meaning_en", "band_meaning_hi",
                        "reasons_that_raise_risk", "things_that_helped"}


def test_template_passes_validator_for_all_bands(outputs):
    bands = set()
    for o in outputs:
        inp = ex.build_llm_input(o)
        tpl = ex.template_explanation(inp)
        assert ex.validate(tpl, inp)["ok"], ex.validate(tpl, inp)["problems"]
        bands.add(o["band"])
    assert len(bands) >= 2


def _good(inp):
    return {"en": f"Your score is {inp['score']}. A person at the lender will look at it.",
            "hi": f"आपका स्कोर {inp['score']} है। ऋणदाता का एक व्यक्ति इसे देखेगा।"}


@pytest.mark.parametrize("bad_en,why", [
    ("Your score is {s}. You earn about Rs 54321 a month.", "numbers not in the input"),
    ("Your score is {s}. Your loan is guaranteed.", "promise"),
    ("Your score is {s}. You will be approved soon.", "promise"),
    ("Your score is {s}. To raise your score, ask friends to send you UPI payments.", "changing the score"),
    ("Your score is {s}. Your CIBIL record is clean.", "cibil"),
    ("Your score is {s}. Interest rate will be 18%.", "numbers not in the input"),
])
def test_validator_rejects_ungrounded_output(outputs, bad_en, why):
    inp = ex.build_llm_input(outputs[0])
    out = _good(inp)
    out["en"] = bad_en.format(s=inp["score"])
    res = ex.validate(out, inp)
    assert not res["ok"]
    assert any(why in p for p in res["problems"]), res["problems"]


def test_validator_checks_hindi_digits(outputs):
    inp = ex.build_llm_input(outputs[0])
    out = _good(inp)
    out["hi"] = "आपका स्कोर ७७७७ है।"
    assert not ex.validate(out, inp)["ok"]


def test_validator_accepts_grounded_output(outputs):
    inp = ex.build_llm_input(outputs[1])
    assert ex.validate(_good(inp), inp)["ok"]


def test_bad_llm_output_falls_back_to_template(outputs):
    inp = ex.build_llm_input(outputs[0])
    p = FakeProvider(json.dumps({"en": f"Score {inp['score']}. You are approved!", "hi": "आप स्वीकृत हैं।"}))
    res = ex.explain(outputs[0], provider=p)
    assert res["source"] == "template"
    assert res["validator"]["ok"]
    assert res["llm_attempt"]["validator"]["ok"] is False
    assert "PRIVATE-77" not in p.seen[0]


def test_llm_failure_falls_back(outputs):
    res = ex.explain(outputs[2], provider=FakeProvider(LLMUnavailable("timeout")))
    assert res["source"] == "template" and res["validator"]["ok"]
    res = ex.explain(outputs[2], provider=FakeProvider("not json at all"))
    assert res["source"] == "template"


def test_good_llm_output_is_used(outputs):
    inp = ex.build_llm_input(outputs[1])
    res = ex.explain(outputs[1], provider=FakeProvider("```json\n" + json.dumps(_good(inp), ensure_ascii=False) + "\n```"))
    assert res["source"] == "llm"


def test_no_provider_uses_template_and_is_deterministic(outputs):
    a = ex.explain(outputs[3], provider=NoProvider())
    b = ex.explain(outputs[3], provider=NoProvider())
    assert a == b and a["source"] == "template"
