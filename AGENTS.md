# Manifests

## Purpose

Manifests carries the Kubernetes manifests for the cluster platform layer: what
runs beneath the products and above the machines. Hardrig owns the machine and
the K3s substrate it installs, plus access to it. Each product owns its own
lifecycle. The layer between had no owner, and this repository is it.

## Current Boundary

- The repository is named for what it carries, and that name is the boundary:
  **only Kubernetes manifests belong here.** Something that is not a manifest
  does not become one by being placed here; when such a thing appears, its home
  is decided rather than assumed.
- The platform layer means ingress and its certificates, the shared data
  services, scheduling priority, the forge itself, and the sealing plane that
  lets any of them carry a secret. It does not mean product workloads.
- A manifest follows git; the plaintext it seals from does not. That split is
  Runseal's law, not a preference here: `local://` resolves below the ignored
  `.local`. Files there are mode 0600 and directories 0700.
- `.local/secrets/` holds the plaintext inputs `kubeseal` turns into the sealed
  manifests this repository commits, together with the sealing key of each
  cluster. **Sealing keys are per cluster and are not interchangeable**: a
  ciphertext sealed for one cluster cannot be opened in another, so the keys are
  named for their clusters and must stay that way.
- Nothing is committed yet beyond this skeleton. The manifests themselves still
  live in the frozen Infra remote and arrive as separate landings, each named in
  `perish.code/infra-repository-removable`.

## What this repository refuses

- Machine facts and cluster access. A node address, an SSH endpoint, a
  kubeconfig: those are Hardrig's, observed rather than restated.
- Credential values. The plaintext under `.local` is an input to sealing, never
  a committed artifact, and no rendered secret belongs in git.
- Product lifecycles. A workload that belongs to a product belongs in that
  product's repository, even when it runs on this platform.
