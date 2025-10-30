import os, time, json, subprocess, re
from prometheus_client import start_http_server, Gauge

# ---------- Config ----------
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "keycloak")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "5"))
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "9323"))
DOCKER_HOST = os.getenv("DOCKER_HOST", "tcp://host.docker.internal:2375")
os.environ["DOCKER_HOST"] = DOCKER_HOST  # docker CLI uses this

# ---------- Metrics (standard names) ----------
g_cpu_percent = Gauge("docker_container_cpu_percent", "Container CPU percent", ["container", "id"])
g_mem_usage   = Gauge("docker_container_memory_usage_bytes", "Container memory usage (bytes)", ["container", "id"])
g_mem_limit   = Gauge("docker_container_memory_limit_bytes", "Container memory limit (bytes)", ["container", "id"])
g_mem_percent = Gauge("docker_container_memory_percent", "Container memory percent", ["container", "id"])

g_net_rx_total = Gauge("docker_container_network_receive_bytes_total", "Network bytes received (total)", ["container", "id"])
g_net_tx_total = Gauge("docker_container_network_transmit_bytes_total", "Network bytes transmitted (total)", ["container", "id"])

g_blk_read_total  = Gauge("docker_container_block_read_bytes_total", "Block IO bytes read (total)", ["container", "id"])
g_blk_write_total = Gauge("docker_container_block_write_bytes_total", "Block IO bytes written (total)", ["container", "id"])

# ---------- Helpers ----------
UNIT = {
    "b": 1, "kb": 1024, "kib": 1024,
    "mb": 1024**2, "mib": 1024**2,
    "gb": 1024**3, "gib": 1024**3,
    "tb": 1024**4, "tib": 1024**4,
}

def parse_bytes(s: str) -> int:
    s = s.strip()
    if not s:
        return 0
    # MiB/KiB/GiB
    if s.lower().endswith("ib"):
        num = float(s[:-3]); unit = s[-3:].lower()
        return int(num * UNIT.get(unit, 1))
    # kB / MB / GB / B
    m = re.match(r"^\s*([\d\.]+)\s*([A-Za-z]+)\s*$", s)
    if m:
        num = float(m.group(1)); unit = m.group(2).lower()
        return int(num * UNIT.get(unit, 1))
    try:
        return int(float(s))
    except Exception:
        return 0

def parse_pair_bytes(s: str):
    # "4.93kB / 0B"
    parts = s.split("/")
    if len(parts) != 2:
        return 0, 0
    return parse_bytes(parts[0].strip()), parse_bytes(parts[1].strip())

def run_docker_stats(container: str):
    # Single JSON record for the named container, with a hard timeout
    cmd = ["docker", "stats", "--no-stream", "--format", "{{json .}}", container]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=3.0)
        line = next((ln for ln in out.splitlines() if ln.strip().startswith("{")), "{}")
        return json.loads(line)
    except subprocess.TimeoutExpired:
        # Return zeros so we still serve /metrics quickly
        return {"Name": container, "ID": "", "CPUPerc": "0%", "MemUsage": "0B / 0B",
                "MemPerc": "0%", "NetIO": "0B / 0B", "BlockIO": "0B / 0B"}
    except Exception as e:
        # Any other docker error → also return zeros
        return {"Name": container, "ID": "", "CPUPerc": "0%", "MemUsage": "0B / 0B",
                "MemPerc": "0%", "NetIO": "0B / 0B", "BlockIO": "0B / 0B"}


def update_metrics():
    stats = run_docker_stats(CONTAINER_NAME)
    # Docker fields: Name, ID, CPUPerc, MemUsage, MemPerc, NetIO, BlockIO
    name = stats.get("Name", CONTAINER_NAME)
    cid  = stats.get("ID", "")

    cpu_perc_str = stats.get("CPUPerc", "0%").replace("%", "").strip() or "0"
    mem_usage_raw = stats.get("MemUsage", "0B / 0B")
    mem_perc_str = stats.get("MemPerc", "0%").replace("%", "").strip() or "0"
    net_io_raw = stats.get("NetIO", "0B / 0B")
    blk_io_raw = stats.get("BlockIO", "0B / 0B")

    mem_used_bytes, mem_limit_bytes = parse_pair_bytes(mem_usage_raw)
    net_rx, net_tx = parse_pair_bytes(net_io_raw)
    blk_read, blk_write = parse_pair_bytes(blk_io_raw)

    labels = {"container": name, "id": cid}

    g_cpu_percent.labels(**labels).set(float(cpu_perc_str))
    g_mem_usage.labels(**labels).set(mem_used_bytes)
    g_mem_limit.labels(**labels).set(mem_limit_bytes)
    g_mem_percent.labels(**labels).set(float(mem_perc_str))
    g_net_rx_total.labels(**labels).set(net_rx)
    g_net_tx_total.labels(**labels).set(net_tx)
    g_blk_read_total.labels(**labels).set(blk_read)
    g_blk_write_total.labels(**labels).set(blk_write)

if __name__ == "__main__":
    # Exposes /metrics on 0.0.0.0:LISTEN_PORT
    start_http_server(LISTEN_PORT)
    while True:
        try:
            update_metrics()
        except Exception as e:
            print(f"[exporter] error: {e}")
        time.sleep(SCRAPE_INTERVAL)
