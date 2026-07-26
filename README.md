# zeroclaw-helm

[![Lint and Test Charts](https://github.com/nebarilabs/zeroclaw-helm/actions/workflows/ci.yaml/badge.svg)](https://github.com/nebarilabs/zeroclaw-helm/actions/workflows/ci.yaml)
[![Release Charts](https://github.com/nebarilabs/zeroclaw-helm/actions/workflows/release.yaml/badge.svg)](https://github.com/nebarilabs/zeroclaw-helm/actions/workflows/release.yaml)
[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/zeroclaw)](https://artifacthub.io/packages/search?repo=zeroclaw)

Helm chart for deploying [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw) on Kubernetes.

## Installation

```bash
helm repo add zeroclaw https://niklasfrick.github.io/zeroclaw-helm
helm repo update
helm install zeroclaw zeroclaw/zeroclaw --set secret.apiKey="sk-..."
```

Or with an existing Kubernetes secret:

```bash
helm install zeroclaw zeroclaw/zeroclaw \
  --set secret.create=false \
  --set secret.existingSecret=zeroclaw-api \
  --set secret.existingSecretKey=API_KEY
```

### From source (development)

```bash
helm install zeroclaw ./chart/zeroclaw --set secret.apiKey="sk-..."
```

## Features

- **Gateway & Daemon modes** — run as a webhook-only server or a full autonomous runtime with channels (Telegram, Discord, etc.)
- **Multi-agent** — define multiple agents with different risk profiles, runtime profiles, and skills
- **Config-driven** — provider, model, pairing, and bind settings via `values.yaml`
- **Persistent storage** — data volume at `/zeroclaw-data` backed by a PVC
- **Ingress & Gateway API** — first-class support for both `Ingress` and `HTTPRoute`
- **Security defaults** — runs as non-root with dropped capabilities

## Configuration

All configuration is done through Helm values. Key settings:

| Value              | Default      | Description                                            |
| ------------------ | ------------ | ------------------------------------------------------ |
| `config.mode`      | `gateway`    | `gateway` (webhook only) or `daemon` (channels require daemon) |
| `config.provider`  | `openrouter` | LLM provider                                           |
| `config.model`     | `""`         | Model override                                         |
| `secret.apiKey`    | `""`         | API key (creates a Kubernetes Secret)                  |
| `persistence.size` | `10Gi`       | PVC size for `/zeroclaw-data`                          |
| `service.targetPort` | `42617`    | Container port (gateway listens on this port)          |

### V3 Named Providers

Route LLM traffic through a custom OpenAI-compatible endpoint:

```yaml
config:
  providers:
    customOllama:
      uri: "http://your-endpoint:80/v1/chat/completions"
      model: "gemma4:26b"
      api_key: "your-key"
```

This renders as `[providers.models.custom.ollama]` in config.toml.

### Multi-Agent

Define multiple agents with different risk profiles and skills:

```yaml
agents:
  default:
    enabled: true
    channels: ["discord.default"]
    model_provider: "custom.ollama"
    risk_profile: "default"
    runtime_profile: "default"
    skill_bundles: [ops]
  ops:
    enabled: true
    model_provider: "custom.ollama"
    risk_profile: "full"
    runtime_profile: "compact"
    skill_bundles: [ops, git-helper, system-info]
```

### Risk Profiles

Control per-agent autonomy and command access:

```yaml
risk_profiles:
  default:
    level: supervised
    workspace_only: true
    allowedCommands: [git, ls, cat, grep, find, echo, pwd]
    requireApprovalForMediumRisk: true
  full:
    level: full
    workspace_only: false
    allowedCommands: [git, ls, cat, grep, find, echo, pwd, kubectl, helm]
    requireApprovalForMediumRisk: false
```

### Runtime Profiles

Control per-agent runtime behavior:

```yaml
runtime_profiles:
  default:
    compactContext: false
    maxHistoryMessages: 50
    maxToolIterations: 10
    parallelTools: false
  compact:
    compactContext: true
    maxHistoryMessages: 25
    maxToolIterations: 100
    parallelTools: true
```

### Peer Groups

Route channels to specific agents with sender gating:

```yaml
peerGroups:
  discord-default:
    channel: "discord.default"
    agents: [default, ops]
    externalPeers: ["123456789"]
```

### A2A Server

Enable the Agent-to-Agent protocol server for multi-agent communication:

```yaml
extraConfig: |
  [a2a]
  enabled = true
  public_base_url = "http://zeroclaw-zeroclaw.zeroclaw.svc.cluster.local:8000"
```

### MCP Bundles

Connect to Model Context Protocol servers for knowledge access:

```yaml
extraConfig: |
  [mcp_bundles.knowledge]
  transport = "sse"
  url = "http://knowledge.knowledge.svc.cluster.local:8080/mcp"
```

See the full values reference and examples in [`chart/zeroclaw/README.md`](chart/zeroclaw/README.md).

## Development

```bash
# Lint
helm lint ./chart/zeroclaw

# Dry-run render
helm template zeroclaw ./chart/zeroclaw

# Install (local cluster)
helm install zeroclaw ./chart/zeroclaw --set secret.apiKey="sk-..."

# Upgrade
helm upgrade zeroclaw ./chart/zeroclaw -f my-values.yaml

# Uninstall
helm uninstall zeroclaw
```

## CI/CD

This repository uses GitHub Actions for continuous integration and release automation:

- **Pull Requests** — every PR to `main` runs chart linting ([chart-testing](https://github.com/helm/chart-testing)), template rendering with multiple value combinations, and schema validation with [kubeconform](https://github.com/yannh/kubeconform). A [kind](https://kind.sigs.k8s.io/) cluster is spun up for install testing.
- **Merge to main** — automatically determines the next [SemVer](https://semver.org/) version from [Conventional Commits](https://www.conventionalcommits.org/), updates `Chart.yaml`, packages the chart, creates a GitHub Release, and publishes to the Helm repository hosted on GitHub Pages.

### Versioning

Commit messages on `main` drive automatic version bumps:

| Commit prefix                | Bump  | Example                         |
| ---------------------------- | ----- | ------------------------------- |
| `fix:`                       | Patch | `fix: correct probe path`       |
| `feat:`                      | Minor | `feat: add ServiceMonitor`      |
| `feat!:` / `BREAKING CHANGE` | Major | `feat!: rename values root key` |

## Repository Setup

To enable the Helm repository on GitHub Pages:

1. Go to **Settings > Pages** in this repository.
2. Set **Source** to **Deploy from a branch**.
3. Set **Branch** to `gh-pages` and path to `/ (root)`.
4. Save.

The release workflow will create the `gh-pages` branch automatically on the first release.

## License

See [LICENSE](LICENSE).
