# ⚡ Chaos Engineering Lite

> 👉 **Website for more info & charts:** https://shri-124.github.io/docker-chaos-lite/  

Spin up a tiny multi-service app with Docker Compose (Nginx → Flask API → Redis), then run a chaos driver that **randomly kills the API** or **adds latency** and **measures recovery time**. Export results to CSV and visualize them on a one-page web UI.

**Skills shown:** fault tolerance, health checks, chaos testing mindset, measurement.

---

## ✨ Features

- **Three services:** `web` (Nginx) → `api` (Flask) → `redis`
- **Chaos driver:** randomly `kill` or inject `latency` (200–1600ms)
- **Metrics:** time-to-recovery (seconds) and average user-visible RTT (seconds)
- **Report:** `chaos_report.csv` + a one-page viewer (`docs/index.html`)
- **Windows-friendly:** PowerShell notes included

---

## 🧱 Architecture

```
Browser ─► web (Nginx) ─► api (Flask) ─► Redis
                           ▲
           chaos.py (kills / latency, writes CSV)
```

- `/health` checks API readiness
- `/api/` increments a Redis counter and returns JSON
- `chaos.py` kills `api` or dials in latency, then measures recovery and RTT

---

## 📦 Prerequisites

- Docker + Docker Compose v2
- Python 3.10+ (for `chaos.py`)
- (Windows) Use **`curl.exe`** or `Invoke-WebRequest` instead of PowerShell's `curl` alias.

---

## 🚀 Quick Start

### 1) Clone and start

```bash
# Clone the repository
git clone https://github.com/shri-124/docker-chaos-lite.git
cd docker-chaos-lite

# Start the services
docker compose up -d --build
```

### Sanity checks

**macOS/Linux:**
```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/api/
```

**Windows PowerShell:**
```powershell
Invoke-WebRequest http://localhost:8080/health
Invoke-WebRequest http://localhost:8080/api/
```

You should see `ok` for health and JSON from `/api/`.

### 2) Run chaos

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PS:  .\.venv\Scripts\Activate.ps1
pip install requests
python chaos/chaos.py
```

This creates `chaos_report.csv` and prints a summary.

### 3) Stop when done

```bash
docker compose down -v
```

---

## 🗂️ Repo Layout

```
chaos-lite/
├─ docker-compose.yml
├─ api/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ app.py              # Flask API (+ /health, /, /chaos?latency_ms=N)
├─ web/
│  ├─ Dockerfile
│  └─ nginx.conf          # reverse proxy to API
├─ chaos/
│  └─ chaos.py            # kills/latency → measures → chaos_report.csv
└─ docs/
   └─ index.html          # drop-in results viewer (GitHub Pages-ready)
```

---

## ⚙️ Configuration (env vars)

You can tweak the chaos run without editing code:

| Variable | Default | What it does |
|----------|---------|--------------|
| `ROUNDS` | 6 | Number of random events |
| `SLEEP_BETWEEN` | 8.0 | Seconds between events |
| `REPORT` | `chaos_report.csv` | Output file |
| `TARGET_CONTAINER` | `chaos-lite-api-1` | API container name (see tips below) |
| `WEB_BASE` | `http://localhost:8080` | Base for user-facing checks |
| `API_BASE` | `http://localhost:8080/api` | Base for latency toggles + RTT sampling |

Run with overrides:

```bash
# example: 10 events, faster pacing
ROUNDS=10 SLEEP_BETWEEN=5 python chaos/chaos.py
```

**PowerShell:**
```powershell
$env:ROUNDS=10; $env:SLEEP_BETWEEN=5; python chaos/chaos.py
```

---

## 📊 Visualize Results

Open `docs/index.html` in a browser and upload `chaos_report.csv` to see:

- **KPIs** (kill count, avg & P95 recovery, avg RTT)
- **Charts** for recovery over time + latency vs observed RTT
- **A table** of all events

### Publish on GitHub Pages

1. Commit `docs/index.html`
2. Settings → Pages → Deploy from branch → branch `main` and folder `/docs`
3. Open the Pages URL and upload your CSV

---

## 🧪 How Recovery Is Measured

1. Chaos driver issues `docker stop` (graceful) or a kill.
2. It starts the API (or relies on `restart: always`) and waits for the port to accept TCP.
3. It polls `HEALTH_URL` until it returns `200 ok`.
4. The elapsed time = **time-to-recovery**.

Latency events set `/chaos?latency_ms=N` on the API, then the script samples RTT to `/api/` and writes the average.

---

## 🛠️ Troubleshooting

### `/api/` 500s right after restart

- Redis may be warming; API returns `503 redis_unavailable` until ready.

### PowerShell `curl` prompts for Uri

- Use `curl.exe` or `Invoke-WebRequest` (PowerShell aliases `curl` to `iwr`).

### Container name mismatch

- Either set `TARGET_CONTAINER` (e.g., `myfolder-api-1`) or pin names in `docker-compose.yml` with `container_name:`.

---

## 🔒 Healthcheck Notes

The `api` healthcheck uses Python (no need to install `curl`):

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request;print(urllib.request.urlopen('http://localhost:5000/health', timeout=2).read().decode())"]
  interval: 5s
  timeout: 2s
  retries: 10
```

This keeps image size small and recovery gating reliable.

---

## 🧹 Handy Commands

```bash
# Show status & restarts
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RestartCount}}"

# Tail logs
docker logs -f chaos-lite-api-1

# Validate Nginx config
docker exec -it chaos-lite-web-1 nginx -t
```

---

## 🎯 What This Demonstrates

- **Fault tolerance:** API restarts automatically; readiness is gated via healthchecks; proxy recovers.
- **Chaos mindset:** Inject *fail-stop* (kills) and *performance* (latency) faults, and measure their user-facing impact.
- **Objective metrics:** Time-to-recovery in seconds, and average RTT under induced latency.

---

Built for learning and demonstration. Perfect for understanding chaos engineering principles in a controlled environment.