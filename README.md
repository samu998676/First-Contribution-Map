# First Contribution Map

A working Streamlit proof of concept that turns a public GitHub repository into a newcomer-friendly entry map. It reads the repository README and up to ten recent open issues, then produces:

1. A high-level project summary.
2. A likely architecture map and approachable component seams.
3. Exactly three grounded first-contribution candidates, with a reason and concrete first step for each.

The app does not clone repositories, inspect private data, or write to GitHub.

## What is included

- Public GitHub URL validation and REST API integration.
- README, repository metadata, and recent non-pull-request issue fetching.
- Gemini structured output validated with Pydantic.
- Issue-number grounding so generated recommendations must refer to supplied issues.
- Prompt-injection boundaries around untrusted README and issue text.
- Deterministic local analysis when no Gemini key is supplied.
- A bundled, network-free demo and Markdown export.
- Responsive, accessible Streamlit interface and automated tests.

## Run locally

Python 3.11–3.13 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Open the local URL printed by Streamlit. The **View demo** path works without credentials or network access.

To analyze live repositories, anonymous GitHub access is enough for light use. Add `GITHUB_TOKEN` to `.env` if you need a higher GitHub request limit.

For Gemini analysis, create a key in [Google AI Studio](https://aistudio.google.com/apikey) and add it to `.env`:

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.7-flash
```

Credentials and model selection are read from `.env`; they are not shown in the application interface.

## Why the model differs from the original prompt

The original project brief names Gemini 1.5 Flash. That model has been retired, so this POC uses Google’s current Flash model (`gemini-3.7-flash`) through the current `google-genai` SDK. `GEMINI_MODEL` keeps the choice configurable.

## Test

```bash
pip install -r requirements-dev.txt
pytest
```

The test suite covers URL safety, GitHub response handling, deterministic analysis, schema guarantees, the demo flow, and actionable input errors.

## POC boundaries

The architecture map is inferred from README text; the app does not inspect the full file tree. “Beginner-friendly” is a recommendation, not a guarantee—contributors should read `CONTRIBUTING.md`, confirm that an issue is current and unclaimed, and coordinate with maintainers before starting substantial work.
