# AGENTS.md — 時光投資簿 timeVest (Habit-tracker)

This file is the authoritative reference for any developer or AI agent working on this project. Read this document in full before writing code, making changes, or opening pull requests.

---

## 1. Project Overview

**時光投資簿 timeVest** is a personal time-investment tracking web application. The core philosophy is to treat time as a financial asset — you "invest" your hours into activities (reading, learning, exercising) and record, analyse, and visualise your returns.

### Key Features

| Tab | 功能說明 |
|-----|---------|
| 專注計時 (Focus Timer) | Circular stopwatch to track real-time focus sessions. Supports selecting an investment account and an item (e.g., a book) from the database. |
| 手動記錄 (Manual Log) | Log focus sessions that have already occurred with explicit start/end timestamps. |
| 項目管理 (Project Management) | Add, update, and delete tracked items (books, courses, etc.) per investment account. View their progress. Edit historical session logs. |
| 投資收益 (Yields) | Milestone and monthly achievement reports. |
| 時光對帳單 (Statement) | Spotify-Wrapped-style annual summary of your time investments. |
| 帳戶管理 (Account Settings) | Create and delete investment accounts (e.g., 日常閱讀, 健身, 吉他). |

### Deployment
- Runs as a **Dockerised Python application** on a VM (e.g., GCP Compute Engine).
- The UI is served by **Gradio** at `0.0.0.0:7860`.
- Public access: `http://<VM_PUBLIC_IP>:7860/`

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| UI Framework | [Gradio](https://gradio.app) | 5.49.1 |
| Language | Python | 3.10 |
| Package Manager | [uv](https://docs.astral.sh/uv/) | latest (replaces pip) |
| Data Store (cloud) | Google BigQuery | `google-cloud-bigquery >= 3.0.0` |
| Data Store (local) | JSON flat files (`investments.json`, `items.json`, `milestones.json`) | — |
| Data Analysis | Pandas | >= 2.0.0 |
| Charting | Matplotlib | >= 3.7.0 |
| Activity Sync | Garmin Connect (`garminconnect`) | >= 0.3.1 |
| Config | `python-dotenv` | >= 1.0.0 |
| Containerisation | Docker | python:3.10-slim, multi-stage build |

---

## 3. Architecture & Directory Structure

```
Habit-tracker/
├── app.py                  # Main entry point: all Gradio UI, event handlers, and HTML rendering
├── timevest_service.py     # Business logic layer: CRUD for investments, items, activities, milestones
├── garmin_integration.py   # Garmin Connect sync: pulls sleep/activity data into BigQuery
├── investments.json        # Local persistent store: list of investment accounts
├── items.json              # Local persistent store: list of tracked items (books, courses, etc.)
├── habits.json             # Local persistent store: habit records (legacy)
├── milestones.json         # Local persistent store: milestones and monthly summaries
├── requirements.txt        # Python dependencies (used by uv for installs)
├── Dockerfile              # Multi-stage container build (builder stage uses uv)
├── .dockerignore           # Excludes .venv, .git, secrets from Docker build context
├── install.sh              # Server bootstrap script (uses uv pip install)
├── .env                    # Secret environment variables (NOT committed)
├── .env.example            # Template for .env
└── gcp-key.json            # GCP service account key (NOT committed; mount as secret)
```

### Data Flow

```
User (Browser)
    │
    ▼
Gradio (app.py)          ← Event handlers, HTML builders
    │
    ▼
TimeVestService           ← Business logic, JSON CRUD, milestone triggers
    │
    ├── investments.json / items.json / milestones.json  (local state)
    │
    └── Google BigQuery   ← Activity log (habit_logs table), historical queries
```

### Dual-layer Storage Pattern
- **Local JSON files** hold the "master list" of accounts, items, and milestones in memory (`service.investments`, `service.items`, `service.milestones`).
- **BigQuery** is the time-series log for every focus session (`log_activity`, `get_activities_by_range`).
- On server (re)start, `on_page_load()` reloads JSON files from disk into `service.*` to restore in-memory state.

---

## 4. Coding Conventions

### General
- **Language**: Python 3.10+, using type hints where practical.
- **Style**: Follow PEP 8. Line length: 120 characters.
- **Encoding**: UTF-8 throughout; Chinese characters appear in UI strings — do not break them.
- **Timezone**: Always use `ZoneInfo("Asia/Taipei")` for time-aware datetimes. Never use naive UTC.

### Gradio UI Patterns

1. **Never filter `item_dropdown` or `manual_item_dropdown` by `status="inProgress"` only.** The Focus Timer and Manual Entry must show **all items** belonging to the selected investment account, regardless of status. This allows users to log sessions for paused or completed books. Only the warning "no items yet" message should trigger when there are zero items total.

2. **Investment-scoped dropdowns.** All item dropdowns are scoped to a specific `investment_id`. Use `service.get_items(inv_id=inv["id"])` — never cross-pollinate items from different accounts.

3. **Sync pattern after mutations.** After adding, updating, or deleting an item, always refresh both the Focus Timer dropdown (`item_dropdown`) and the Manual Entry dropdown (`manual_item_dropdown`) via a Gradio `.then()` chain. The callback must receive the current `inv_name` as input to compute the correct item scope.

4. **Dynamic update returns.** All Gradio callbacks that update a dropdown must return a `gr.update(choices=..., visible=..., label=...)` dict. Do not return bare lists.

5. **HTML rendering.** Rich HTML blocks are constructed with Python f-strings and returned by Gradio callback functions. No external template engine is used.

### Service Layer (`timevest_service.py`)

- `TimeVestService` is a singleton (`service = TimeVestService(...)` in `app.py`).
- All JSON mutations go through `save_json()` immediately after updating `self.items` / `self.investments` / `self.milestones` in memory.
- BigQuery operations (`log_activity`, `get_activities_by_range`, etc.) are wrapped in try/except blocks; surface errors as human-readable messages.
- Milestone checks (`_check_milestones`) are triggered automatically after every `log_activity` call.

### Environment Variables
All secrets must be loaded from `.env` via `python-dotenv`. Required keys:

| Variable | Description |
|----------|-------------|
| `BQ_PROJECT_ID` | GCP project ID |
| `BQ_DATASET_ID` | BigQuery dataset name |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON key |
| `GARMIN_EMAIL` | Garmin account email |
| `GARMIN_PASSWORD` | Garmin account password |
| `GARMIN_TOKEN_STORE` | Local path for Garmin OAuth token cache |

---

## 5. Testing Protocols

This project currently has no automated test suite. The following **manual verification checklist** should be performed after every non-trivial change:

### Focus Timer & Item Dropdown
- [ ] Select each investment account — verify the item dropdown shows **all** items for that account (not just in-progress ones).
- [ ] Select an account with no items — verify the warning appears and the quick-add input is shown.
- [ ] Add a new item via the **Project Management** tab → switch to **Focus Timer** → verify the new item appears in the dropdown immediately (without a page reload).
- [ ] Add a new item directly via the **Focus Timer** quick-add → verify the dropdown refreshes with the new item.
- [ ] Delete an item from the timer quick-delete → verify the dropdown updates.
- [ ] Settle a timer session → verify the BigQuery activity log receives the correct `investment_id`, `item_id`, and duration.

### Project Management
- [ ] Add a new item → verify it appears in the Project Management item list after clicking "整理列表".
- [ ] Update an item's status to "completed" → verify it still appears in the Focus Timer dropdown.
- [ ] Delete an item → verify it is removed from all dropdowns across all tabs.

### Manual Entry
- [ ] Select an account → verify the item dropdown shows all items for that account.
- [ ] Submit a manual log entry with a valid time range → verify a success message and BigQuery write.
- [ ] Submit with invalid time format → verify a clear error message in Chinese.

### Account Management
- [ ] Add a new investment account → verify it appears in all account dropdowns across every tab.
- [ ] Delete an account → verify all associated items are removed and dropdowns update.

### Deployment Smoke Test
After rebuilding the Docker image and deploying:
```bash
docker build -t habit-tracker .
docker run -p 7860:7860 --env-file .env -v $(pwd)/gcp-key.json:/app/gcp-key.json habit-tracker
# Open http://localhost:7860 and run through the checklist above.
```

---

## 6. Pull Request Guidelines

### Branch Naming
```
feature/<short-description>
fix/<short-description>
docs/<short-description>
```
Example: `fix/timer-item-dropdown-scope`

### Commit Messages
Use imperative mood in English or Chinese. Reference the affected tab/component.
```
fix: show all items in Focus Timer dropdown, not just inProgress
feat: add quick-add item from timer tab
docs: add AGENTS.md project guide
```

### PR Checklist
Before opening a PR, confirm:
- [ ] The manual verification checklist above has been run.
- [ ] No secrets (`.env`, `gcp-key.json`) are committed.
- [ ] `investments.json`, `items.json`, and `milestones.json` only contain **example or test data** — never real user data.
- [ ] All Chinese UI strings remain intact (do not silently drop or corrupt them in code edits).
- [ ] If you modified the Gradio event handler chain (`.click()`, `.change()`, `.then()`), verify the correct `inputs=` and `outputs=` components are wired.
- [ ] If you changed `timevest_service.py`, verify `save_json()` is called after every mutation.
- [ ] Docker build passes: `docker build -t habit-tracker .`

### What NOT to Do
- **Do not** add `status="inProgress"` filters to item dropdowns in the Focus Timer or Manual Entry tabs.
- **Do not** use `dynamic_update_all_items_dropdown()` (which returns all items across all investments) to refresh investment-scoped dropdowns — always scope by `inv_id`.
- **Do not** store credentials or user passwords in code or JSON files.
- **Do not** rename or remove the `on_page_load()` function — it is critical for restoring in-memory state after server restarts.

---

## 7. Deployment Reference

### Package Manager: uv

All Python dependencies are managed with **[uv](https://docs.astral.sh/uv/)** — a Rust-based package manager that is 10–100x faster than pip.

```bash
# One-time install (on a fresh VM or dev machine)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies (replaces: pip install -r requirements.txt)
uv pip install -r requirements.txt

# Add a new package
uv pip install <package> && uv pip freeze > requirements.txt
```

> **Do not** use bare `pip install` anywhere — always use `uv pip install` so the cache and venv remain consistent.

### Docker (VM)

The Dockerfile uses a **two-stage build** powered by uv:

| Stage | Base Image | Purpose |
|-------|-----------|--------|
| `builder` | `python:3.10-slim` | Installs uv, creates `.venv`, resolves all dependencies |
| runtime | `python:3.10-slim` | Copies `.venv` + app code only — no build tooling |

```bash
# Build (subsequent builds are fast — uv cache mount skips re-downloading packages)
docker build -t habit-tracker .

# Run (mount secrets externally)
docker run -d \
  --name timevest \
  -p 7860:7860 \
  --env-file .env \
  -v /path/to/gcp-key.json:/app/gcp-key.json \
  habit-tracker
```

### GCP Compute Engine VM
The app is typically deployed on a GCP VM. Gradio binds to `0.0.0.0:7860`. Ensure:
1. The VM firewall allows inbound TCP on port 7860.
2. The GCP service account has **BigQuery Data Editor** and **BigQuery Job User** IAM roles.
3. Garmin token cache path (`GARMIN_TOKEN_STORE`) is writable inside the container.

### Garmin Sync
A background thread (`run_initial_sync`) runs `sync_garmin_activities()` on startup. This is non-blocking; a failure will log to stdout and not crash the app.
