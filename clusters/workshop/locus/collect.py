import argparse
import datetime as dt
import hashlib
import json
import math
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NamedTuple

STEP = 15
NANO = 1_000_000_000
QUANTITY = re.compile(r"([0-9]+(?:\.[0-9]+)?)(n|u|m)?")
SCALE = {"n": 1e-9, "u": 1e-6, "m": 1e-3, None: 1.0}
UTC = re.compile(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?Z")


class Fixed(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *request):
        return None


wire = urllib.request.build_opener(Fixed())


def timestamp(text):
    date, part = UTC.fullmatch(text).groups()
    seconds = int(dt.datetime.fromisoformat(date + "+00:00").timestamp())
    return seconds * NANO + int((part or "").ljust(9, "0"))


class Metric(NamedTuple):
    producer: str
    name: str
    unit: str


class Series(NamedTuple):
    name: str
    workload: str


CPU = Metric("workshop.metrics.cpu", "container.cpu", "cores")
PROBE = Metric("workshop.metrics.probe", "probe.duration", "seconds")


def atom(metric, series, at, value):
    identity = hashlib.sha256(f"{metric.producer}\0{series.name}\0{at}".encode()).hexdigest()
    context = {"metric.name": metric.name, "metric.unit": metric.unit, "metric.kind": "gauge",
               "metric.series": series.name, "metric.label.workload": series.workload}
    return dict(at=at, id=identity, producer=metric.producer, context=context, choices=[], payload={"value": value})

def cpu():
    data = subprocess.run(
        ["runseal", ":kube.workshop", "kubectl", "get", "--raw", "/apis/metrics.k8s.io/v1beta1/pods"],
        check=True, capture_output=True, timeout=6,
    )
    entries = []
    for pod in json.loads(data.stdout)["items"]:
        meta = pod["metadata"]
        at = timestamp(pod["timestamp"])
        workload = meta["namespace"] + "/" + meta["name"]
        for container in pod["containers"]:
            match = QUANTITY.fullmatch(container["usage"]["cpu"])
            if not match:
                raise ValueError("unknown CPU quantity")
            value = float(match[1]) * SCALE[match[2]]
            if not math.isfinite(value):
                raise ValueError("invalid CPU quantity")
            series = workload + "/" + container["name"]
            entries.append(atom(CPU, Series(series, workload), at, value))
    return sorted(entries, key=lambda item: item["context"]["metric.series"])[:32]


def health(url):
    start = time.monotonic_ns()
    at = time.time_ns()
    with wire.open(url, timeout=4) as answer:
        if answer.status != 200:
            raise ValueError("health check response")
        answer.read(16384)
    return [atom(PROBE, Series("locus", "locus"), at,
                 (time.monotonic_ns() - start) / NANO)]


def append(api, token, facts):
    if not facts:
        return
    query = urllib.parse.urlencode({"producer": facts[0]["producer"]})
    body = b"".join(json.dumps(fact, separators=(",", ":"), sort_keys=True).encode() + b"\n" for fact in facts)
    key = hashlib.sha256(body).hexdigest()
    request = urllib.request.Request(f"{api}/api/v1/atoms?{query}", data=body, headers={
        "Authorization": "Bearer " + token, "Idempotency-Key": key, "Content-Type": "application/x-ndjson",
    })
    with wire.open(request, timeout=5) as answer:
        if answer.status != 204:
            raise ValueError("append response")


def measure(fetch, api, key, previous):
    try:
        facts = [fact for fact in fetch() if fact["id"] not in previous]
        append(api, key, facts)
        previous.update(fact["id"] for fact in facts)
        return {"accepted": len(facts)}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"status": "missing", "error": type(error).__name__, **(
            {"http": error.code} if isinstance(error, urllib.error.HTTPError) else {})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, help="Isolated Locus endpoint or an authenticated loopback port-forward")
    parser.add_argument("--probe", required=True, help="Workshop HTTPS health URL")
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=86400)
    args = parser.parse_args()
    target = urllib.parse.urlsplit(args.api)
    if target.scheme != "https" and not (target.scheme == "http" and target.hostname in {"127.0.0.1", "::1"}):
        parser.error("pilot credentials require HTTPS or an isolated loopback forward")
    credentials = target.username or target.password
    if credentials or target.query or target.fragment:
        parser.error("pilot API must be a plain origin")
    key = args.key_file.read_text().strip()
    if not key or any(c.isspace() for c in key):
        parser.error("invalid pilot bearer file")
    deadline = time.monotonic() + args.seconds
    wake = time.monotonic()
    seen = set()
    try:
        while time.monotonic() < deadline:
            sample = {
                "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "cpu": measure(cpu, args.api.rstrip("/"), key, seen),
                "probe": measure(lambda: health(args.probe), args.api.rstrip("/"), key, seen),
            }
            print(json.dumps(sample, separators=(",", ":")), flush=True)
            wake += STEP
            time.sleep(max(0, min(deadline, wake) - time.monotonic()))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
