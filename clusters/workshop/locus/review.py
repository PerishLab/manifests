import argparse
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from pathlib import Path
from collect import CPU, PROBE, NANO, wire


def query(api, token, metric, window):
    params = urllib.parse.urlencode({"producer": metric.producer, "name": metric.name,
                                     "unit": metric.unit, "kind": "gauge", "group": "workload",
                                     "from": window[0], "to": window[1], "step": 15 * NANO})
    request = urllib.request.Request(api + "/api/v1/metrics?" + params, headers={"Authorization": "Bearer " + token})
    start = time.monotonic_ns()
    with wire.open(request, timeout=5) as answer:
        data = json.load(answer)
    return data, (time.monotonic_ns() - start) / 1_000_000


def counts(report):
    groups = report["groups"]
    slots = [bucket for group in groups for bucket in group["buckets"]]
    return {"groups": len(groups), "slots": len(slots), "samples": sum(slot["samples"] for slot in slots),
            "missing": sum(slot["quality"] == "missing" for slot in slots),
            "conflict": sum(slot["quality"] == "conflict" for slot in slots)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--port", type=int, default=43986)
    parser.add_argument("--reads", type=int, default=60)
    args = parser.parse_args()
    location = f"http://127.0.0.1:{args.port}"
    token = (args.directory / "writer.key").read_text().strip()
    now = time.time_ns()
    window = (now - 3600 * NANO, now)
    cpu, _ = query(location, token, CPU, window)
    latency = []
    for _ in range(args.reads):
        report, elapsed = query(location, token, PROBE, window)
        latency.append(elapsed)
    print(json.dumps({"window":window, "cpu":counts(cpu), "probe":counts(report), "reads":len(latency),
                      "milliseconds":{"median":statistics.median(latency),
                                      "p95":sorted(latency)[math.ceil(len(latency) * .95) - 1]}}))


if __name__ == "__main__":
    main()
