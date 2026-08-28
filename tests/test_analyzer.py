from __future__ import annotations

import pytest

from src.analyzer import EntryMap, build_demo_entry_map
from src.demo_data import get_demo_context


def test_demo_analysis_is_deterministic_and_complete() -> None:
    context = get_demo_context()

    first = build_demo_entry_map(context)
    second = build_demo_entry_map(context.to_dict())

    assert first == second
    assert isinstance(first, EntryMap)
    assert 3 <= len(first.components) <= 5
    assert len(first.seams) >= 1
    assert len(first.beginner_issues) == 3
    assert len({issue.issue_number for issue in first.beginner_issues}) == 3
    supplied_numbers = {issue.number for issue in context.issues}
    assert {issue.issue_number for issue in first.beginner_issues} <= supplied_numbers


def test_demo_analysis_uses_honest_placeholders_when_issues_are_missing() -> None:
    context = get_demo_context().to_dict()
    context["issues"] = context["issues"][:1]

    result = build_demo_entry_map(context)

    assert len(result.beginner_issues) == 3
    assert sum(item.issue_number == 0 for item in result.beginner_issues) == 2
    assert "did not contain enough" in result.beginner_issues[-1].why


def test_entry_map_rejects_duplicate_real_issue_numbers() -> None:
    context = get_demo_context()
    result = build_demo_entry_map(context)
    payload = result.model_dump()
    payload["beginner_issues"][1]["issue_number"] = payload["beginner_issues"][0]["issue_number"]

    with pytest.raises(ValueError, match="distinct"):
        EntryMap.model_validate(payload)

