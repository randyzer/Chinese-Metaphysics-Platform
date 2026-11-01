# Docker Desktop Deployment Design

**Date:** 2026-11-02  
**Target:** Docker Desktop on the local macOS host  
**Branch:** `codex/docker-deployment`

## Goal

Provide a production-oriented, reproducible Docker deployment for Chinese Metaphysics Platform. A fresh checkout should build and run through Docker Compose, expose the application at `http://localhost:8888`, and keep all API credentials outside Git.

## Scope

The deployment will add a multi-stage application image, a Compose service definition, a Docker build context exclusion file, and concise deployment documentation. It will not add a reverse proxy, TLS termination, database service, analytics, telemetry, or any new outbound network integration.

## Architecture

Use one application container built in two stages:

1. A pinned Node.js build stage runs `npm ci` and `npm run build` in `frontend/`.
2. A pinned slim Python stage installs `requirements.txt`, copies the application source and compiled `frontend/dist`, and starts Uvicorn on `0.0.0.0:8888`.

FastAPI will continue to serve both API routes and the compiled single-page application. This preserves the existing application architecture and avoids an unnecessary Nginx container or internal proxy.

The runtime container will use an unprivileged user. Only port `8888` will be published. The Compose service will set production-safe application defaults and use a health check against the existing `/health` endpoint.

## Files

- `Dockerfile`: multi-stage frontend and backend build, unprivileged runtime user, Uvicorn entry point.
- `compose.yaml`: application service, port mapping, environment injection, health check, and restart policy.
- `.dockerignore`: excludes Git metadata, caches, virtual environments, frontend dependencies, build artifacts, tests, and local secret files.
- `.env.example`: documents Docker-relevant variables without real credentials.
- `README.md` or `INSTALL.md`: documents Docker Desktop prerequisites, setup, start, stop, logs, and rebuild commands.

The implementation will avoid unrelated source refactors.

## Configuration and Secrets

The checked-in configuration will contain only variable names and non-sensitive defaults. A developer may copy `.env.example` to `.env` and set provider credentials locally. `.env` must remain ignored and must never be copied into the image.

The default deployment must start without an LLM API key so the platform's non-provider-dependent features remain available. Provider-backed features will require the corresponding locally supplied credential.

Runtime defaults:

- `APP_ENV=production`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8888`
- `APP_DEBUG=false`

## Failure Handling

- Docker build failures must stop the deployment before a container is created.
- A failed `/health` check marks the service unhealthy.
- The Compose restart policy restarts the service after unexpected process failures but does not hide persistent health-check failures.
- Startup and application errors remain inspectable through `docker compose logs`.

## Verification

The implementation is accepted only after these checks succeed on Docker Desktop:

1. `docker compose config` validates the Compose model.
2. `docker compose build` completes for the host architecture.
3. `docker compose up -d` starts the service.
4. `docker compose ps` reports the service running and healthy.
5. `curl --fail http://localhost:8888/health` succeeds.
6. The root page and `/docs` return successful HTTP responses.
7. Existing relevant automated tests still pass, or any pre-existing failures are reported explicitly.
8. `git diff --check` reports no whitespace errors.

## Delivery

Changes will be committed to `codex/docker-deployment`, pushed only to `origin`, and submitted as a pull request targeting `randyzer/Chinese-Metaphysics-Platform:main`. The PR will summarize the container architecture, secret-handling model, and verification evidence.
