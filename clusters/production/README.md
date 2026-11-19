# Production

`cluster.toml` records this cluster's purpose, authoritative substrate reference,
Runseal entry and selected formal Ensign release. It is metadata, not a new
configuration parser. Kubernetes resources are built from `kustomization.yaml`.
The product owns the chart and its bootstrap/upgrade contract; this repository
selects the instance configuration. Operations use `runseal :kube.production`.

## Adoption

Resolve the declared release authority, verify its stable channel seal and
complete distribution, and match the chart OCI digest recorded in `cluster.toml`
before applying. Do not use an unqualified checkout chart or a moving image tag.
The formal chart is `oci://ghcr.io/perishlab/charts/ensign`, version `0.11.0`.
Image and chart use the same formal release marker.

Provision namespace `ensign` and its private `registry` Secret before starting
the HelmChart. The Secret is type `kubernetes.io/dockerconfigjson` and contains
only a qualified read:packages credential for GHCR. It serves both chart download
and image pulls; no repository or organization administration credential belongs
in the cluster. Obtain it through private custody, never command arguments or
committed YAML. Inventory existing secrets without printing their values.

`access.yaml` supplies imagePullSecrets on the chart's two named ServiceAccounts.
Its release metadata permits ordinary Helm adoption of those accounts; the chart
owns RBAC, and Kubernetes copies pull references from each account into newly
created Pods. Reapply the access declaration before an install or upgrade and
verify the resulting Pod references. It adds no Secret-read permission to serve.

Validate and adopt through the declared profile from the repository root:

```sh
runseal :kube.production kubectl apply -f clusters/production/ensign/namespace.yaml
runseal :kube.production kubectl apply --dry-run=server -k clusters/production
runseal :kube.production kubectl diff -k clusters/production
runseal :kube.production kubectl apply -k clusters/production
runseal :kube.production helm list --all --namespace ensign
runseal :kube.production kubectl get jobs,pods,pvc,ingress --namespace ensign
```

The existing K3s Helm controller consumes the declaration. Do not run a competing
manual Helm mutation. Chart operations abort on failure instead of automatically
uninstalling the identity service. Observe the exact release revision, Job and
resources before another change; never blindly replay an uncertain operation.
A chart update requires reviewed values and release provenance, including the
product's single-process/Recreate lifecycle. Serving must get only its named
signing Secret, not sudo or Secret create/update permissions.

## Identity

The hostname is `ensign.perish.cn`; the canonical issuer is
`https://ensign.perish.cn/api` because the product mounts OIDC below `/api`.
The whole hostname routes to the API, including the embedded browser assets.
Discovery, JWKS and health are respectively below `/api/.well-known/` and
`/api/health`. Clients and Alibaba trust use the full canonical issuer.

Workshop's existing Ensign estate is not implicitly replaced by this declaration.
Before production bootstrap, explicitly settle whether the estate is promoted
or independent. Promotion retains a matched database/sudo/signing/consumer-key
set, freezes source writes for the final snapshot, restores before any target
bootstrap, verifies stable subjects and keys, and migrates consumers without
allowing independent writable copies. Never create a fresh estate and describe
it as a migration. Keep a source rollback reference until cutover is qualified.

## Persistence and recovery

Traefik uses one replica and a local-path PVC for ACME state at `/data/acme.json`.
Its production resolver uses TLS-ALPN-01 on port 443, so no DNS API credential is
needed on this cluster. HTTP redirects to HTTPS. The ACME contact follows the
existing estate contact. Ensign's bundled PostgreSQL gets an 8 GiB local-path
PVC; inspect the real PV path against Hardrig's declared data mount. Both are
single-node storage, with no claim of HA or offsite disaster recovery.

Retain a matched off-cluster recovery set in a private, access-restricted seat:
PostgreSQL's logical dump, `ensign-store`, `ensign-sudo`, `ensign-signing` and
any consumer key artifacts, plus ACME state and exact deployment identities.
Rendered Helm state and all Secret responses are private too. Back up through
`runseal :kube.production` without echoing bytes; public evidence contains only
identities, digests, counts, readiness and results. Local-path survival after
restart is not a backup. Rehearse PostgreSQL restore into an isolated database
and compare the identity/signing bindings before claiming recovery works.

Record rollout, restart, backup/restore and runtime permission results on the
native Issue. Reusable product black-box checks belong to Seatrial; this content
closure's Plumb/Ectropy Guard is not proof that those checks ran. Do not publish
credentials or generate a second lifecycle/guard wrapper here.
