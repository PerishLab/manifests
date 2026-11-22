#!/bin/bash
set -euo pipefail
umask 077
source_dir="$(cd "$(dirname "$0")" && pwd -P)"
cd "${1:?private state directory required}"
port=43986
pid=
trap 'if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; fi' EXIT
start() {
    runseal :kube.workshop kubectl port-forward -n workshop-locus-metrics service/locus-metrics "$port":8080 --address 127.0.0.1 >> forward.log 2>&1 &
    pid=$!
}
start
for ((i=0;i<80;i++)); do
    if curl --noproxy '*' -fsS --max-time 2 "http://127.0.0.1:$port/health" >/dev/null 2>&1; then break; fi
    kill -0 "$pid"
    sleep .25
done
curl --noproxy '*' -fsS --max-time 2 "http://127.0.0.1:$port/health" >/dev/null
start_time="$(date -u +%FT%TZ)"
printf '%s\n' "$start_time" > sample-start.utc
python3 -B "$source_dir/collect.py" --api "http://127.0.0.1:$port" --probe https://api.locus.workshop.liberte.host/health --key-file writer.key >> samples.ndjson &
collector=$!
for ((elapsed=0; elapsed<86520; elapsed+=10)); do
    if ! kill -0 "$collector" 2>/dev/null; then wait "$collector"; date -u +%FT%TZ > sample-end.utc; exit; fi
    if ! kill -0 "$pid" 2>/dev/null; then wait "$pid" 2>/dev/null || true; start; fi
    sleep 10
done
wait "$collector"
date -u +%FT%TZ > sample-end.utc
