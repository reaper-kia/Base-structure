from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_ml11_stays_isolated_from_ml_service() -> None:
    ml_requirements = (
        PROJECT_ROOT / "ml_service" / "requirements.txt"
    ).read_text(encoding="utf-8")
    ml_main = (
        PROJECT_ROOT / "ml_service" / "src" / "ml_service" / "main.py"
    ).read_text(encoding="utf-8")

    assert "vosk" not in ml_requirements.lower()
    assert '@app.post("/stt")' not in ml_main


def test_both_compose_files_use_the_dedicated_stt_service() -> None:
    for compose_name in ("docker-compose.yml", "compose.prod.yml"):
        compose = (PROJECT_ROOT / compose_name).read_text(encoding="utf-8")

        assert "stt_service:" in compose
        assert "context: ./stt-service" in compose
