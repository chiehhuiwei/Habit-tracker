# AGENTS.md — 時光投資簿 timeVest (Habit-tracker)

This file is the authoritative reference for any developer or AI agent working on this project. Read this document in full before writing code, making changes, or opening pull requests.

---

## 1. Project Overview

**時光投資簿 timeVest** is a personal time-investment tracking system integrated with **LINE Official Account (OA)** and **LIFF (LINE Front-end Framework)**. The core philosophy is to treat time as a financial asset — you "invest" your hours into activities (reading, learning, exercising) and record, analyse, and visualise your returns.

### Key Features

| Feature | Description |
|---|---|
| LINE 對話計時 | Start/end focus sessions via chat or rich menu, answer progress/memo prompts, and sync to BigQuery. |
| LIFF 專注碼表 | Mobile-first circular stopwatch web app (`/liff/`) embedded inside LINE for real-time tracking. |
| LIFF 項目管理 | Track reading pages or percentage completion, set ⭐ favorite activities, add/edit/delete items. |
| 收益與對帳單 | View unlocked milestones, weekly/all-time time allocations, and stats summaries. |
| 行事曆提醒 (選用) | Merge multiple iCal calendars, receive 08:00 daily digest and 15-min pre-class notifications. |
| 多人小圈子模式 | Isolated accounts, items, and timers per user via SQLite (`timevest.db`). Friends join with `LINE_INVITE_CODE`. |

### Deployment
- Runs as a **Dockerised Python application** on a VM (e.g., GCP Compute Engine).
- Unified **FastAPI** service serving `/line/webhook`, `/api/*`, and `/liff/` at `0.0.0.0:7860`.
- Automatic HTTPS termination handled by **Caddy** (Let's Encrypt).

---

## 2. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Web Framework | [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org) | `>= 0.110.0` / `>= 0.29.0` |
| Mobile Frontend | HTML5 + CSS + JavaScript + [LINE LIFF SDK](https://static.line-scdn.net/liff/edge/2/sdk.js) | v2 |
| Language | Python | 3.10+ |
| Package Manager | [uv](https://docs.astral.sh/uv/) | latest (replaces pip) |
| Relational Store (local) | SQLite (WAL mode, `timevest.db` via `timevest/core/store.py`) | 3.x |
| Time-series Store (cloud) | Google BigQuery (`habit_logs` table) | `google-cloud-bigquery >= 3.0.0` |
| Activity Sync | Garmin Connect (`garminconnect`) | `>= 0.3.1` |
| Calendar (iCal) | `icalendar`, `recurring-ical-events` | `>= 6.0.0` / `>= 3.3.0` |
| Reverse Proxy (HTTPS) | Caddy 2 | latest |

---

## 3. Architecture & Directory Structure

```
Habit-tracker/
├── timevest/                   # Main application package
│   ├── main.py                 # Application entry point: setup BigQuery, builds & starts FastAPI
│   ├── core/                   # Domain logic & persistence
│   │   ├── service.py          # TimeVestService: BigQuery activity logging, stats queries, milestones
│   │   └── store.py            # SQLite repository: per-user accounts, items, session state, calendars
│   ├── line/                   # LINE Official Account webhook & worker
│   │   ├── config.py           # LINE configuration & env loader
│   │   ├── users.py            # User management, contextvars current_user, invite codes
│   │   ├── ledger.py           # Adapter layer between LINE bot and TimeVestService
│   │   ├── state.py            # User conversational & active session state in SQLite
│   │   ├── routes.py           # FastAPI APIRouter for /line/webhook and /line/healthz
│   │   ├── flows/              # Multi-turn conversation flows (start, end, pending)
│   │   ├── jobs/               # Reminders & daily digest scheduler
│   │   └── calendar/           # iCal synchronization & conflict detection
│   ├── web/                    # LIFF web application & REST APIs
│   │   ├── auth.py             # LINE LIFF Bearer token validation against LINE profile API
│   │   ├── routes.py           # REST APIs (/api/investments, /api/items, /api/session, /api/stats)
│   │   └── static/             # Static frontend assets served at /liff/ (index.html, style.css, app.js)
│   └── integrations/           # External service sync
│       └── garmin.py           # Background Garmin Connect activity synchronization
├── scripts/                    # Deployment & management scripts
│   ├── install.sh              # Server bootstrapping script
│   └── richmenu/               # Rich menu assets (generate_image.py, richmenu.json, setup-richmenu.sh)
├── deploy/                     # Deployment configurations
│   └── Caddyfile               # Caddy reverse proxy configuration
├── docs/                       # Project documentation
│   └── line-bot.md             # Complete LINE OA & LIFF operational guide
├── examples/                   # Reference configs
│   └── calendars.example.json  # iCal calendar configuration template
├── legacy/                     # Archived flat-file JSON stores (imported automatically on first run)
├── line_data/                  # Persistent SQLite database (`timevest.db`) (volume mounted)
├── tests/                      # Automated pytest suite (16 tests, fake BigQuery client)
├── Dockerfile                  # Multi-stage container build (builder stage uses uv)
├── docker-compose.yml          # Service definition (habit-tracker + caddy)
└── requirements.txt            # Python dependencies
```

### Data Flow

```
User (LINE App) ──▶ POST /line/webhook (signed) ──┐
                                                  ▼
User (LIFF Web) ──▶ HTTPS /api/* (LIFF Token) ───▶ FastAPI (timevest.main)
                                                  │
                                                  ▼
                                           TimeVestService
                                                  │
                       ┌──────────────────────────┴──────────────────────────┐
                       ▼                                                     ▼
        SQLite (`line_data/timevest.db`)                      Google BigQuery (`habit_logs`)
    (Per-user investments, items, state)                 (Permanent historical focus sessions)
```

---

## 4. Coding Conventions

- **Language & Style**: Python 3.10+, PEP 8, 120 character max line length.
- **Timezone**: Always use `ZoneInfo("Asia/Taipei")`. Never use naive UTC datetimes.
- **Data Isolation**: All user-facing endpoints and storage access MUST be scoped to the authenticated `user_id`.
- **Database Access**:
  - Local configuration and states: Read/write through `timevest.core.store`.
  - BigQuery queries: Parameterized or properly escaped; filter by `user_id` so members only query their own data.
- **Testing**:
  - Always run tests before opening PRs:
    ```bash
    .venv/bin/python -m pytest tests -q
    ```

---

## 5. Deployment

```bash
# Build and run containers with automated Let's Encrypt HTTPS
docker compose --profile https up -d --build
```
- Port 80 & 443 must be open in VM firewall.
- `line_data/` must be mounted as a persistent volume to preserve `timevest.db`.
