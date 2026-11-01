# Docker Desktop Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secure, reproducible single-container Docker Desktop deployment and deliver it through a pull request from `codex/docker-deployment`.

**Architecture:** A Node.js build stage compiles the Vite frontend, then a slim Python runtime stage installs backend dependencies and serves the compiled SPA and FastAPI API from one unprivileged container. Docker Compose publishes port 8888, injects optional credentials from an untracked `.env`, and verifies the existing `/health` endpoint.

**Tech Stack:** Docker Engine, Docker Compose, Node.js 22, Vite 8, Python 3.12, FastAPI, Uvicorn, pytest, GitHub CLI

---

### Task 1: Define and implement the container deployment contract

**Files:**
- Create: `tests/test_docker_deployment.py`
- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Modify: `.env.example`

- [ ] **Step 1: Write the failing deployment contract tests**

Create `tests/test_docker_deployment.py`:

```python
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
```

- [ ] **Step 2: Run the contract tests and verify the expected failure**

Run:

```bash
python3 -m pytest tests/test_docker_deployment.py -q
```

Expected: FAIL because `Dockerfile`, `compose.yaml`, and `.dockerignore` do not exist and `.env.example` still uses `DEBUG`.

- [ ] **Step 3: Add the multi-stage Docker image**

Create `Dockerfile`:

```dockerfile
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=app:app . ./
COPY --from=frontend-builder --chown=app:app /build/frontend/dist ./frontend/dist

USER app
EXPOSE 8888

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]
```

- [ ] **Step 4: Add the Compose service**

Create `compose.yaml`:

```yaml
services:
  app:
    build:
      context: .
    image: chinese-metaphysics-platform:local
    ports:
      - "${APP_PORT:-8888}:8888"
    environment:
      APP_ENV: ${APP_ENV:-production}
      APP_HOST: 0.0.0.0
      APP_PORT: 8888
      APP_DEBUG: "false"
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      DEEPSEEK_BASE_URL: ${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
      DEEPSEEK_MODEL: ${DEEPSEEK_MODEL:-deepseek-chat}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      BAGUA_LOG_LEVEL: ${BAGUA_LOG_LEVEL:-WARNING}
    restart: unless-stopped
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - >-
          import urllib.request;
          urllib.request.urlopen('http://127.0.0.1:8888/health', timeout=2)
      interval: 30s
      timeout: 3s
      start_period: 30s
      retries: 3
```

- [ ] **Step 5: Exclude local state, secrets, and unnecessary build inputs**

Create `.dockerignore`:

```gitignore
.git
.gitignore
.github
.DS_Store
.env
.env.*
!.env.example
.venv
venv
__pycache__
*.py[cod]
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
htmlcov
frontend/node_modules
frontend/dist
tests
docs
*.log
*.sqlite3
*.db
```

- [ ] **Step 6: Correct and expand the safe environment example**

Replace `.env.example` with:

```dotenv
# Server
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8888
APP_DEBUG=false
BAGUA_LOG_LEVEL=WARNING

# Optional AI providers. Leave empty to run without provider-backed features.
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
ANTHROPIC_API_KEY=
```

- [ ] **Step 7: Run the deployment contract tests**

Run:

```bash
python3 -m pytest tests/test_docker_deployment.py -q
```

Expected: `5 passed`.

- [ ] **Step 8: Validate the Compose and Dockerfile syntax without exposing interpolated secrets**

Run:

```bash
docker compose config --quiet
docker build --check .
```

Expected: both commands exit with status 0. Do not run `docker compose config` without `--quiet`, because an existing local `.env` could contain credentials.

- [ ] **Step 9: Commit the container implementation**

```bash
git add Dockerfile compose.yaml .dockerignore .env.example tests/test_docker_deployment.py
git commit -m "feat: add Docker Desktop deployment"
```

### Task 2: Document the Docker Desktop workflow

**Files:**
- Modify: `tests/test_docker_deployment.py`
- Modify: `README.md:374-422`

- [ ] **Step 1: Add a failing documentation contract test**

Append to `tests/test_docker_deployment.py`:

```python
def test_readme_documents_complete_docker_workflow():
    readme = read_repo_file("README.md")
    assert "### Docker Desktop（推荐）" in readme
    assert "cp .env.example .env" in readme
    assert "docker compose up --build -d" in readme
    assert "docker compose ps" in readme
    assert "docker compose logs -f app" in readme
    assert "docker compose down" in readme
    assert "http://localhost:8888/health" in readme
```

- [ ] **Step 2: Run the documentation test and verify the expected failure**

Run:

```bash
python3 -m pytest tests/test_docker_deployment.py::test_readme_documents_complete_docker_workflow -q
```

Expected: FAIL because the Docker Desktop section is absent.

- [ ] **Step 3: Correct the configuration example in README**

In `README.md`, replace the existing server configuration block under `完整配置项 · All Options` with:

```dotenv
# ─── 服务器 Server ───────────────────────────────────────────────
APP_ENV=production         # production / development
APP_HOST=0.0.0.0          # 监听地址，0.0.0.0 允许局域网访问
APP_PORT=8888              # 对外访问端口
APP_DEBUG=false            # true 时启用开发调试模式
BAGUA_LOG_LEVEL=WARNING    # Python 日志级别

# ─── AI 功能 AI Agent（可选）────────────────────────────────────
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
ANTHROPIC_API_KEY=
```

Keep the explanation that calculation modules work without an API key. Remove the unsupported `CORS_ORIGINS` example and replace every server-level `DEBUG=false` example with `APP_DEBUG=false`.

- [ ] **Step 4: Replace the production deployment section with the Docker Desktop workflow**

Replace the existing `### 生产部署 · Production Deployment` section through its Nginx recommendation with:

````markdown
### Docker Desktop（推荐）

首次运行前，确认 Docker Desktop 已启动：

```bash
cp .env.example .env
# 可选：编辑 .env，填入需要使用的 AI 服务密钥
docker compose up --build -d
```

应用启动后访问：

- Web：<http://localhost:8888>
- 健康检查：<http://localhost:8888/health>
- API 文档：<http://localhost:8888/docs>

常用维护命令：

```bash
docker compose ps
docker compose logs -f app
docker compose up --build -d
docker compose down
```

`.env` 只保留在本机，不会被 Git 跟踪或复制进镜像。未配置 API Key 时，命理计算模块仍可使用，依赖外部模型的功能不可用。
````

- [ ] **Step 5: Run the deployment tests and documentation checks**

Run:

```bash
python3 -m pytest tests/test_docker_deployment.py -q
git diff --check
```

Expected: `6 passed`; `git diff --check` exits with status 0.

- [ ] **Step 6: Commit the documentation**

```bash
git add README.md tests/test_docker_deployment.py
git commit -m "docs: add Docker Desktop workflow"
```

### Task 3: Build and verify the live Docker deployment

**Files:**
- No repository file changes expected unless verification finds a defect.

- [ ] **Step 1: Start Docker Desktop and wait for the daemon**

Run:

```bash
open -a Docker
```

Then poll with `docker info` at short intervals for up to two minutes. Expected: `docker info` exits with status 0. If Docker Desktop displays a first-run agreement, privileged-helper request, login prompt, or daemon error, stop and request user assistance instead of bypassing it.

- [ ] **Step 2: Run the fastest static validation**

Run:

```bash
docker compose config --quiet
docker build --check .
python3 -m pytest tests/test_docker_deployment.py -q
git diff --check
```

Expected: every command exits with status 0 and pytest reports `6 passed`.

- [ ] **Step 3: Build the application image**

Run:

```bash
docker compose build
```

Expected: the frontend Vite build and Python dependency installation complete, producing `chinese-metaphysics-platform:local`.

- [ ] **Step 4: Start the service**

Run:

```bash
docker compose up -d
```

Expected: service `app` is created and started.

- [ ] **Step 5: Wait for the service to become healthy**

Poll without printing environment variables:

```bash
docker compose ps --format json
```

Expected within 90 seconds: service state is `running` and health is `healthy`. If it is not healthy, inspect only `docker compose logs --tail=200 app`; never print `docker inspect` environment output.

- [ ] **Step 6: Verify HTTP behavior**

Run:

```bash
curl --fail --silent --show-error http://localhost:8888/health
curl --fail --silent --show-error --output /dev/null http://localhost:8888/
curl --fail --silent --show-error --output /dev/null http://localhost:8888/docs
```

Expected: all commands exit with status 0; `/health` reports `success: true` and `frontend_hosted: true`.

- [ ] **Step 7: Run the existing automated test suite**

Run:

```bash
python3 -m pytest -q
```

Expected: exit status 0. If failures are pre-existing or environment-specific, capture the failing test names and concise diagnostics without changing unrelated application behavior.

- [ ] **Step 8: Verify the final repository state**

Run:

```bash
git status --short --branch
git log --oneline --decorate main..HEAD
git diff --check main...HEAD
```

Expected: a clean worktree, the design plus implementation commits listed, and no whitespace errors.

### Task 4: Push the branch and open the pull request

**Files:**
- No repository file changes expected.

- [ ] **Step 1: Push only the approved feature branch to origin**

Run:

```bash
git push --set-upstream origin codex/docker-deployment
```

Expected: branch is published to `randyzer/Chinese-Metaphysics-Platform`; no push is made to `upstream`.

- [ ] **Step 2: Create the pull request**

Run:

```bash
gh pr create \
  --repo randyzer/Chinese-Metaphysics-Platform \
  --base main \
  --head codex/docker-deployment \
  --title "Add Docker Desktop deployment" \
  --body-file /tmp/chinese-metaphysics-docker-pr.md
```

Before this command, create `/tmp/chinese-metaphysics-docker-pr.md` with a summary of the multi-stage image, Compose workflow, secret handling, and the exact verification results from Task 3. Do not include credentials or interpolated environment values.

Expected: GitHub returns the new pull request URL.

- [ ] **Step 3: Confirm the PR metadata**

Run:

```bash
gh pr view --repo randyzer/Chinese-Metaphysics-Platform --json url,baseRefName,headRefName,state,title
```

Expected: state `OPEN`, base `main`, head `codex/docker-deployment`, and title `Add Docker Desktop deployment`.
