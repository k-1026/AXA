"""ai/agent/eval/cases.py 의 안전 검사 문장을 pytest에서 항상 확인 (LLM 호출 없음)."""

import pytest

from ai.agent.eval.cases import INTENT_CASES, SAFETY_CASES
from ai.agent.tools.chat_tools import build_registry
from ai.llm.safety import check


@pytest.mark.parametrize("case", SAFETY_CASES, ids=lambda c: f"{c.lang}:{c.text[:30]}")
def test_safety_case(case):
    r = check(case.text, case.lang)
    assert r.action == case.action, f"{case.note}: {r.action} {r.categories}"
    assert set(case.categories) <= set(r.categories)


def test_intent_cases_refer_to_real_tools_and_have_unique_ids():
    names = set(build_registry().tools)
    ids = [c.id for c in INTENT_CASES]
    assert len(ids) == len(set(ids))
    for c in INTENT_CASES:
        assert set(c.must_call) <= names and set(c.must_not_call) <= names, c.id
        assert not set(c.must_call) & set(c.must_not_call), c.id
