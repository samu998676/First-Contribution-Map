'use client';

import { FormEvent, useState } from 'react';

type GitHubLabel = { name?: string };

type GitHubIssue = {
  number: number;
  title: string;
  html_url: string;
  body?: string | null;
  comments?: number;
  labels?: Array<GitHubLabel | string>;
  pull_request?: unknown;
};

type GitHubRepository = {
  name: string;
  full_name: string;
  html_url: string;
  description?: string | null;
  language?: string | null;
  stargazers_count: number;
  forks_count: number;
  open_issues_count: number;
  topics?: string[];
  default_branch: string;
  license?: { spdx_id?: string; name?: string } | null;
};

type Candidate = {
  number: number;
  title: string;
  url: string;
  why: string;
  firstStep: string;
  skills: string[];
  placeholder?: boolean;
};

type ContributionMap = {
  repository: {
    name: string;
    fullName: string;
    url: string;
    description: string;
    language: string;
    stars: number;
    forks: number;
    openIssues: number;
    topics: string[];
    license: string;
  };
  summary: string;
  architecture: string;
  components: Array<{ name: string; description: string }>;
  seams: string[];
  candidates: Candidate[];
  mode: string;
  reviewedIssues: number;
};

const DEMO_MAP: ContributionMap = {
  repository: {
    name: 'first-contribution-demo',
    fullName: 'open-source/first-contribution-demo',
    url: '',
    description: 'A developer tool that helps newcomers orient themselves in unfamiliar open-source projects.',
    language: 'Python',
    stars: 1840,
    forks: 212,
    openIssues: 26,
    topics: ['open-source', 'onboarding', 'developer-tools'],
    license: 'MIT',
  },
  summary:
    'This project gives new contributors a practical orientation layer before they start reading source code. It turns project documentation and issue activity into a concise overview, highlights likely component boundaries, and points to approachable first investigations.',
  architecture:
    'The README suggests a small web application with a presentation layer, a repository-context service, and an analysis layer. GitHub supplies public metadata and issue text; the analyzer converts that context into a validated entry map; the interface presents and exports the result.',
  components: [
    { name: 'Web interface', description: 'Collects a repository URL and presents a focused contribution map.' },
    { name: 'Repository context', description: 'Loads public README content, metadata, and recent non-PR issues.' },
    { name: 'Analysis layer', description: 'Summarizes project context and ranks contained first-contribution candidates.' },
    { name: 'Export workflow', description: 'Turns the result into a portable Markdown guide.' },
  ],
  seams: [
    'Documentation and onboarding copy',
    'Issue-label and scope heuristics',
    'Error messages and empty states',
    'Markdown export formatting',
  ],
  candidates: [
    {
      number: 118,
      title: 'Clarify the local setup guide for Windows contributors',
      url: '',
      why: 'The expected outcome is concrete, documentation changes are easy to review, and the work does not require deep architectural knowledge.',
      firstStep: 'Follow the current Windows instructions in a clean environment and note the first ambiguous or missing step.',
      skills: ['Markdown', 'Technical writing', 'Developer experience'],
    },
    {
      number: 124,
      title: 'Add coverage for an invalid repository URL',
      url: '',
      why: 'The behavior is isolated, the desired result can be expressed as a small test, and the relevant validation boundary is easy to locate.',
      firstStep: 'Add one failing test for a malformed GitHub URL before changing validation behavior.',
      skills: ['Testing', 'Python', 'Input validation'],
    },
    {
      number: 131,
      title: 'Improve the empty-state explanation for repositories with no issues',
      url: '',
      why: 'This is a contained interface change with a clear user outcome and low risk to the analysis pipeline.',
      firstStep: 'Reproduce the no-open-issues state and draft the smallest copy change that explains the next action.',
      skills: ['UI copy', 'Accessibility', 'Streamlit'],
    },
  ],
  mode: 'Guided demo',
  reviewedIssues: 5,
};

const PLACEHOLDERS: Candidate[] = [
  {
    number: 0,
    title: 'Review and improve the contributor onboarding path',
    url: '',
    why: 'No additional real issue was available in the recent issue sample, so this is a clearly labeled investigation idea rather than a GitHub issue.',
    firstStep: 'Read the README and CONTRIBUTING guide as a newcomer and record one point of friction.',
    skills: ['Documentation', 'Developer experience'],
    placeholder: true,
  },
  {
    number: 0,
    title: 'Reproduce a contained bug and capture it in a test',
    url: '',
    why: 'No additional real issue was available. This placeholder suggests a safe contribution pattern without inventing an issue number.',
    firstStep: 'Choose a small confirmed bug, reproduce it locally, and add a failing regression test.',
    skills: ['Testing', 'Debugging'],
    placeholder: true,
  },
  {
    number: 0,
    title: 'Trace one isolated interface or configuration change',
    url: '',
    why: 'No additional real issue was available. A narrow configuration or copy change can still be a useful first investigation.',
    firstStep: 'Locate the smallest component or configuration file responsible for the visible behavior.',
    skills: ['Code navigation', 'Configuration'],
    placeholder: true,
  },
];

function parseRepositoryUrl(rawValue: string): { owner: string; repo: string } {
  const raw = rawValue.trim();
  if (!raw) throw new Error('Enter a public GitHub repository URL.');

  let url: URL;
  try {
    url = new URL(raw.includes('://') ? raw : 'https://' + raw);
  } catch {
    throw new Error('Enter a URL like https://github.com/owner/repository.');
  }

  const hostname = url.hostname.toLowerCase();
  if (hostname !== 'github.com' && hostname !== 'www.github.com') {
    throw new Error('Only public github.com repository URLs are supported.');
  }

  const parts = url.pathname.split('/').filter(Boolean);
  if (parts.length < 2) throw new Error('The GitHub URL must include an owner and repository.');

  const owner = parts[0];
  const repo = parts[1].replace(/\.git$/i, '');
  const ownerPattern = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/;
  const repoPattern = /^[A-Za-z0-9_.-]{1,100}$/;
  if (!ownerPattern.test(owner) || !repoPattern.test(repo)) {
    throw new Error('The GitHub owner or repository name is not valid.');
  }
  return { owner, repo };
}

function labelsFor(issue: GitHubIssue): string[] {
  return (issue.labels || [])
    .map((label) => (typeof label === 'string' ? label : label.name || ''))
    .filter(Boolean);
}

function cleanMarkdown(value: string): string {
  return value
    .replace(/~~~[\s\S]*?~~~/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_\u0060>|~-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function firstReadableParagraph(readme: string): string {
  const blocks = readme
    .split(/\n\s*\n/)
    .map(cleanMarkdown)
    .filter((block) => block.length > 70 && !block.toLowerCase().startsWith('table of contents'));
  return blocks[0] || '';
}

function issueScore(issue: GitHubIssue): number {
  const text = [issue.title, issue.body || '', ...labelsFor(issue)].join(' ').toLowerCase();
  let score = 0;
  if (/good first issue|beginner|first[- ]timer|starter/.test(text)) score += 9;
  if (/documentation|docs|readme|typo|copy/.test(text)) score += 6;
  if (/test|coverage|example|accessibility|a11y|configuration|config/.test(text)) score += 4;
  if (/help wanted|small|easy|low risk/.test(text)) score += 3;
  if (/security|breaking|architecture|migration|epic|major refactor/.test(text)) score -= 7;
  score -= Math.min(issue.comments || 0, 8) * 0.2;
  return score;
}

function recommendationFor(issue: GitHubIssue): Candidate {
  const labels = labelsFor(issue);
  const text = [issue.title, issue.body || '', ...labels].join(' ').toLowerCase();

  if (/documentation|docs|readme|typo|copy/.test(text)) {
    return {
      number: issue.number,
      title: issue.title,
      url: issue.html_url,
      why: 'The requested outcome is documentation-focused, easy to review, and unlikely to require a full mental model of the codebase.',
      firstStep: 'Reproduce the documentation gap as a new reader, then propose the smallest precise edit that resolves it.',
      skills: ['Markdown', 'Technical writing', 'Developer experience'],
    };
  }
  if (/test|coverage/.test(text)) {
    return {
      number: issue.number,
      title: issue.title,
      url: issue.html_url,
      why: 'The issue points to a measurable behavior and offers a contained way to learn the project through its test suite.',
      firstStep: 'Locate the nearest related test and add one failing example that captures the expected behavior.',
      skills: ['Testing', 'Code navigation', 'Debugging'],
    };
  }
  if (/accessibility|a11y|ui|interface|copy|style|css/.test(text)) {
    return {
      number: issue.number,
      title: issue.title,
      url: issue.html_url,
      why: 'The visible outcome is concrete and the change is likely contained within a user-facing component or style boundary.',
      firstStep: 'Reproduce the current interface behavior and identify the smallest component that owns it.',
      skills: ['Frontend', 'Accessibility', 'UI testing'],
    };
  }
  if (/config|configuration|example|sample/.test(text)) {
    return {
      number: issue.number,
      title: issue.title,
      url: issue.html_url,
      why: 'Configuration and example changes usually have a bounded surface area and a clear before-and-after result.',
      firstStep: 'Find the closest existing example or configuration test and confirm how the current behavior differs.',
      skills: ['Configuration', 'Examples', 'Validation'],
    };
  }
  return {
    number: issue.number,
    title: issue.title,
    url: issue.html_url,
    why: 'The issue appears more contained than the other recent candidates and provides a concrete starting point for investigation.',
    firstStep: 'Reproduce or clarify the requested behavior, then leave a short comment describing the smallest proposed change.',
    skills: ['Code navigation', 'Issue triage', 'Testing'],
  };
}

function buildMap(repository: GitHubRepository, readme: string, issues: GitHubIssue[]): ContributionMap {
  const language = repository.language || 'multi-language';
  const readmeSummary = firstReadableParagraph(readme);
  const summary =
    repository.description ||
    readmeSummary ||
    repository.full_name + ' is a public open-source project. Its README and recent issues provide the clearest starting context for a new contributor.';

  const topics = repository.topics || [];
  const components = [
    {
      name: language + ' core',
      description: 'The primary implementation layer where the project’s main behavior is likely maintained.',
    },
    {
      name: 'Documentation and onboarding',
      description: 'README guidance, examples, and contributor-facing explanations that help people enter the project.',
    },
    {
      name: 'Issue and contribution workflow',
      description: 'The public backlog, labels, review expectations, and maintainer coordination around changes.',
    },
  ];
  if (/api|sdk|client|integration/i.test(readme + ' ' + topics.join(' '))) {
    components.splice(1, 0, {
      name: 'Public API and integrations',
      description: 'Boundaries that connect core behavior to external clients, services, or extension points.',
    });
  }

  const architecture =
    'The README suggests a ' +
    language +
    ' project centered on a core implementation layer, supported by documentation and a GitHub-based contribution workflow. ' +
    (components.length > 3
      ? 'It also appears to expose API or integration boundaries that can isolate smaller changes.'
      : 'For a first contribution, documentation, tests, examples, and issue-specific components are the safest seams to inspect first.');

  const seams = [
    'README, examples, and onboarding guidance',
    'Tests around one observable behavior',
    'Configuration and validation boundaries',
    'Small issue-labeled user experience fixes',
  ];
  if (topics.length) seams.push('Topic-specific modules: ' + topics.slice(0, 3).join(', '));

  const ranked = [...issues].sort((a, b) => issueScore(b) - issueScore(a));
  const candidates = ranked.slice(0, 3).map(recommendationFor);
  while (candidates.length < 3) candidates.push(PLACEHOLDERS[candidates.length]);

  return {
    repository: {
      name: repository.name,
      fullName: repository.full_name,
      url: repository.html_url,
      description: repository.description || '',
      language,
      stars: repository.stargazers_count,
      forks: repository.forks_count,
      openIssues: repository.open_issues_count,
      topics,
      license: repository.license?.spdx_id || repository.license?.name || 'Not specified',
    },
    summary: summary.length > 520 ? summary.slice(0, 517) + '…' : summary,
    architecture,
    components: components.slice(0, 5),
    seams: seams.slice(0, 6),
    candidates,
    mode: 'Live local analysis',
    reviewedIssues: issues.length,
  };
}

async function fetchRepositoryMap(rawUrl: string): Promise<ContributionMap> {
  const { owner, repo } = parseRepositoryUrl(rawUrl);
  const root = 'https://api.github.com/repos/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo);
  const apiHeaders = {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };

  const repositoryResponse = await fetch(root, { headers: apiHeaders });
  if (repositoryResponse.status === 404) {
    throw new Error('We could not access this repository. Confirm that it exists and is public.');
  }
  if (repositoryResponse.status === 403) {
    throw new Error('GitHub’s public request limit was reached. Please try again later.');
  }
  if (!repositoryResponse.ok) {
    throw new Error('GitHub returned an unexpected response. Please try again shortly.');
  }
  const repository = (await repositoryResponse.json()) as GitHubRepository;
  if (!repository || !repository.full_name) throw new Error('GitHub returned incomplete repository information.');

  const [readmeResponse, issuesResponse] = await Promise.all([
    fetch(root + '/readme', {
      headers: { ...apiHeaders, Accept: 'application/vnd.github.raw+json' },
    }),
    fetch(root + '/issues?state=open&sort=updated&direction=desc&per_page=30', {
      headers: apiHeaders,
    }),
  ]);

  const readme = readmeResponse.ok ? await readmeResponse.text() : '';
  if (!issuesResponse.ok) {
    if (issuesResponse.status === 403) {
      throw new Error('GitHub’s public request limit was reached while loading issues.');
    }
    throw new Error('The repository loaded, but its recent issues could not be read.');
  }
  const issuePayload = (await issuesResponse.json()) as GitHubIssue[];
  const issues = issuePayload.filter((issue) => !issue.pull_request).slice(0, 10);
  return buildMap(repository, readme, issues);
}

function compactNumber(value: number): string {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'm';
  if (value >= 1_000) return (value / 1_000).toFixed(1) + 'k';
  return String(value);
}

function downloadMap(map: ContributionMap) {
  const lines = [
    '# First Contribution Map: ' + map.repository.fullName,
    '',
    '_Generated with ' + map.mode + '._',
    '',
    '## What this project does',
    '',
    map.summary,
    '',
    '## Likely architecture',
    '',
    map.architecture,
    '',
    '### Components',
    '',
    ...map.components.map((component) => '- **' + component.name + '** — ' + component.description),
    '',
    '### Good places to enter',
    '',
    ...map.seams.map((seam) => '- ' + seam),
    '',
    '## First-contribution candidates',
    '',
    ...map.candidates.flatMap((candidate, index) => [
      '### ' + (index + 1) + '. ' + candidate.title,
      '',
      candidate.number ? 'Issue #' + candidate.number + (candidate.url ? ': ' + candidate.url : '') : '_Local investigation placeholder_',
      '',
      '**Why:** ' + candidate.why,
      '',
      '**First step:** ' + candidate.firstStep,
      '',
      '**Skills:** ' + candidate.skills.join(', '),
      '',
    ]),
    '## Before you start',
    '',
    'Read CONTRIBUTING.md, confirm the issue is current and unclaimed, and describe your proposed approach to the maintainers.',
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = map.repository.name + '-contribution-map.md';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

export default function Home() {
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [map, setMap] = useState<ContributionMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const nextMap = await fetchRepositoryMap(repositoryUrl);
      setMap(nextMap);
      window.setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something unexpected happened. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  function showDemo() {
    setError('');
    setMap(DEMO_MAP);
    window.setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' }), 50);
  }

  function reset() {
    setMap(null);
    setError('');
    setRepositoryUrl('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="First Contribution Map home">
          <span className="brand-mark" aria-hidden="true">&lt;/&gt;</span>
          <span>First Contribution Map</span>
        </a>
        <span className="proof-badge"><span aria-hidden="true" />PUBLIC POC · README + ISSUES</span>
      </header>

      <section className="hero" id="top">
        <p className="eyebrow">Repository onboarding, decoded</p>
        <h1>Find your first <em>meaningful contribution.</em></h1>
        <p className="hero-copy">
          Paste a public GitHub repository. Get the project context, likely architecture,
          and three approachable starting points—before getting lost in the codebase.
        </p>

        <form className="repository-card" onSubmit={handleSubmit}>
          <label htmlFor="repository-url">Public GitHub repository</label>
          <div className="input-row">
            <span className="input-prefix" aria-hidden="true">github.com/</span>
            <input
              id="repository-url"
              type="text"
              value={repositoryUrl}
              onChange={(event) => setRepositoryUrl(event.target.value)}
              placeholder="owner/repository"
              autoComplete="url"
              disabled={loading}
            />
          </div>
          <div className="action-row">
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? 'Building your map…' : 'Generate contribution map'}
              <span aria-hidden="true">→</span>
            </button>
            <button className="secondary-button" type="button" onClick={showDemo} disabled={loading}>
              View guided demo
            </button>
          </div>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          <div className="trust-row" aria-label="Privacy notes">
            <span>Public metadata only</span>
            <span>No repository clone</span>
            <span>No writes to GitHub</span>
          </div>
        </form>
      </section>

      {loading ? (
        <section className="loading-panel" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <div>
            <strong>Building your contribution map</strong>
            <p>Reading the README and reviewing recent open issues…</p>
          </div>
        </section>
      ) : null}

      {!map && !loading ? (
        <section className="overview-video" aria-labelledby="overview-video-title">
          <div className="overview-video-header">
            <div className="overview-video-copy">
              <p className="section-kicker">49-second product overview</p>
              <h2 id="overview-video-title">See First Contribution Map in action</h2>
              <p>
                See the challenge, the solution, and the complete path from a public repository
                to a confident first-contribution starting point.
              </p>
            </div>
            <a
              className="overview-download"
              href="media/first-contribution-map-overview.mp4"
              download="first-contribution-map-overview.mp4"
            >
              Download HD video <span aria-hidden="true">↓</span>
            </a>
          </div>

          <div className="overview-video-frame">
            <video
              controls
              playsInline
              preload="metadata"
              poster="media/first-contribution-map-overview-poster.jpg"
              aria-label="First Contribution Map product overview"
            >
              <source src="media/first-contribution-map-overview.mp4" type="video/mp4" />
              <track
                default
                kind="captions"
                src="media/first-contribution-map-overview.vtt"
                srcLang="en"
                label="English"
              />
              Your browser cannot play this video.{' '}
              <a
                href="media/first-contribution-map-overview.mp4"
                download="first-contribution-map-overview.mp4"
              >
                Download the HD video instead.
              </a>
            </video>
          </div>

          <div className="overview-points" aria-label="Video overview">
            <article>
              <span>Challenge</span>
              <p>New contributors face too much context and no clear entry point.</p>
            </article>
            <article>
              <span>Solution</span>
              <p>The map explains the project, its likely seams, and approachable issues.</p>
            </article>
            <article>
              <span>Outcome</span>
              <p>Less time decoding the codebase and more confidence starting a useful PR.</p>
            </article>
          </div>
        </section>
      ) : null}

      {!map && !loading ? (
        <section className="onboarding" aria-labelledby="onboarding-title">
          <div className="section-heading">
            <p className="section-kicker">How it works</p>
            <h2 id="onboarding-title">From unfamiliar codebase to a clear first step</h2>
          </div>
          <div className="step-grid">
            <article className="step-card">
              <span>01</span>
              <h3>Paste a repository</h3>
              <p>Use any public GitHub URL, including copied links from an issues or code page.</p>
            </article>
            <article className="step-card">
              <span>02</span>
              <h3>Read the context</h3>
              <p>The site reviews the README, repository metadata, and up to ten recent open issues.</p>
            </article>
            <article className="step-card">
              <span>03</span>
              <h3>Start with confidence</h3>
              <p>See the project map, likely seams, and three grounded candidate cards.</p>
            </article>
          </div>
        </section>
      ) : null}

      {map ? (
        <section className="results" id="results">
          <div className="source-strip">
            <div>
              <p className="repo-name">{map.repository.fullName}</p>
              <p>{map.reviewedIssues} recent issue{map.reviewedIssues === 1 ? '' : 's'} reviewed · README context analyzed</p>
            </div>
            <div className="source-actions">
              <span className="mode-badge">{map.mode}</span>
              {map.repository.url ? (
                <a href={map.repository.url} target="_blank" rel="noreferrer">Open GitHub ↗</a>
              ) : null}
            </div>
          </div>

          <div className="repo-stats" aria-label="Repository details">
            <div><span>Language</span><strong>{map.repository.language}</strong></div>
            <div><span>Stars</span><strong>{compactNumber(map.repository.stars)}</strong></div>
            <div><span>Forks</span><strong>{compactNumber(map.repository.forks)}</strong></div>
            <div><span>Open issues</span><strong>{compactNumber(map.repository.openIssues)}</strong></div>
            <div><span>License</span><strong>{map.repository.license}</strong></div>
          </div>

          <section className="result-block">
            <div className="result-index">01 · PROJECT</div>
            <h2>What this project does</h2>
            <p className="large-copy">{map.summary}</p>
            {map.repository.topics.length ? (
              <div className="chip-row">
                {map.repository.topics.slice(0, 6).map((topic) => <span key={topic}>{topic}</span>)}
              </div>
            ) : null}
          </section>

          <section className="result-block">
            <div className="result-index">02 · ARCHITECTURE</div>
            <h2>Where the seams are</h2>
            <p className="architecture-copy">{map.architecture}</p>
            <div className="architecture-grid">
              <div>
                <h3>Likely components</h3>
                <div className="component-list">
                  {map.components.map((component, index) => (
                    <article key={component.name}>
                      <span>{String(index + 1).padStart(2, '0')}</span>
                      <div>
                        <h4>{component.name}</h4>
                        <p>{component.description}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
              <aside className="seams-card">
                <p className="section-kicker">Good places to enter</p>
                <h3>Contained boundaries</h3>
                <p>Areas where a new contributor can investigate without understanding the entire codebase.</p>
                <ul>
                  {map.seams.map((seam) => <li key={seam}>{seam}</li>)}
                </ul>
              </aside>
            </div>
          </section>

          <section className="result-block">
            <div className="result-index">03 · FIRST CONTRIBUTIONS</div>
            <h2>Three approachable starting points</h2>
            <p className="section-intro">
              These are recommendations, not assignments. Confirm scope and ownership with maintainers before starting.
            </p>
            <div className="issue-grid">
              {map.candidates.map((candidate, index) => (
                <article className="issue-card" key={String(candidate.number) + candidate.title}>
                  <div className="issue-topline">
                    <span className="issue-rank">{String(index + 1).padStart(2, '0')}</span>
                    <span className={candidate.placeholder ? 'issue-kind placeholder' : 'issue-kind'}>
                      {candidate.placeholder ? 'Local placeholder' : 'Issue #' + candidate.number}
                    </span>
                  </div>
                  <h3>{candidate.title}</h3>
                  <div className="issue-detail">
                    <span>Why it fits</span>
                    <p>{candidate.why}</p>
                  </div>
                  <div className="issue-detail">
                    <span>Suggested first move</span>
                    <p>{candidate.firstStep}</p>
                  </div>
                  <div className="skill-row">
                    {candidate.skills.map((skill) => <span key={skill}>{skill}</span>)}
                  </div>
                  {candidate.url ? (
                    <a className="issue-link" href={candidate.url} target="_blank" rel="noreferrer">
                      View issue on GitHub <span aria-hidden="true">↗</span>
                    </a>
                  ) : (
                    <p className="demo-note">{candidate.placeholder ? 'Not a real GitHub issue' : 'Demo issue'}</p>
                  )}
                </article>
              ))}
            </div>
          </section>

          <aside className="before-card">
            <div className="before-icon" aria-hidden="true">✓</div>
            <div>
              <h3>Before you start</h3>
              <p>Read CONTRIBUTING.md, confirm the issue is current and unclaimed, and leave a short comment describing your proposed approach.</p>
            </div>
          </aside>

          <div className="footer-actions">
            <button className="primary-button" type="button" onClick={() => downloadMap(map)}>Download map</button>
            <button className="text-button" type="button" onClick={reset}>Analyze another repository</button>
          </div>
        </section>
      ) : null}

      <footer>
        <p>First Contribution Map · Public GitHub context only · No repository writes</p>
        <a href="https://github.com/samu998676/First-Contribution-Map" target="_blank" rel="noreferrer">Source on GitHub ↗</a>
      </footer>
    </main>
  );
}
