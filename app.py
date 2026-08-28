"""Streamlit entry point for First Contribution Map."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Iterable

import streamlit as st
from dotenv import load_dotenv

from src.analyzer import (
    AnalyzerError,
    EntryMap,
    analyze_repository,
    build_demo_entry_map,
)
from src.demo_data import get_demo_context
from src.github_client import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubNetworkError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    InvalidRepositoryURLError,
    PrivateRepositoryError,
    RepositoryContext,
    parse_github_repo_url,
)


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="First Contribution Map",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://github.com/",
        "About": "Turn a public repository README and recent issues into a practical first-contribution map.",
    },
)


def _load_css() -> None:
    st.markdown(
        f"<style>{(ROOT / 'assets' / 'styles.css').read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


def _escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _split_named_item(value: str) -> tuple[str, str]:
    for separator in (" — ", ": ", " – "):
        if separator in value:
            name, description = value.split(separator, 1)
            return name.strip(), description.strip()
    return value.strip(), "A likely boundary inferred from the available repository context."


def _compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _top_bar() -> None:
    st.markdown(
        """
        <div class="fcm-topbar">
          <div class="fcm-brand">
            <span class="fcm-mark">&lt;/&gt;</span>
            <span>First Contribution Map</span>
          </div>
          <span class="fcm-proof-badge"><span class="fcm-proof-dot"></span>POC · README + issues</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _hero() -> None:
    st.markdown(
        """
        <section class="fcm-hero">
          <div class="fcm-eyebrow">Repository onboarding, decoded</div>
          <h1>Find your first <span>meaningful contribution.</span></h1>
          <p>Paste a public GitHub repository. Get the project context, likely architecture,
          and three approachable issues—before getting lost in the codebase.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _repository_form() -> tuple[bool, bool, str]:
    with st.form("repository_form", clear_on_submit=False):
        st.markdown('<div class="fcm-input-label">Public GitHub repository</div>', unsafe_allow_html=True)
        repo_url = st.text_input(
            "Public GitHub repository",
            key="repository_url",
            label_visibility="collapsed",
            placeholder="https://github.com/owner/repository",
        )
        primary, secondary = st.columns([2.15, 1])
        with primary:
            analyze_clicked = st.form_submit_button(
                "Generate contribution map",
                type="primary",
                use_container_width=True,
            )
        with secondary:
            demo_clicked = st.form_submit_button(
                "View demo",
                use_container_width=True,
            )
    st.markdown(
        """
        <div class="fcm-privacy-line">
          <span>Public metadata only</span>
          <span>No repository clone</span>
          <span>No writes to GitHub</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return analyze_clicked, demo_clicked, repo_url


def _empty_state() -> None:
    st.markdown(
        """
        <section class="fcm-empty">
          <div class="fcm-empty-title">From unfamiliar codebase to a clear first step</div>
          <div class="fcm-step-grid">
            <article class="fcm-step">
              <div class="fcm-step-no">01</div>
              <strong>Paste a repository</strong>
              <p>Use any public GitHub URL. Nested links such as an issues page work too.</p>
            </article>
            <article class="fcm-step">
              <div class="fcm-step-no">02</div>
              <strong>We read the context</strong>
              <p>The prototype reviews the README and up to ten recent open issues.</p>
            </article>
            <article class="fcm-step">
              <div class="fcm-step-no">03</div>
              <strong>Start with confidence</strong>
              <p>See the project map, likely seams, and three grounded starting points.</p>
            </article>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _analyze_live_repository(
    repo_url: str,
    *,
    gemini_key: str,
    github_token: str,
    model: str,
) -> tuple[RepositoryContext, EntryMap, str, str]:
    """Fetch and analyze a live repository, returning an optional fallback note."""

    parse_github_repo_url(repo_url)
    client = GitHubClient(token=github_token or None)

    with st.status("Building your contribution map…", expanded=True) as status:
        st.write("Connecting to GitHub…")
        context = client.fetch_repository(repo_url, issue_limit=10)
        st.write("README loaded." if context.readme else "No README found; using repository metadata and issues.")
        st.write(f"Reviewed {len(context.issues)} recent open issue{'s' if len(context.issues) != 1 else ''}.")

        use_gemini = bool(gemini_key) and len(context.issues) >= 3
        fallback_note = ""
        if use_gemini:
            st.write("Asking Gemini to rank approachable first contributions…")
            try:
                entry_map = analyze_repository(context, api_key=gemini_key, model=model)
                mode = "Gemini analysis"
            except AnalyzerError as exc:
                entry_map = build_demo_entry_map(context)
                mode = "Local fallback"
                fallback_note = f"Gemini was unavailable, so this map uses the local heuristic: {exc}"
        else:
            st.write("Building a local, deterministic preview…")
            entry_map = build_demo_entry_map(context)
            mode = "Local analysis"

        status.update(label="Contribution map ready", state="complete", expanded=False)
    return context, entry_map, mode, fallback_note


def _load_demo() -> tuple[RepositoryContext, EntryMap, str, str]:
    with st.status("Loading the guided demo…", expanded=True) as status:
        st.write("Opening a bundled Streamlit repository snapshot…")
        context = get_demo_context()
        st.write("Reviewing five representative open issues…")
        entry_map = build_demo_entry_map(context)
        status.update(label="Demo contribution map ready", state="complete", expanded=False)
    return (
        context,
        entry_map,
        "Guided demo",
        "This guided demo uses a bundled repository snapshot and local analysis; live repository contents may differ.",
    )


def _store_result(
    context: RepositoryContext,
    entry_map: EntryMap,
    mode: str,
    note: str,
) -> None:
    st.session_state["repository_context"] = context
    st.session_state["entry_map"] = entry_map
    st.session_state["analysis_mode"] = mode
    st.session_state["analysis_note"] = note


def _show_error(exc: Exception) -> None:
    if isinstance(exc, InvalidRepositoryURLError):
        message = "Enter a public GitHub URL like https://github.com/owner/repository."
    elif isinstance(exc, (GitHubNotFoundError, PrivateRepositoryError)):
        message = "We couldn’t access this repository. Check that it exists and is public."
    elif isinstance(exc, GitHubRateLimitError):
        message = str(exc)
    elif isinstance(exc, GitHubAuthenticationError):
        message = "GitHub rejected the access token. Check it, or clear the field to use anonymous access."
    elif isinstance(exc, GitHubNetworkError):
        message = "GitHub could not be reached. Check your connection and try again."
    elif isinstance(exc, GitHubAPIError):
        message = "GitHub returned an unexpected response. Please try again shortly."
    elif isinstance(exc, AnalyzerError):
        message = str(exc)
    else:
        message = "Something unexpected happened while building the map. Please try again."
    st.error(message, icon="⚠️")


def _render_source_strip(context: RepositoryContext, mode: str) -> None:
    repo = context.repository
    readme_state = "README analyzed" if context.readme else "README unavailable"
    repo_href = _escape(repo.html_url)
    st.markdown(
        f"""
        <div class="fcm-source-strip">
          <div>
            <div class="fcm-repo-name">{_escape(repo.full_name)}</div>
            <div class="fcm-source-meta">{readme_state} · {len(context.issues)} recent issues reviewed ·
              <a href="{repo_href}" target="_blank" rel="noopener noreferrer">Open repository ↗</a>
            </div>
          </div>
          <span class="fcm-status-pill">✓ {_escape(mode)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _chips(values: Iterable[str]) -> str:
    return "".join(f'<span class="fcm-chip">{_escape(value)}</span>' for value in values if value)


def _render_summary(context: RepositoryContext, entry_map: EntryMap) -> None:
    repo = context.repository
    chip_values = [
        repo.primary_language or "",
        *repo.topics[:4],
        f"★ {_compact_number(repo.stars)}" if repo.stars else "",
        repo.license_name or "",
    ]
    st.markdown(
        f"""
        <div class="fcm-section-kicker">01 · Project</div>
        <h2 class="fcm-section-heading">What this project does</h2>
        <div class="fcm-summary-card">
          <p>{_escape(entry_map.summary)}</p>
          <div class="fcm-chips">{_chips(chip_values)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_architecture(entry_map: EntryMap) -> None:
    st.markdown(
        """
        <div class="fcm-section-kicker">02 · Architecture</div>
        <h2 class="fcm-section-heading">Where the project fits together</h2>
        <p class="fcm-section-intro">These boundaries are inferred from the README, not a full source-code scan.
        Treat them as a fast orientation map and confirm them in the file tree.</p>
        """,
        unsafe_allow_html=True,
    )

    components_html = []
    for index, component in enumerate(entry_map.components, 1):
        name, description = _split_named_item(component)
        components_html.append(
            f"""
            <div class="fcm-component">
              <span class="fcm-component-no">{index:02d}</span>
              <strong>{_escape(name)}</strong>
              <p>{_escape(description)}</p>
            </div>
            """
        )

    seams_html = []
    for seam in entry_map.seams[:5]:
        name, description = _split_named_item(seam)
        seams_html.append(
            f"""
            <div class="fcm-seam">
              <span class="fcm-component-no">↳</span>
              <strong>{_escape(name)}</strong>
              <p>{_escape(description)}</p>
              <span class="fcm-confidence">Inferred from README</span>
            </div>
            """
        )

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown(
            f"""
            <div class="fcm-map-card">
              <h3>Likely architecture</h3>
              <p class="fcm-map-helper">{_escape(entry_map.architecture)}</p>
              {''.join(components_html)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <div class="fcm-map-card">
              <h3>Good places to enter</h3>
              <p class="fcm-map-helper">Seams are places where components meet—often approachable without understanding the entire codebase.</p>
              {''.join(seams_html)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def _issue_labels(context: RepositoryContext, number: int) -> tuple[str, ...]:
    for issue in context.issues:
        if issue.number == number:
            return issue.labels
    return ()


def _render_issues(context: RepositoryContext, entry_map: EntryMap) -> None:
    st.markdown(
        """
        <div class="fcm-issues-section">
          <div class="fcm-section-kicker">03 · First contributions</div>
          <h2 class="fcm-section-heading">Three promising starting points</h2>
          <p class="fcm-section-intro">Ranked for clarity, learning value, and likely change surface.
          Always confirm that an issue is current and unclaimed before starting.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(3, gap="medium")
    for rank, (column, recommendation) in enumerate(zip(columns, entry_map.beginner_issues), 1):
        labels = _issue_labels(context, recommendation.issue_number)[:3]
        signal_values = list(labels) or recommendation.skills[:3]
        issue_number = f"#{recommendation.issue_number}" if recommendation.issue_number else "Open issues"
        link = ""
        if recommendation.url:
            link = (
                f'<a class="fcm-issue-link" href="{_escape(recommendation.url)}" '
                'target="_blank" rel="noopener noreferrer">View issue on GitHub ↗</a>'
            )
        else:
            link = '<span class="fcm-card-copy">Ask a maintainer for a current issue</span>'

        with column:
            st.markdown(
                f"""
                <article class="fcm-issue-card">
                  <div class="fcm-issue-top">
                    <span class="fcm-rank">{rank:02d}</span>
                    <span class="fcm-issue-number">{_escape(issue_number)}</span>
                  </div>
                  <h3>{_escape(recommendation.title)}</h3>
                  <div class="fcm-chips">{_chips(signal_values)}</div>
                  <div class="fcm-card-label">Why it stands out</div>
                  <p class="fcm-card-copy">{_escape(recommendation.why)}</p>
                  <div class="fcm-card-label">Suggested first move</div>
                  <div class="fcm-first-move">{_escape(recommendation.good_first_step)}</div>
                  <div class="fcm-card-footer">{link}</div>
                </article>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="fcm-next-step"><strong>Before you start:</strong> Read CONTRIBUTING.md, confirm the issue is
        unclaimed, and leave a short comment describing your proposed approach.</div>
        """,
        unsafe_allow_html=True,
    )


def _export_markdown(context: RepositoryContext, entry_map: EntryMap, mode: str) -> str:
    repo = context.repository
    lines = [
        f"# First Contribution Map — {repo.full_name}",
        "",
        f"_Generated from the repository README and {len(context.issues)} recent open issues ({mode})._",
        "",
        "## What this project does",
        "",
        entry_map.summary,
        "",
        "## Likely architecture",
        "",
        entry_map.architecture,
        "",
    ]
    lines.extend(f"- {component}" for component in entry_map.components)
    lines.extend(["", "## Good places to enter", ""])
    lines.extend(f"- {seam}" for seam in entry_map.seams)
    lines.extend(["", "## Three promising starting points", ""])
    for index, issue in enumerate(entry_map.beginner_issues, 1):
        issue_ref = f"[#{issue.issue_number}]({issue.url})" if issue.issue_number and issue.url else "Open issues"
        lines.extend(
            [
                f"### {index}. {issue.title} ({issue_ref})",
                "",
                f"**Why it stands out:** {issue.why}",
                "",
                f"**Suggested first move:** {issue.good_first_step}",
                "",
                f"**Skills:** {', '.join(issue.skills)}",
                "",
            ]
        )
    lines.extend(
        [
            "---",
            "Before starting, read CONTRIBUTING.md, confirm the issue is unclaimed, and share your proposed approach.",
        ]
    )
    return "\n".join(lines)


def _render_actions(context: RepositoryContext, entry_map: EntryMap, mode: str) -> None:
    left, middle, spacer = st.columns([1.35, 1.4, 4.25])
    with left:
        st.download_button(
            "Download map",
            data=_export_markdown(context, entry_map, mode),
            file_name=f"{context.repository.name}-contribution-map.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with middle:
        if st.button("Analyze another repository", use_container_width=True):
            for key in ("repository_context", "entry_map", "analysis_mode", "analysis_note", "repository_url"):
                st.session_state.pop(key, None)
            st.rerun()


def _render_results(context: RepositoryContext, entry_map: EntryMap, mode: str, note: str) -> None:
    _render_source_strip(context, mode)
    if note:
        if mode == "Guided demo":
            st.info(note, icon="ℹ️")
        elif mode == "Local fallback":
            st.warning(note, icon="⚠️")
        else:
            st.caption(note)
    _render_summary(context, entry_map)
    _render_architecture(entry_map)
    _render_issues(context, entry_map)
    _render_actions(context, entry_map, mode)


def _footer() -> None:
    st.markdown(
        """
        <div class="fcm-footer">First Contribution Map · Read the context, find the seam, make the first move.</div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _load_css()
    _top_bar()
    _hero()

    analyze_clicked, demo_clicked, repo_url = _repository_form()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()

    if demo_clicked:
        try:
            _store_result(*_load_demo())
            st.toast("Contribution map ready", icon="🧭")
        except Exception as exc:  # Keep the bundled demo recoverable in the UI.
            _show_error(exc)

    if analyze_clicked:
        try:
            result = _analyze_live_repository(
                repo_url,
                gemini_key=gemini_key,
                github_token=github_token,
                model=model,
            )
            _store_result(*result)
            st.toast("Contribution map ready", icon="🧭")
        except Exception as exc:
            _show_error(exc)

    context = st.session_state.get("repository_context")
    entry_map = st.session_state.get("entry_map")
    if isinstance(context, RepositoryContext) and isinstance(entry_map, EntryMap):
        _render_results(
            context,
            entry_map,
            st.session_state.get("analysis_mode", "Analysis"),
            st.session_state.get("analysis_note", ""),
        )
    else:
        _empty_state()

    _footer()


if __name__ == "__main__":
    main()
