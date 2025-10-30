#!/usr/bin/env python3
import os, time, threading, requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

LOCUST_URL = os.getenv("LOCUST_URL", "http://locust:8089")
SCRAPE_EVERY = float(os.getenv("SCRAPE_EVERY", "5"))  # seconds
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "9324"))

reg = CollectorRegistry()

g_users = Gauge("locust_users", "Current number of simulated users in Locust", registry=reg)
g_state = Gauge("locust_state", "Locust state: 0=stopped,1=spawning,2=running,3=stopping,4=cleaning_up", registry=reg)

g_total_rps = Gauge("locust_total_rps", "Total requests per sec", registry=reg)
g_total_fail_rps = Gauge("locust_total_fail_rps", "Total failed requests per sec", registry=reg)

g_endpoint_rps = Gauge("locust_endpoint_rps", "Endpoint requests per sec", ["name","method"], registry=reg)
g_endpoint_fail_rps = Gauge("locust_endpoint_fail_rps", "Endpoint failed requests per sec", ["name","method"], registry=reg)

g_latency_avg_ms = Gauge("locust_latency_avg_ms", "Average response time (ms)", registry=reg)
g_latency_p95_ms = Gauge("locust_latency_p95_ms", "p95 response time (ms)", registry=reg)

STATE_MAP = {"stopped":0, "spawning":1, "running":2, "stopping":3, "cleaning_up":4}

def poll():
    while True:
        try:
            r = requests.get(f"{LOCUST_URL}/stats/requests", timeout=5)
            data = r.json()

            # Core high-level fields
            state = data.get("state", "stopped")
            user_count = data.get("user_count", 0)
            g_users.set(user_count)
            g_state.set(STATE_MAP.get(state, 0))

            # Totals live on the row with name == "Total"
            total = next((s for s in data.get("stats", []) if s.get("name") == "Total"), None)
            if total:
                g_total_rps.set(total.get("current_rps", 0.0))
                g_total_fail_rps.set(total.get("current_fail_per_sec", 0.0))
                g_latency_avg_ms.set(total.get("avg_response_time", 0.0))
                g_latency_p95_ms.set(data.get("current_response_time_percentile_95", 0.0))

            # Per-endpoint series (skip Total)
            for s in data.get("stats", []):
                name = s.get("name", "")
                if name == "Total":
                    continue
                method = s.get("method", "")
                g_endpoint_rps.labels(name=name, method=method).set(s.get("current_rps", 0.0))
                g_endpoint_fail_rps.labels(name=name, method=method).set(s.get("current_fail_per_sec", 0.0))
        except Exception:
            # keep exporter alive even if Locust is temporarily down
            pass
        time.sleep(SCRAPE_EVERY)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404); self.end_headers(); return
        out = generate_latest(reg)
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    HTTPServer(("0.0.0.0", LISTEN_PORT), Handler).serve_forever()
