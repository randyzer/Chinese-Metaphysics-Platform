from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_required_docker_files_exist():
    assert (ROOT / "Dockerfile").is_file()
    assert (ROOT / "compose.yaml").is_file()
    assert (ROOT / ".dockerignore").is_file()


def test_runtime_is_unprivileged_and_serves_on_port_8888():
    dockerfile = read_repo_file("Dockerfile")
    assert "FROM node:22-bookworm-slim AS frontend-builder" in dockerfile
    assert "FROM python:3.12-slim-bookworm AS runtime" in dockerfile
    assert "USER app" in dockerfile
    assert 'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]' in dockerfile


def test_local_secrets_and_build_artifacts_are_excluded():
    patterns = set(read_repo_file(".dockerignore").splitlines())
    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "!.env.example" in patterns
    assert "frontend/node_modules" in patterns
    assert "frontend/dist" in patterns
    assert ".git" in patterns


def test_compose_uses_safe_production_defaults_and_healthcheck():
    compose = read_repo_file("compose.yaml")
    assert '${APP_PORT:-8888}:8888' in compose
    assert "APP_ENV: ${APP_ENV:-production}" in compose
    assert 'APP_DEBUG: "false"' in compose
    assert "DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}" in compose
    assert "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}" in compose
    assert "http://127.0.0.1:8888/health" in compose


def test_example_environment_uses_application_setting_names():
    env_example = read_repo_file(".env.example")
    assert "APP_ENV=production" in env_example
    assert "APP_DEBUG=false" in env_example
    assert "\nDEBUG=" not in env_example
    assert "DEEPSEEK_API_KEY=" in env_example
    assert "ANTHROPIC_API_KEY=" in env_example


def test_readme_documents_complete_docker_workflow():
    readme = read_repo_file("README.md")
    assert "### Docker Desktop（推荐）" in readme
    assert "cp .env.example .env" in readme
    assert "docker compose up --build -d" in readme
    assert "docker compose ps" in readme
    assert "docker compose logs -f app" in readme
    assert "docker compose down" in readme
    assert "http://localhost:8888/health" in readme
