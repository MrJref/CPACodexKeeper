# CPACodexKeeper

[![CI](https://github.com/5345asda/CPACodexKeeper/actions/workflows/ci.yml/badge.svg)](https://github.com/5345asda/CPACodexKeeper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

[中文](README.md) | [English](README.en.md)

CPACodexKeeper is a Python tool for **inspecting and maintaining codex tokens stored in a CPA management system**.

It does not create tokens. Instead, it continuously maintains **existing codex tokens already stored in a CPA management API**.

## Core capabilities

- check whether a token is still valid
- disable or re-enable tokens based on the actual quota windows returned by usage
- optionally refresh disabled tokens that are close to expiry
- support `config.yml`, `.env`, Docker, and GitHub Actions CI

## Who this is for

If you already have a CPA-style token management API and want to:

- clean invalid tokens automatically
- control token usage quota
- re-enable tokens when quota recovers
- enable auto-refresh for disabled near-expiry tokens when needed

then this project is built for that workflow.

## Quick start

```bash
cp .env.example .env
python main.py --once
```

See the sections below for full configuration and runtime details.

---

## 1. What problem this project solves

In practice, codex tokens are not static assets. Over time, they may run into issues such as:

- tokens becoming invalid but still remaining in the management system
- usage quota being exhausted
- tokens being manually disabled and never re-enabled when quota recovers
- disabled tokens getting close to expiry and needing refresh only when refresh is explicitly allowed
- team and non-team accounts returning different usage structures

CPACodexKeeper automates those maintenance tasks so they do not need to be handled manually.

---

## 2. Current maintenance flow

Each inspection round follows this sequence:

1. fetch the token list from the CPA management API
2. keep only tokens where `type=codex`
3. fetch token details one by one
4. read expiry information and remaining lifetime
5. call the OpenAI usage endpoint
6. delete the token if usage returns `401` or `402`, meaning the token is invalid or the workspace is deactivated
7. if usage returns two quota windows, evaluate them by their actual meaning
8. disable when either window reaches the threshold, and re-enable only when both drop below it
9. if the token has **no `refresh_token`** and is already expired, delete it directly
10. if the token has **no `refresh_token`** and the checked quota reaches the threshold, delete it directly
11. if automatic refresh is explicitly enabled and the token is still disabled after quota handling and close to expiry, refresh it
12. upload the refreshed token payload back to CPA

This process is **round-based with intra-round concurrency**. One full round still completes before the next round starts, but multiple tokens can be inspected concurrently within the same round.

---

## 3. Supported quota logic

The project supports both team and non-team usage responses.

### Team mode

When the usage response includes both windows:

- `rate_limit.primary_window`: usually the primary quota window; logs label it from `limit_window_seconds` as `5h`, `Week`, or another appropriate name
- `rate_limit.secondary_window`: usually the secondary quota window; logs also label it from `limit_window_seconds`

In that case, the program will:

- disable when either `primary_window.used_percent` or `secondary_window.used_percent` reaches the threshold
- re-enable only when both windows are below the threshold
- automatically send the `Chatgpt-Account-Id` header

### Non-team or no weekly window

If no weekly window exists:

- the program falls back to `primary_window.used_percent`

### Default threshold

Default:

- `CPA_QUOTA_THRESHOLD=100`

That means:

- disable only when the checked quota reaches 100%
- re-enable when it drops below 100%
- but if a token has no `refresh_token`, reaching the threshold deletes it instead of only disabling it

---

## 4. Configuration

The project supports `config.yml`, environment variables, and `.env`. Precedence from highest to lowest:

1. `config.yml`
2. environment variables, including values injected by `docker-compose.yml`
3. `.env`
4. defaults

The committed `config.yml` is fully commented by default, so it does not override environment variables until you uncomment and set values. Use it when you want the WebUI and runtime policy to be changed by editing a config file.

You can also keep using the `.env` template:

```bash
cp .env.example .env
```

Then edit `.env`, or edit `config.yml` directly.

### Configuration fields

- `CPA_ENDPOINT`: CPA management API base URL
- `CPA_TOKEN`: CPA management token
- `CPA_PROXY`: optional HTTP/HTTPS proxy
- `CPA_INTERVAL`: daemon interval in seconds, default `1800`
- `CPA_QUOTA_THRESHOLD`: disable threshold, default `100`
- `CPA_EXPIRY_THRESHOLD_DAYS`: refresh threshold in days for disabled tokens, default `3`
- `CPA_ENABLE_REFRESH`: whether automatic refresh for disabled tokens is enabled, default `true`
- `CPA_HTTP_TIMEOUT`: timeout for CPA API requests, default `30`
- `CPA_USAGE_TIMEOUT`: timeout for OpenAI usage requests, default `15`
- `CPA_MAX_RETRIES`: retry count for transient network / 5xx failures, default `2`
- `CPA_WORKER_THREADS`: number of worker threads per inspection round, default `8`
- `WEBUI_ENABLED`: whether to start the built-in WebUI, default `false`; `docker-compose.yml` sets it to `true`
- `APP_HOST`: WebUI listen address, default `0.0.0.0`
- `APP_PORT`: WebUI listen port, default `8080`
- `AUTH_ENABLED`: whether WebUI login protection is enabled, default `false`
- `LOGIN_PASSWORD`: required when `AUTH_ENABLED=true`
- `AUTH_SESSION_TTL`: login session lifetime, default `168h`, supports `s/m/h/d` suffixes

The `config.yml` and `.env.example` files include comments for direct editing.

Automatic refresh is enabled by default, but the keeper still refreshes only tokens that remain disabled after quota handling; enabled tokens are left to CPA's own auto-refresh logic. If you need to avoid competing with another writer rotating the same shared `refresh_token`, set it to `false` in `config.yml` or `.env`.

---

## 5. Running the project

### Requirements

- Python 3.11+
- dependency: `curl-cffi`

Install dependencies:

```bash
pip install -r requirements.txt
```

### Run once

Useful for manual inspection, debugging, or external schedulers:

```bash
cp .env.example .env
python main.py --once
```

### Run in daemon mode

Useful for continuous maintenance:

```bash
python main.py
```

### WebUI

The built-in WebUI keeps the daemon inspection loop and adds a status dashboard, recent logs, and manual inspection trigger:

```bash
WEBUI_ENABLED=true python main.py
```

You can also override configuration from the CLI:

```bash
python main.py --web
python main.py --no-web
```

For public deployments, enable login protection:

```env
AUTH_ENABLED=true
LOGIN_PASSWORD=replace-with-a-strong-password
AUTH_SESSION_TTL=168h
```

### Dry run

This will not actually delete, disable, enable, or upload updates:

```bash
python main.py --once --dry-run
```

---

## 6. Docker deployment

The project supports Docker. `docker-compose.yml` mounts `./config.yml` into the container, and `config.yml` takes precedence over environment values injected by Compose.

### Build the image

```bash
docker build -t cpacodexkeeper .
```

### Run directly

```bash
docker run -d \
  --name cpacodexkeeper \
  -p 8080:8080 \
  -e CPA_ENDPOINT=https://your-cpa-endpoint \
  -e CPA_TOKEN=your-management-token \
  -e CPA_INTERVAL=1800 \
  -e WEBUI_ENABLED=true \
  -e AUTH_ENABLED=true \
  -e LOGIN_PASSWORD=replace-with-a-strong-password \
  cpacodexkeeper
```

### Use Compose

Copy the template first:

```bash
cp .env.example .env
```

Then edit `.env` or `config.yml` and start:

```bash
docker compose up -d --build
```

Compose maps `${APP_PORT:-8080}` by default and enables `WEBUI_ENABLED=true`. If `webui.port` or `APP_PORT` is set in `config.yml`, the application uses that internal port; the published port is still determined by `${APP_PORT:-8080}` when Compose starts. Then open:

```text
http://localhost:8080
```

---

## 7. Output behavior

For each token, the tool logs details such as:

- multiple tokens may be inspected concurrently within a round
- each token log is buffered and emitted as one block so console output does not interleave across threads

- token name
- email
- current disabled state
- expiry time
- remaining lifetime
- usage check result
- actual quota window information
- whether the token was deleted, disabled, enabled, or refreshed

At the end of each round, it prints a summary including:

- total
- alive
- dead (deleted)
- disabled
- enabled
- refreshed
- skipped
- network errors

---

## 8. Robustness features

The current version already includes several protections:

- strict configuration validation at startup
- range validation for numeric fields
- separate timeouts for CPA API and usage API
- limited retries for transient network / 5xx failures
- safe fallback when `secondary_window = null`
- one bad token does not break the whole round
- daemon mode keeps running even if one round fails

---

## 9. Developer helpers

The project includes a `justfile` for common commands.

If you use `just`, you can run:

```bash
just install
just test
just run-once
just dry-run
just daemon
just docker-build
just docker-up
just docker-down
```

---

## 10. Tests and CI

### Local tests

```bash
python -m unittest discover -s tests
```

Or:

```bash
just test
```

### GitHub Actions

The repository includes a CI workflow that:

- runs unit tests automatically
- verifies that the Docker image builds successfully

Workflow file:

```text
.github/workflows/ci.yml
```

---

## 11. Project structure

```text
CPACodexKeeper/
├─ src/
│  ├─ cli.py
│  ├─ cpa_client.py
│  ├─ logging_utils.py
│  ├─ maintainer.py
│  ├─ models.py
│  ├─ openai_client.py
│  ├─ settings.py
│  └─ utils.py
├─ tests/
├─ config.yml
├─ .env.example
├─ docker-compose.yml
├─ Dockerfile
├─ justfile
├─ main.py
├─ README.md
└─ README.en.md
```

---

## 12. Troubleshooting

### Configuration error at startup

Usually caused by missing fields or invalid values in `config.yml` / `.env`.

Check:

- `CPA_ENDPOINT`
- `CPA_TOKEN`
- whether numeric fields are valid integers

### usage returns `401`

The token is invalid. Under the current logic, it will be deleted.

### usage returns `402`

This usually means the workspace is deactivated or unavailable. Under the current logic, it will also be deleted.

### `secondary_window = null`

No weekly window is available. The tool automatically falls back to the primary window.

### Docker cannot build locally

Make sure Docker CLI is installed and available in your environment.

---

## 13. Intended usage

This project is meant for **authorized internal maintenance scenarios**, such as:

- private CPA management systems
- internal token-pool maintenance
- authorized inspection and cleanup jobs

Real credentials should never be committed to version control. Keep real `config.yml` or `.env` values local, or inject them securely in your deployment environment.
