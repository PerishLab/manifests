import argparse
import base64
import hashlib
import json
import os
import subprocess
import urllib.parse
from pathlib import Path
import jwt
from collect import wire

NS = "workshop-locus-metrics"
ISSUER = "https://ensign.workshop.liberte.host/api"
VERSION = "0.23.0"


def kube(*args, data=None):
    return subprocess.run(["runseal", ":kube.workshop", "kubectl", *args], check=True, input=data, capture_output=True).stdout


def work(*args):
    subprocess.run(["runseal", ":kube.workshop", *args], check=True)


def read(url, data=None):
    with wire.open(url, data=data, timeout=10) as answer:
        return json.load(answer)


def qualify():
    record = f"https://releases.locus.perish.uk/v1/releases/stable/v{VERSION}/distribution.json"
    available = json.loads(subprocess.run(
        ["curl", "-fsS", "--max-time", "10", record], check=True, capture_output=True,
    ).stdout)
    if available["state"] != "complete" or available["media"]["chart"] != "published" or available["media"]["oci"] != "published":
        raise RuntimeError("stable service artifacts are incomplete")
    if available["commit"] != "24445e44488ae1b419d92ab810ee9dd532da62cd":
        raise RuntimeError("unexpected Locus revision")
    key = json.loads(kube("get", "secret", "-n", "workshop-ensign", "ensign-workshop-agent-key", "-o", "json"))
    bearer = base64.b64decode(key["data"]["value"], validate=True).decode().strip()
    jwks = read(ISSUER + "/.well-known/jwks.json")
    grant = read(ISSUER+"/token", urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "subject_token": bearer, "resource": "locus",
    }).encode())
    access = grant["access_token"]
    selector = jwt.get_unverified_header(access)["kid"]
    jwk, = [key for key in jwks["keys"] if key["kid"] == selector and key["alg"] == "ES256"]
    claims = jwt.decode(access, jwt.PyJWK.from_dict(jwk).key, algorithms=["ES256"],
                        audience="locus", issuer=ISSUER, options={"require":["sub","exp","iss","aud"]})
    if claims["sub"] != "workshop-agent":
        raise RuntimeError("unexpected collector identity")
    return bearer, jwks, claims["sub"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    folder = parser.parse_args().directory
    os.umask(0o077)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if folder.stat().st_mode & 0o077:
        raise RuntimeError("pilot state directory must be private")
    bearer, jwks, subject = qualify()
    key = folder / "writer.key"
    key.write_text(bearer + "\n")
    key.chmod(0o600)
    values = folder / "values.json"
    values.write_text(json.dumps({"issuer":ISSUER,"jwks":jwks,"storage":{"size":"1Gi"}}))
    labels = {"app.kubernetes.io/part-of": "workshop-locus-metrics"}
    current = kube("get", "namespace", NS, "--ignore-not-found", "-o", "json")
    if current:
        if json.loads(current)["metadata"].get("labels", {}).get("app.kubernetes.io/part-of") != labels["app.kubernetes.io/part-of"]:
            raise RuntimeError("namespace belongs to another workload")
    else:
        namespace = {"apiVersion":"v1","kind":"Namespace","metadata":{"name":NS,"labels":labels}}
        kube("create", "-f", "-", data=json.dumps(namespace).encode())
    policy = {"apiVersion":"networking.k8s.io/v1","kind":"NetworkPolicy",
              "metadata":{"name":"port-forward-only","namespace":NS},
              "spec":{"podSelector":{},"policyTypes":["Ingress"],"ingress":[]}}
    kube("apply","-f","-",data=json.dumps(policy).encode())
    work("helm","upgrade","--install","locus-metrics","oci://ghcr.io/perishlab/charts/locus",
         "--version",VERSION,"-n",NS,"-f",str(values),"--wait","--timeout","3m")
    for producer in ("workshop.metrics.cpu","workshop.metrics.probe"):
        work("kubectl","exec","-n",NS,"deploy/locus-metrics","--","locus-api","access","--home","/data",
             "grant","--subject",subject,"--issuer",ISSUER,"--producer",producer,"append")
        work("kubectl","exec","-n",NS,"deploy/locus-metrics","--","locus-api","access","--home","/data",
             "grant","--subject",subject,"--issuer",ISSUER,"--producer",producer,"scan")
    record = {"version":VERSION,"namespace":NS,"issuer":ISSUER,
              "jwks_digest":hashlib.sha256(json.dumps(jwks,sort_keys=True).encode()).hexdigest()}
    (folder/"deployment.json").write_text(json.dumps(record,indent=2))
    print(json.dumps(record))


if __name__ == "__main__":
    main()
