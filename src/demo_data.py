"""Bundled, network-free repository snapshot for the product demo."""

from __future__ import annotations

from .github_client import Issue, RepositoryContext, RepositoryMetadata


def get_demo_context() -> RepositoryContext:
    """Return a realistic snapshot that can be analyzed without API access."""

    repository = RepositoryMetadata(
        owner="streamlit",
        name="streamlit",
        full_name="streamlit/streamlit",
        html_url="https://github.com/streamlit/streamlit",
        description="A faster way to build and share data apps.",
        default_branch="develop",
        primary_language="Python",
        stars=45_629,
        forks=4_100,
        open_issues_count=930,
        license_name="Apache-2.0",
        topics=("python", "data-apps", "streamlit", "frontend"),
        is_archived=False,
        is_fork=False,
    )

    readme = """# Welcome to Streamlit

Streamlit is an open-source app framework for Machine Learning and Data Science teams.
Create interactive data apps in pure Python and share them in minutes.

The Python package exposes the public API used by app authors. A web and websocket
server coordinates script execution, while the React and TypeScript frontend renders
widgets and application state in the browser. Protocol definitions connect the Python
backend to the frontend. Documentation, examples, and a large automated test suite live
alongside the product code.

## Development

Contributors can work on Python unit tests, frontend tests, documentation, examples,
widgets, configuration, or the client-server protocol. See CONTRIBUTING.md for setup,
formatting, and pull-request guidance.
"""

    issues = (
        Issue(
            number=16680,
            title="Broken relative link in contributor instructions and stale dependency entries",
            html_url="https://github.com/streamlit/streamlit/issues/16680",
            body=(
                "A link in the contributor instructions points to the wrong relative path. "
                "The same small cleanup can remove stale frontend dependency exceptions."
            ),
            labels=("type:bug", "status:confirmed", "priority:P4", "area:contribution"),
            author="contributor",
            comments=1,
            created_at="2026-08-27T00:00:00Z",
            updated_at="2026-08-27T00:00:00Z",
        ),
        Issue(
            number=16679,
            title="Python unit tests are not portable to Windows",
            html_url="https://github.com/streamlit/streamlit/issues/16679",
            body=(
                "Several focused unit tests assume POSIX path separators or temporary-file "
                "behavior. Each failure has a small reproduction and expected outcome."
            ),
            labels=("type:bug", "area:windows", "status:confirmed", "priority:P4", "area:contribution"),
            author="contributor",
            comments=2,
            created_at="2026-08-27T00:00:00Z",
            updated_at="2026-08-27T00:00:00Z",
        ),
        Issue(
            number=16677,
            title="Color error message renders as one run-on line",
            html_url="https://github.com/streamlit/streamlit/issues/16677",
            body=(
                "A user-facing validation error loses the line breaks between its bullets. "
                "The expected text and the source error class are identified."
            ),
            labels=("type:bug", "status:confirmed", "priority:P3", "area:backend"),
            author="contributor",
            comments=0,
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
        ),
        Issue(
            number=16676,
            title="Fix a typo in the configuration deprecation warning",
            html_url="https://github.com/streamlit/streamlit/issues/16676",
            body="A stray character changes how a short warning is formatted. Add a regression assertion.",
            labels=("type:bug", "status:confirmed", "priority:P4", "feature:config"),
            author="contributor",
            comments=0,
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
        ),
        Issue(
            number=16674,
            title="Object rendering helper misses uppercase hexadecimal addresses on Windows",
            html_url="https://github.com/streamlit/streamlit/issues/16674",
            body="Extend one helper and its parameterized tests to recognize uppercase hexadecimal characters.",
            labels=("type:bug", "area:windows", "status:confirmed", "priority:P3"),
            author="contributor",
            comments=1,
            created_at="2026-08-26T00:00:00Z",
            updated_at="2026-08-26T00:00:00Z",
        ),
    )
    return RepositoryContext(repository=repository, readme=readme, issues=issues)


__all__ = ["get_demo_context"]

