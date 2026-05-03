import json

from typer.testing import CliRunner

from aisearch.cli import app


def test_doctor_outputs_provider_status_json():
    runner = CliRunner()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "1.0"
    assert {provider["name"] for provider in data["providers"]} >= {"tavily", "brave"}


def test_search_with_missing_key_skips_provider_without_network():
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "search",
            "--query",
            "test query",
            "--providers",
            "tavily",
            "--format",
            "json",
        ],
        env={"TAVILY_API_KEY": ""},
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["results"] == []
    assert data["provider_runs"][0]["status"] == "skipped"
