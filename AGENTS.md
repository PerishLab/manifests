# Manifests

Read the canonical [PerishLab delivery governance](https://github.com/PerishLab/.github/blob/main/GOVERNANCE.md)
at work start and again before delivery or Issue closure. That document owns
organization-wide Issue, pull-request and acceptance policy; this file keeps
repository-specific constraints without copying that policy.

## Purpose

Manifests owns each cluster's deployment composition, platform resources and
nonsecret product configuration. Fleet and Workshop own their respective machine declarations. Hardrig provides
machine access and K3s substrate operations. Products own their reusable charts and lifecycle. Wharf, Plumb,
Ectropy and Seatrial retain the shared delivery and verification boundaries.

## Cluster declarations

New clusters use a singleword purpose name such as `production` or `workshop`.
New directories and file stems are singleword. Existing historical cluster paths
remain in place until a separately reviewed migration. `cluster.toml` records
purpose, the Runseal profile and the owning repository and stable Hardrig host identity;
it carries no kubeconfig, address or credential. All API and Helm operations,
including validation and recovery, run through the cluster's declared profile.

A cluster may consume a product's formal chart, immutable release identity and
nonsecret instance configuration. The product retains its chart and lifecycle;
this repository owns the cluster composition and operational adoption. Source
Guard remains Plumb/Ectropy through Wharf. Seatrial owns reusable black-box
qualification, not a repository-local replacement pipeline; an unrun scene is
not passing evidence. Content-only shape creates no binary release obligation.

## Current Boundary

- The repository is named for what it carries, and that name is the boundary:
  Kubernetes declarations, their nonsecret values, cluster metadata and
  operating guidance belong here. Product source and private runtime state do not.
- The platform layer means ingress and its certificates, the shared data
  services, scheduling priority, the forge itself, and the sealing plane that
  lets any of them carry a secret. Product workloads are consumed through their owning product's formal chart
  and lifecycle, with instance values and cluster adoption declared here.
- A manifest follows git; the plaintext it seals from does not. That split is
  Runseal's law, not a preference here: `local://` resolves below the ignored
  `.local`. Files there are mode 0600 and directories 0700.
- `.local/secrets/` holds the plaintext inputs `kubeseal` turns into the sealed
  manifests this repository commits, together with the sealing key of each
  cluster. **Sealing keys are per cluster and are not interchangeable**: a
  ciphertext sealed for one cluster cannot be opened in another, so the keys are
  named for their clusters and must stay that way.
- Manifests live under `clusters/<cluster>/`, the shape they had in Infra. The
  cluster is the first axis because a sealing key is cluster-specific and a
  ciphertext sealed for one cluster cannot be opened in another; nothing else
  about the layout is invented here.
- Landed so far: the sealing plane for all three sealed clusters, and the
  platform layer proper — ingress with its certificates and DNS solver on
  `perish.top` and `lab.perish.top`, the shared data services on `perish.top`,
  scheduling priority, `liberte.top`'s shared PostgreSQL, the forge itself, and
  the lab experiment namespace. The identity plane, cluster access and
  everything under `mirror.perish.lan` still live in the frozen Infra remote and
  arrive as separate landings, tracked in PerishLab/manifests#2.
- A script that operated a manifest does not come with it. Three have been left
  behind so far — the sealing-key backup, the Helm smoke test, and Infra's own
  operator commands — each because this repository takes manifests and because
  each depended on a Deno namespace being retired. What they did is written out
  as commands in the AGENTS.md beside the manifest they served, so the procedure
  survives the program.
- Forgejo runs on this platform as part of the platform layer, so its manifest
  belongs here rather than in a product repository. It is no longer where the
  estate's source lives — every repository, this one included, is canonical on
  GitHub — but it stays live and still serves consumers such as the
  `git.perish.top` cargo index. Nothing else about the forge is here: runner
  registration and runtime state live with the mirror cluster, whose landing is
  tracked in PerishLab/manifests#2, and the Forgejo job image has no current
  owner since the images repository was archived. They are named, not copied.
- PostgreSQL exists twice, once per cluster, and the two are unrelated
  instances rather than one service seen from two places. `perish.top`'s is the
  shared data-plane StatefulSet; `liberte.top`'s is that cluster's own
  multi-tenant instance whose sole tenant is authentik. Neither may be treated
  as a copy of the other.
- A ciphertext travels with the workload it belongs to, not with the controller.
  `perish.top` and `liberte.top` keep each `*-sealedsecret.yaml` under its own
  component, so those arrive with their components. `lab.perish.top` keeps its
  one beside the controller, which is how Infra had it.

## What this repository refuses

- Machine facts and private cluster access. Use the owning repository’s host declaration
  and a Runseal profile, not duplicated node addresses, SSH details or kubeconfigs.
- Credential values. The plaintext under `.local` is an input to sealing, never
  a committed artifact, and no rendered secret belongs in git.
- Product lifecycle implementations. Product source and reusable chart templates
  stay with the product; cluster composition and nonsecret instance values live here.
