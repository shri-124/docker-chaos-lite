"""
Chaos Engineering Lite:
- Randomly kill the 'api' container and measure time until /health returns 200 via the web proxy.
- Randomly add latency to the API (via /chaos) and measure average RTT impact.
- Writes a CSV report and prints a summary.

Requirements:
  pip install requests
  Docker CLI available in PATH.
"""

import csv, os, random, subprocess, sys, time
from datetime import datetime
import requests

WEB_BASE = os.environ.get("WEB_BASE", "http://localhost:8080")
API_BASE = os.environ.get("API_BASE", "http://localhost:8080/api")
HEALTH_URL = os.environ.get("HEALTH_URL", "http://localhost:5001/health")
CONTAINER = os.environ.get("TARGET_CONTAINER", "chaos-lite-api-1")  # docker compose v2 default name
ROUNDS = int(os.environ.get("ROUNDS", "6"))
SLEEP_BETWEEN = float(os.environ.get("SLEEP_BETWEEN", "8.0"))
REPORT = os.environ.get("REPORT", "chaos_report.csv")

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def wait_for_health(timeout=60.0, interval=0.5):
    start = time.time()
    end = start + timeout
    last_err = None
    while time.time() < end:
        try:
            r = requests.get(f"{WEB_BASE}/health", timeout=3)
            if r.status_code == 200 and r.text.strip() == "ok":
                return time.time() - start
        except requests.RequestException as e:
            last_err = e
        time.sleep(interval)
    raise TimeoutError(f"health never recovered in {timeout}s; last_err={last_err}")

def set_latency(ms: int):
    try:
        r = requests.post(f"{API_BASE}/chaos", params={"latency_ms": ms}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"[warn] failed to set latency {ms}ms: {e}")

def sample_rtt(samples=10):
    rtts = []
    for _ in range(samples):
        t0 = time.time()
        try:
            r = requests.get(f"{API_BASE}/", timeout=10)
            r.raise_for_status()
        except Exception:
            rtts.append(None)
        else:
            rtts.append(time.time() - t0)
        time.sleep(0.25)
    # return avg over non-None
    valid = [x for x in rtts if x is not None]
    return sum(valid)/len(valid) if valid else None

def kill_container(name: str):
    print(f"[chaos] docker kill {name}")
    sh(f"docker kill {name}")

def start_container(name: str):
    print(f"[info] ensuring {name} is up (compose will auto-restart)")
    # Compose restarts automatically, but we can nudge if needed:
    sh(f"docker start {name}")

def main():
    # warm up health
    print("[info] warming up...")
    _ = wait_for_health(timeout=90.0)
    print("[info] healthy.")

    with open(REPORT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp","event","param","recovery_seconds","avg_rtt_seconds"])

        for i in range(ROUNDS):
            event = random.choice(["kill", "latency"])
            ts = datetime.utcnow().isoformat()

            if event == "kill":
                kill_container(CONTAINER)
                start_container(CONTAINER)

                try:
                    rec = wait_for_health(timeout=90.0)
                except TimeoutError as e:
                    rec = None
                    print(f"[error] {e}")

                w.writerow([ts,"kill",CONTAINER,rec,""])
                #start_container(CONTAINER)

            else:  # latency
                ms = random.choice([200, 400, 800, 1200, 1600])
                print(f"[chaos] add latency {ms}ms")
                set_latency(ms)
                # measure impact on RTT
                avg_rtt = sample_rtt(samples=12)
                w.writerow([ts,"latency",ms,"",avg_rtt])
                # clear latency
                set_latency(0)

            f.flush()
            time.sleep(SLEEP_BETWEEN)

    print(f"\n=== run complete ===\nreport: {REPORT}")
    # quick summary
    kills, recs, lats, rtts = 0, [], 0, []
    with open(REPORT, newline="") as f:
        for row in csv.DictReader(f):
            if row["event"] == "kill":
                kills += 1
                if row["recovery_seconds"]:
                    recs.append(float(row["recovery_seconds"]))
            else:
                lats += 1
                if row["avg_rtt_seconds"]:
                    rtts.append(float(row["avg_rtt_seconds"]))
    if kills:
        print(f"kills: {kills}, avg recovery: { (sum(recs)/len(recs)) if recs else 'n/a'} s")
    if lats:
        print(f"latency events: {lats}, avg RTT under latency: { (sum(rtts)/len(rtts)) if rtts else 'n/a'} s")
    print("tip: open the CSV in a sheet for a quick chart.")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[info] interrupted; clearing latency and exiting…")
        set_latency(0)
        sys.exit(0)
