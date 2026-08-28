from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from src.github_client import (
    GitHubClient,
    InvalidRepositoryURLError,
    parse_github_repo_url,
)


class FakeResponse:
    def __init__(self, payload: Any, *, status: int = 200) -> None:
        self.status = status
        self.headers: dict[str, str] = {}
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        return None


def test_parse_repository_url_normalizes_common_variants() -> None:
    cases = {
        "https://github.com/streamlit/streamlit": "streamlit/streamlit",
        "github.com/tiangolo/fastapi.git": "tiangolo/fastapi",
        "https://github.com/pallets/flask/issues/42": "pallets/flask",
        "http://www.github.com/encode/httpx/": "encode/httpx",
    }

    for value, expected in cases.items():
        assert parse_github_repo_url(value).full_name == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not a url",
        "https://gitlab.com/owner/repo",
        "git@github.com:owner/repo.git",
        "https://user:pass@github.com/owner/repo",
        "https://github.com/owner",
        "https://github.com//repo",
    ],
)
def test_parse_repository_url_rejects_unsafe_or_incomplete_values(value: str) -> None:
    with pytest.raises(InvalidRepositoryURLError):
        parse_github_repo_url(value)


def test_client_fetches_readme_and_filters_pull_requests() -> None:
    responses = iter(
        [
            {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
                "default_branch": "main",
                "private": False,
                "language": "Python",
                "stargazers_count": 42,
                "forks_count": 3,
                "open_issues_count": 2,
                "topics": ["demo"],
                "archived": False,
                "fork": False,
                "license": {"spdx_id": "MIT"},
            },
            {
                "encoding": "base64",
                "content": base64.b64encode(b"# Demo\n\nA useful project.").decode("ascii"),
            },
            [
                {
                    "number": 9,
                    "title": "A pull request",
                    "html_url": "https://github.com/owner/repo/pull/9",
                    "pull_request": {},
                },
                {
                    "number": 8,
                    "title": "Improve the setup guide",
                    "html_url": "https://github.com/owner/repo/issues/8",
                    "body": "Clarify one command.",
                    "labels": [{"name": "documentation"}],
                    "user": {"login": "octocat"},
                    "comments": 1,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                },
            ],
        ]
    )
    requested_urls: list[str] = []

    def opener(request: Any, *, timeout: float) -> FakeResponse:
        requested_urls.append(request.full_url)
        assert timeout == 4
        return FakeResponse(next(responses))

    context = GitHubClient(token="token", timeout=4, opener=opener).fetch(
        "https://github.com/owner/repo",
        issue_limit=1,
    )

    assert context.repository.full_name == "owner/repo"
    assert context.repository.primary_language == "Python"
    assert context.readme.startswith("# Demo")
    assert [issue.number for issue in context.issues] == [8]
    assert context.issues[0].labels == ("documentation",)
    assert any("/readme?ref=main" in url for url in requested_urls)

