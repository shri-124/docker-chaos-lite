import os, time, socket
from flask import Flask, jsonify, request
import redis

app = Flask(__name__)

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
)

# global latency knob (ms). health endpoint ignores this so recovery is measurable.
CHAOS_LATENCY_MS = int(os.environ.get("CHAOS_LATENCY_MS", "0"))

@app.route("/health")
def health():
    # simple health that doesn't sleep
    try:
        r.ping()
        return "ok", 200
    except Exception:
        return "redis-down", 503


@app.route("/")
def index():
    global CHAOS_LATENCY_MS
    if CHAOS_LATENCY_MS > 0:
        time.sleep(CHAOS_LATENCY_MS / 1000.0)

    try:
        count = r.incr("hits")
    except Exception as e:
        # surface a clear, non-500 signal while Redis stabilizes
        return jsonify({"error": "redis_unavailable", "detail": str(e)}), 503

    return jsonify({"service": "api", "host": socket.gethostname(), "hits": count})


@app.route("/chaos", methods=["POST"])
def chaos():
    """
    Toggle request latency: POST /chaos?latency_ms=1500
    Set to 0 to clear.
    """
    global CHAOS_LATENCY_MS
    try:
        ms = int(request.args.get("latency_ms", "0"))
        CHAOS_LATENCY_MS = max(0, ms)
        return jsonify({"latency_ms": CHAOS_LATENCY_MS})
    except ValueError:
        return jsonify({"error": "latency_ms must be an integer"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
