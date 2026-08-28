"""Small, dependency-free GitHub client for the First Contribution Map app.

The module deliberately accepts only GitHub web URLs.  It never requests a URL
supplied by the user directly; instead it extracts and validates the repository
owner/name and builds requests against ``api.github.com``.  This keeps URL
handling predictable and avoids turning the app into a general-purpose URL
fetcher.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen


GITHUB_API_ROOT = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_ISSUE_LIMIT = 10
MAX_ISSUE_LIMIT = 10
_ISSUES_PER_PAGE = 100
_MAX_ISSUE_PAGES = 5

_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


class GitHubClientError(Exception):
    """Base class for errors that can be shown safely in the app."""


class InvalidRepositoryURLError(GitHubClientError):
    """Raised when a value is not a supported public GitHub repository URL."""


class GitHubNetworkError(GitHubClientError):
    """Raised when GitHub cannot be reached before the request completes."""

    def __init__(self, message: str, *, url: str) -> None:
        self.url = url
        super().__init__(message)


class GitHubAPIError(GitHubClientError):
    """Raised when the GitHub API returns an unsuccessful response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        url: str,
        api_message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.api_message = api_message
        super().__init__(message)


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a repository is missing or not publicly accessible."""


class GitHubAuthenticationError(GitHubAPIError):
    """Raised when a supplied GitHub token is invalid or expired."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub's API rate limit has been exhausted."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        url: str,
        api_message: str | None = None,
        reset_at: str | None = None,
    ) -> None:
        self.reset_at = reset_at
        super().__init__(
            message,
            status_code=status_code,
            url=url,
            api_message=api_message,
        )


class GitHubResponseError(GitHubClientError):
    """Raised when GitHub returns data in an unexpected shape."""

    def __init__(self, message: str, *, url: str) -> None:
        self.url = url
        super().__init__(message)


class PrivateRepositoryError(GitHubClientError):
    """Raised when a token resolves a repository that is not public."""


@dataclass(frozen=True, slots=True)
class RepositoryRef:
    """A validated GitHub repository identifier."""

    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}"

    def to_dict(self) -> dict[str, str]:
        return {
            "owner": self.owner,
            "name": self.name,
            "full_name": self.full_name,
            "html_url": self.html_url,
        }

    as_dict = to_dict


@dataclass(frozen=True, slots=True)
class RepositoryMetadata:
    """Repository fields useful to the prompt and the Streamlit UI."""

    owner: str
    name: str
    full_name: str
    html_url: str
    description: str | None
    default_branch: str
    primary_language: str | None
    stars: int
    forks: int
    open_issues_count: int
    license_name: str | None
    topics: tuple[str, ...]
    is_archived: bool
    is_fork: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "name": self.name,
            "full_name": self.full_name,
            "html_url": self.html_url,
            "description": self.description,
            "default_branch": self.default_branch,
            "primary_language": self.primary_language,
            "stars": self.stars,
            "forks": self.forks,
            "open_issues_count": self.open_issues_count,
            "license_name": self.license_name,
            "topics": list(self.topics),
            "is_archived": self.is_archived,
            "is_fork": self.is_fork,
        }

    as_dict = to_dict


@dataclass(frozen=True, slots=True)
class Issue:
    """A non-pull-request GitHub issue."""

    number: int
    title: str
    html_url: str
    body: str | None
    labels: tuple[str, ...]
    author: str | None
    comments: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "html_url": self.html_url,
            "body": self.body,
            "labels": list(self.labels),
            "author": self.author,
            "comments": self.comments,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    as_dict = to_dict


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """All repository context needed for one model request."""

    repository: RepositoryMetadata
    readme: str
    issues: tuple[Issue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository.to_dict(),
            "readme": self.readme,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    as_dict = to_dict


def parse_github_repo_url(value: str) -> RepositoryRef:
    """Parse a GitHub web URL into a validated owner/repository pair.

    ``https://github.com/owner/repo``, URLs ending in ``.git``, URLs copied
    from a page below the repository (for example ``/issues`` or ``/tree``),
    and URLs without an explicit scheme are accepted.  SSH clone syntax and
    non-GitHub hosts are intentionally rejected.
    """

    if not isinstance(value, str) or not value.strip():
        raise InvalidRepositoryURLError("Enter a GitHub repository URL.")

    raw_value = value.strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_value):
        raise InvalidRepositoryURLError("The GitHub URL contains invalid characters.")

    candidate = raw_value
    if re.match(r"^(?:www\.)?github\.com(?:/|$)", candidate, re.IGNORECASE):
        candidate = f"https://{candidate}"

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise InvalidRepositoryURLError("The GitHub URL is malformed.") from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise InvalidRepositoryURLError(
            "Use an http(s) GitHub URL such as https://github.com/owner/repo."
        )

    hostname = (parsed.hostname or "").lower()
    if hostname not in {"github.com", "www.github.com"}:
        raise InvalidRepositoryURLError("Only github.com repository URLs are supported.")

    if parsed.username is not None or parsed.password is not None:
        raise InvalidRepositoryURLError("GitHub URLs containing credentials are not supported.")

    allowed_port = (scheme == "https" and port in {None, 443}) or (
        scheme == "http" and port in {None, 80}
    )
    if not allowed_port:
        raise InvalidRepositoryURLError("The GitHub URL uses an unsupported port.")

    # Preserve empty segments so malformed URLs such as github.com//repo do not
    # silently shift the repository name into the owner position.
    path_parts = parsed.path.split("/")
    if len(path_parts) < 3 or path_parts[0] != "" or not path_parts[1] or not path_parts[2]:
        raise InvalidRepositoryURLError(
            "The URL must include both a GitHub owner and repository name."
        )

    owner = unquote(path_parts[1])
    repository = unquote(path_parts[2])
    if repository.lower().endswith(".git"):
        repository = repository[:-4]

    if not _OWNER_RE.fullmatch(owner):
        raise InvalidRepositoryURLError("The GitHub owner name in the URL is invalid.")
    if not repository or repository in {".", ".."} or not _REPOSITORY_RE.fullmatch(repository):
        raise InvalidRepositoryURLError("The GitHub repository name in the URL is invalid.")

    return RepositoryRef(owner=owner, name=repository)


class GitHubClient:
    """Minimal GitHub REST API client with no third-party dependencies."""

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = "First-Contribution-Map/0.1",
        opener: Any = urlopen,
    ) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number of seconds")
        if not user_agent or "\n" in user_agent or "\r" in user_agent:
            raise ValueError("user_agent must be a non-empty, single-line string")

        normalized_token = token.strip() if token is not None else None
        if normalized_token and ("\n" in normalized_token or "\r" in normalized_token):
            raise ValueError("token must not contain line breaks")

        self.token = normalized_token or None
        self.timeout = float(timeout)
        self.user_agent = user_agent
        self._opener = opener

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.user_agent,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def fetch_repository(
        self,
        repository_url: str,
        *,
        issue_limit: int = DEFAULT_ISSUE_LIMIT,
    ) -> RepositoryContext:
        """Fetch metadata, the default-branch README, and recent open issues."""

        if (
            isinstance(issue_limit, bool)
            or not isinstance(issue_limit, int)
            or not 0 <= issue_limit <= MAX_ISSUE_LIMIT
        ):
            raise ValueError(f"issue_limit must be an integer from 0 to {MAX_ISSUE_LIMIT}")

        repository = parse_github_repo_url(repository_url)
        metadata = self._fetch_metadata(repository)
        readme = self._fetch_readme(repository, metadata.default_branch)
        issues = self._fetch_issues(repository, issue_limit)
        return RepositoryContext(repository=metadata, readme=readme, issues=tuple(issues))

    # A short alias reads naturally in the Streamlit app.
    fetch = fetch_repository

    def _fetch_metadata(self, repository: RepositoryRef) -> RepositoryMetadata:
        path = self._repository_api_path(repository)
        url = self._build_url(path)
        payload = self._request_json(path)
        if not isinstance(payload, Mapping):
            raise GitHubResponseError("GitHub returned invalid repository metadata.", url=url)
        if payload.get("private") is True:
            raise PrivateRepositoryError("Only public GitHub repositories are supported.")

        default_branch = _optional_string(payload.get("default_branch"))
        if not default_branch:
            raise GitHubResponseError(
                "GitHub did not return a default branch for this repository.",
                url=url,
            )

        license_payload = payload.get("license")
        license_name = None
        if isinstance(license_payload, Mapping):
            license_name = _optional_string(license_payload.get("spdx_id"))
            if not license_name or license_name == "NOASSERTION":
                license_name = _optional_string(license_payload.get("name"))

        topics_payload = payload.get("topics")
        topics = tuple(
            topic
            for topic in topics_payload
            if isinstance(topic, str) and topic
        ) if isinstance(topics_payload, Sequence) and not isinstance(topics_payload, str) else ()

        return RepositoryMetadata(
            owner=repository.owner,
            name=repository.name,
            full_name=_optional_string(payload.get("full_name")) or repository.full_name,
            html_url=_optional_string(payload.get("html_url")) or repository.html_url,
            description=_optional_string(payload.get("description")),
            default_branch=default_branch,
            primary_language=_optional_string(payload.get("language")),
            stars=_nonnegative_int(payload.get("stargazers_count")),
            forks=_nonnegative_int(payload.get("forks_count")),
            open_issues_count=_nonnegative_int(payload.get("open_issues_count")),
            license_name=license_name,
            topics=topics,
            is_archived=payload.get("archived") is True,
            is_fork=payload.get("fork") is True,
        )

    def _fetch_readme(self, repository: RepositoryRef, default_branch: str) -> str:
        path = f"{self._repository_api_path(repository)}/readme"
        url = self._build_url(path, {"ref": default_branch})
        try:
            payload = self._request_json(path, {"ref": default_branch})
        except GitHubNotFoundError:
            # A README is helpful but not mandatory; the app can still produce
            # a useful map from metadata and issues.
            return ""

        if not isinstance(payload, Mapping):
            raise GitHubResponseError("GitHub returned an invalid README response.", url=url)

        content = payload.get("content")
        if content is None:
            return ""
        if not isinstance(content, str):
            raise GitHubResponseError("GitHub returned an invalid README body.", url=url)

        encoding = payload.get("encoding")
        if encoding != "base64":
            raise GitHubResponseError(
                f"GitHub returned an unsupported README encoding: {encoding!r}.",
                url=url,
            )

        try:
            compact_content = "".join(content.split())
            raw_readme = base64.b64decode(compact_content, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise GitHubResponseError("GitHub returned malformed README content.", url=url) from exc
        return raw_readme.decode("utf-8", errors="replace")

    def _fetch_issues(self, repository: RepositoryRef, limit: int) -> list[Issue]:
        if limit == 0:
            return []

        path = f"{self._repository_api_path(repository)}/issues"
        issues: list[Issue] = []
        for page in range(1, _MAX_ISSUE_PAGES + 1):
            query = {
                "state": "open",
                "sort": "created",
                "direction": "desc",
                "per_page": _ISSUES_PER_PAGE,
                "page": page,
            }
            url = self._build_url(path, query)
            payload = self._request_json(path, query)
            if not isinstance(payload, list):
                raise GitHubResponseError("GitHub returned an invalid issues response.", url=url)

            for item in payload:
                if not isinstance(item, Mapping) or "pull_request" in item:
                    continue
                issue = self._parse_issue(item)
                if issue is not None:
                    issues.append(issue)
                if len(issues) == limit:
                    return issues

            if len(payload) < _ISSUES_PER_PAGE:
                break

        return issues

    @staticmethod
    def _parse_issue(payload: Mapping[str, Any]) -> Issue | None:
        number = payload.get("number")
        title = payload.get("title")
        html_url = payload.get("html_url")
        if isinstance(number, bool) or not isinstance(number, int):
            return None
        if not isinstance(title, str) or not isinstance(html_url, str):
            return None

        labels_payload = payload.get("labels")
        labels: list[str] = []
        if isinstance(labels_payload, list):
            for label in labels_payload:
                if isinstance(label, str) and label:
                    labels.append(label)
                elif isinstance(label, Mapping):
                    name = label.get("name")
                    if isinstance(name, str) and name:
                        labels.append(name)

        user_payload = payload.get("user")
        author = (
            _optional_string(user_payload.get("login"))
            if isinstance(user_payload, Mapping)
            else None
        )

        body = payload.get("body")
        return Issue(
            number=number,
            title=title,
            html_url=html_url,
            body=body if isinstance(body, str) else None,
            labels=tuple(labels),
            author=author,
            comments=_nonnegative_int(payload.get("comments")),
            created_at=_optional_string(payload.get("created_at")) or "",
            updated_at=_optional_string(payload.get("updated_at")) or "",
        )

    @staticmethod
    def _repository_api_path(repository: RepositoryRef) -> str:
        owner = quote(repository.owner, safe="")
        name = quote(repository.name, safe="")
        return f"/repos/{owner}/{name}"

    @staticmethod
    def _build_url(path: str, query: Mapping[str, Any] | None = None) -> str:
        url = f"{GITHUB_API_ROOT}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        return url

    def _request_json(
        self,
        path: str,
        query: Mapping[str, Any] | None = None,
    ) -> Any:
        url = self._build_url(path, query)
        request = Request(url=url, headers=self.headers, method="GET")

        try:
            response = self._opener(request, timeout=self.timeout)
            try:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                response_headers = dict(getattr(response, "headers", {}) or {})
                body = response.read()
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()
        except HTTPError as exc:
            try:
                body = exc.read()
            except (OSError, ValueError):
                body = b""
            self._raise_api_error(
                status_code=exc.code,
                url=url,
                headers=dict(exc.headers or {}),
                body=body,
            )
            raise AssertionError("unreachable")
        except (socket.timeout, TimeoutError) as exc:
            raise GitHubNetworkError(
                f"GitHub did not respond within {self.timeout:g} seconds.",
                url=url,
            ) from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, (socket.timeout, TimeoutError)):
                message = f"GitHub did not respond within {self.timeout:g} seconds."
            else:
                message = "Could not connect to the GitHub API."
            raise GitHubNetworkError(message, url=url) from exc
        except OSError as exc:
            raise GitHubNetworkError("Could not connect to the GitHub API.", url=url) from exc

        if not isinstance(status, int) or not 200 <= status < 300:
            self._raise_api_error(
                status_code=int(status or 0),
                url=url,
                headers=response_headers,
                body=body,
            )

        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubResponseError(
                "GitHub returned an unreadable API response.",
                url=url,
            ) from exc

    @staticmethod
    def _raise_api_error(
        *,
        status_code: int,
        url: str,
        headers: Mapping[str, Any],
        body: bytes,
    ) -> None:
        api_message = _api_error_message(body)
        if status_code == 401:
            raise GitHubAuthenticationError(
                "GitHub rejected the access token. Check or remove the configured token.",
                status_code=status_code,
                url=url,
                api_message=api_message,
            )

        remaining = _header_value(headers, "X-RateLimit-Remaining")
        is_rate_limit = status_code == 429 or (
            status_code == 403
            and (remaining == "0" or "rate limit" in (api_message or "").lower())
        )
        if is_rate_limit:
            reset_at = _format_rate_limit_reset(
                _header_value(headers, "X-RateLimit-Reset")
            )
            suffix = f" Try again after {reset_at}." if reset_at else " Try again later."
            raise GitHubRateLimitError(
                f"GitHub's API rate limit has been reached.{suffix}",
                status_code=status_code,
                url=url,
                api_message=api_message,
                reset_at=reset_at,
            )

        if status_code == 404:
            raise GitHubNotFoundError(
                "Repository not found. Confirm that the URL points to a public repository.",
                status_code=status_code,
                url=url,
                api_message=api_message,
            )

        detail = f": {api_message}" if api_message else ""
        raise GitHubAPIError(
            f"GitHub API request failed with status {status_code}{detail}",
            status_code=status_code,
            url=url,
            api_message=api_message,
        )


def fetch_repository_context(
    repository_url: str,
    *,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    issue_limit: int = DEFAULT_ISSUE_LIMIT,
) -> RepositoryContext:
    """Convenience wrapper for callers that do not need to reuse a client."""

    return GitHubClient(token=token, timeout=timeout).fetch_repository(
        repository_url,
        issue_limit=issue_limit,
    )


def fetch_repository_data(
    repository_url: str,
    *,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    issue_limit: int = DEFAULT_ISSUE_LIMIT,
) -> dict[str, Any]:
    """Fetch repository context and return a JSON-friendly plain dictionary."""

    return fetch_repository_context(
        repository_url,
        token=token,
        timeout=timeout,
        issue_limit=issue_limit,
    ).to_dict()


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


def _api_error_message(body: bytes) -> str | None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    return _optional_string(payload.get("message"))


def _header_value(headers: Mapping[str, Any], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if str(key).lower() == target:
            return str(value)
    return None


def _format_rate_limit_reset(value: str | None) -> str | None:
    if not value:
        return None
    try:
        reset = datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None
    return reset.isoformat(timespec="seconds").replace("+00:00", "Z")


__all__ = [
    "DEFAULT_ISSUE_LIMIT",
    "DEFAULT_TIMEOUT_SECONDS",
    "GitHubAPIError",
    "GitHubAuthenticationError",
    "GitHubClient",
    "GitHubClientError",
    "GitHubNetworkError",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
    "GitHubResponseError",
    "InvalidRepositoryURLError",
    "Issue",
    "PrivateRepositoryError",
    "RepositoryContext",
    "RepositoryMetadata",
    "RepositoryRef",
    "fetch_repository_context",
    "fetch_repository_data",
    "parse_github_repo_url",
]
