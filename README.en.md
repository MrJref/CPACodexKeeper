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
6. if usage returns `401` or `402`, first try to revive it by refreshing with `refresh_token`
7. after a successful revive refresh, upload the latest token payload and run usage again; only continue quota handling if the second check passes
8. if there is no `refresh_token`, refresh fails, upload fails, or the second check still returns `401` / `402`, apply the dead-token policy
9. if usage returns two quota windows, evaluate them by their actual meaning
10. disable when either window's remaining quota is below the threshold, and re-enable only when both are at or above it
11. if the token has **no `refresh_token`** and is already expired, delete it directly
12. if the token has **no `refresh_token`** and remaining quota is below the threshold, delete it directly
13. if automatic refresh is explicitly enabled and the token is still disabled after quota handling and close to expiry, refresh it
14. upload the refreshed token payload back to CPA

This process is **round-based with intra-round concurrency**. One full round still completes before the next round starts, but multiple tokens can be inspected concurrently within the same round.

---

## 3. Supported quota logic

The project supports both team and non-team usage responses.

### Team mode

When the usage response includes both windows:

- `rate_limit.primary_window`: usually the primary quota window; logs label it from `limit_window_seconds` as `5h`, `Week`, or another appropriate name
- `rate_limit.secondary_window`: usually the secondary quota window; logs also label it from `limit_window_seconds`

In that case, the program will:

- convert `primary_window.used_percent` and `secondary_window.used_percent` to remaining quota
- disable when either window's remaining quota is below the threshold
- re-enable only when both windows are at or above the threshold
- automatically send the `Chatgpt-Account-Id` header

### Non-team or no weekly window

If no weekly window exists:

- the program falls back to `primary_window.used_percent` and converts it to remaining quota

### Default threshold

Default:

- `CPA_QUOTA_THRESHOLD=1`

That means:

- disable only when remaining quota is below 1%, which normally means the quota is exhausted at 0%
- setting it to `30` means disabling when remaining quota is below 30%, and re-enabling when it is at or above 30%
- but if a token has no `refresh_token`, reaching the remaining-quota threshold deletes it instead of only disabling it

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
- `CPA_CRON`: daemon auto-inspection cron in 6-field format `second minute hour day month weekday`, default `0 0/10 * * * ?`
- `CPA_INTERVAL_MIN` / `CPA_INTERVAL_MAX`: optional random offset window around each Cron hit, supporting raw seconds or `s/m/h/d` suffixes; `CPA_INTERVAL_MIN` is the maximum early offset and `CPA_INTERVAL_MAX` is the maximum late offset. For example, if Cron hits `12:00:00` with `8m` / `2m`, the inspection runs at a random time between `11:52:00` and `12:02:00`.
- `CPA_QUOTA_THRESHOLD`: remaining-quota disable threshold, default `1`; for example, `30` disables when remaining quota is below 30%
- `CPA_EXPIRY_THRESHOLD_DAYS`: refresh threshold in days for disabled tokens, default `3`
- `CPA_ENABLE_REFRESH`: whether automatic refresh for disabled tokens is enabled, default `true`
- `CPA_ENABLE_AUTO_DELETE`: whether automatic deletion is enabled, default `true`; when `false`, tokens that would be deleted are disabled instead
- `CPA_HTTP_TIMEOUT`: timeout for CPA API requests, default `30`
- `CPA_USAGE_TIMEOUT`: timeout for OpenAI usage requests, default `15`
- `CPA_MAX_RETRIES`: retry count for transient network / 5xx failures, default `2`
- `CPA_WORKER_THREADS`: number of worker threads per inspection round, default `8`
- `WEBUI_ENABLED`: whether to start the built-in WebUI, default `false`; `docker-compose.yml` sets it to `true`
- `APP_HOST`: WebUI listen address, default `0.0.0.0`
- `APP_PORT`: WebUI listen port, default `8765`
- `LOG_MAX_LINES`: maximum recent log lines kept in WebUI memory, default `500`
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

The built-in WebUI keeps the daemon inspection loop and adds a status dashboard, recent logs, log clearing, manual inspection trigger, proxy latency test, and hot-updated `config.yml` editing:

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

The project supports Docker. `docker-compose.yml` mounts `./config.yml` into the container as writable so the WebUI can save configuration, and `config.yml` takes precedence over environment values injected by Compose.

### Build the image

```bash
docker build -t cpacodexkeeper .
```

### Run directly

```bash
docker run -d \
  --name cpacodexkeeper \
  -p 8765:8765 \
  -e CPA_ENDPOINT=https://your-cpa-endpoint \
  -e CPA_TOKEN=your-management-token \
  -e 'CPA_CRON=0 0/10 * * * ?' \
  -e WEBUI_ENABLED=true \
  -e LOG_MAX_LINES=500 \
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

Compose maps `${APP_PORT:-8765}` by default and enables `WEBUI_ENABLED=true`. If `webui.port` or `APP_PORT` is set in `config.yml`, the application uses that internal port; the published port is still determined by `${APP_PORT:-8765}` when Compose starts. Then open:

```text
http://localhost:8765
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
- completion time (`yyyy-MM-dd HH:mm:ss`)

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

The current access token is invalid. The current logic first tries to revive it with `refresh_token`; if refresh and the second usage check succeed, the token is kept. If revive fails, the dead-token policy applies.

### usage returns `402`

This usually means the workspace is deactivated or unavailable. The current logic also tries a revive refresh first; if refresh fails or the second check still fails, the dead-token policy applies.

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
