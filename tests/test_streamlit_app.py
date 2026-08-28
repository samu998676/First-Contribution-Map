from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_empty_state_loads_without_errors() -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()

    assert not app.exception
    assert not app.error
    assert [field.label for field in app.text_input] == ["Public GitHub repository"]
    assert not app.checkbox
    assert [button.label for button in app.button] == [
        "Generate contribution map",
        "View demo",
    ]


def test_demo_path_renders_complete_map() -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    app.button[1].click().run()

    assert not app.exception
    assert not app.error
    assert app.session_state.filtered_state["analysis_mode"] == "Guided demo"
    assert len(app.get("download_button")) == 1
    assert any(button.label == "Analyze another repository" for button in app.button)
    assert [message.value for message in app.toast] == ["Contribution map ready"]


def test_invalid_url_is_actionable() -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    app.text_input[-1].input("not-a-repository")
    app.button[0].click().run()

    assert not app.exception
    assert [error.value for error in app.error] == [
        "Enter a public GitHub URL like https://github.com/owner/repository."
    ]
