# ZeroClaw Helm Chart

This chart deploys [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw) on Kubernetes.

It is built from upstream runtime behavior:
- Docker image expects data under `/zeroclaw-data`
- Runs in `gateway` (webhook only) or `daemon` (full runtime) mode, both on port `3000` by default
- `API_KEY` and provider settings are passed by environment variables
- Full `config.toml` is generated from Helm values and mounted via ConfigMap
- Channel tokens and other sensitive values are injected from Kubernetes Secrets at startup

## Prerequisites

- Kubernetes 1.24+
- Helm 3.12+
- A StorageClass (or an existing PVC) if persistence is enabled

## Install

```bash
helm install zeroclaw ./chart/zeroclaw \
  --set secret.apiKey="sk-..."
```

Or use an existing secret:

```bash
helm install zeroclaw ./chart/zeroclaw \
  --set secret.create=false \
  --set secret.existingSecret=zeroclaw-api \
  --set secret.existingSecretKey=API_KEY
```

## Upgrade

```bash
helm upgrade zeroclaw ./chart/zeroclaw -f my-values.yaml
```

## Uninstall

```bash
helm uninstall zeroclaw
```

## Configuration Notes

- **Runtime mode**: set `config.mode` to choose the runtime:
  - `gateway` (default) — HTTP webhook server only. You call `POST /webhook` to interact.
  - `daemon` — full autonomous runtime: gateway + channels (Telegram, Discord, …) + heartbeat + memory.
- **Pairing**: set `config.requirePairing: true` to enable the 6-digit pairing flow for bearer tokens. Defaults to `false` for Kubernetes (network-level auth via ClusterIP/ingress is usually sufficient).
- **Persistence**: data is mounted at `/zeroclaw-data` (config and workspace live there).
- **API key**: always injected into `API_KEY` from a Kubernetes Secret (generated or existing).
- **config.toml**: fully generated from Helm values — every ZeroClaw config section is configurable.
- **Security**: container runs as non-root (`65534`) with dropped Linux capabilities.
- **Pod restart on config change**: deployment annotations include checksums of the ConfigMap and Secrets, so pods automatically restart when configuration changes.

## Key Values

| Key                      | Type   | Default                            | Description                                 |
| ------------------------ | ------ | ---------------------------------- | ------------------------------------------- |
| `image.repository`       | string | `ghcr.io/theonlyhennygod/zeroclaw` | ZeroClaw image repository                   |
| `image.tag`              | string | `latest`                           | ZeroClaw image tag                          |
| `replicaCount`           | int    | `1`                                | Deployment replica count                    |
| `service.type`           | string | `ClusterIP`                        | Kubernetes Service type                     |
| `service.port`           | int    | `3000`                             | Service port                                |
| `config.mode`            | string | `gateway`                          | `gateway` (webhook only) or `daemon` (full) |
| `config.provider`        | string | `openrouter`                       | LLM provider                                |
| `config.model`           | string | `""`                               | Model override (empty = provider default)   |
| `config.temperature`     | float  | `0.7`                              | LLM temperature                             |
| `config.allowPublicBind` | bool   | `true`                             | Allow non-localhost bind                    |
| `config.requirePairing`  | bool   | `false`                            | Require pairing code                        |

### Memory

| Key                                  | Type   | Default  | Description                               |
| ------------------------------------ | ------ | -------- | ----------------------------------------- |
| `config.memory.backend`              | string | `sqlite` | `sqlite`, `lucid`, `markdown`, `none`     |
| `config.memory.autoSave`             | bool   | `true`   | Auto-save conversation context            |
| `config.memory.embeddingProvider`    | string | `none`   | `none`, `openai`, `custom:URL`            |
| `config.memory.vectorWeight`         | float  | `0.7`    | Vector similarity weight in hybrid search |
| `config.memory.keywordWeight`        | float  | `0.3`    | Keyword BM25 weight in hybrid search      |
| `config.memory.responseCacheEnabled` | bool   | `false`  | Cache LLM responses                       |

### Autonomy

| Key                               | Type   | Default            | Description                      |
| --------------------------------- | ------ | ------------------ | -------------------------------- |
| `config.autonomy.level`           | string | `supervised`       | `readonly`, `supervised`, `full` |
| `config.autonomy.workspaceOnly`   | bool   | `true`             | Scope filesystem to workspace    |
| `config.autonomy.allowedCommands` | list   | `[git,npm,...]`    | Allowed shell commands           |
| `config.autonomy.forbiddenPaths`  | list   | `[/etc,/root,...]` | Blocked filesystem paths         |

### Runtime

| Key                     | Type   | Default  | Description                                              |
| ----------------------- | ------ | -------- | -------------------------------------------------------- |
| `config.runtime.kind`   | string | `native` | `native` or `docker`                                     |
| `config.runtime.shell`  | string | `sh`     | Shell interpreter for the native runtime                 |

### Browser

| Key                              | Type   | Default                | Description                              |
| -------------------------------- | ------ | ---------------------- | ---------------------------------------- |
| `config.browser.enabled`         | bool   | `false`                | Enable browser capabilities              |
| `config.browser.automationEnabled` | bool | `false`                | Enable the full browser automation tool  |
| `config.browser.allowedDomains`  | list   | `[]`                   | Allowed domains (`[]` means unrestricted) |
| `config.browser.backend`         | string | `agent_browser`        | Browser backend implementation           |

### Skills

| Key                        | Type | Default | Description                                                                        |
| -------------------------- | ---- | ------- | ---------------------------------------------------------------------------------- |
| `config.skills.openSkills` | bool | `false` | Auto-clone community open-skills repo on startup (requires `git` in the container) |

### Channels

| Key                                       | Type   | Default | Description                    |
| ----------------------------------------- | ------ | ------- | ------------------------------ |
| `config.channels.telegram.enabled`        | bool   | `false` | Enable Telegram channel        |
| `config.channels.telegram.allowedUsers`   | list   | `[]`    | Telegram usernames or user IDs |
| `config.channels.discord.enabled`         | bool   | `false` | Enable Discord channel         |
| `config.channels.discord.guildId`         | string | `""`    | Discord guild ID filter        |
| `config.channels.discord.allowedUsers`    | list   | `[]`    | Discord user IDs               |
| `config.channels.discord.listenToBots`    | bool   | `false` | Listen to bot messages         |
| `config.channels.slack.enabled`           | bool   | `false` | Enable Slack channel           |
| `config.channels.slack.channelId`         | string | `""`    | Slack channel to listen on     |
| `config.channels.slack.allowedUsers`      | list   | `[]`    | Slack member IDs               |
| `config.channels.whatsapp.enabled`        | bool   | `false` | Enable WhatsApp channel        |
| `config.channels.whatsapp.phoneNumberId`  | string | `""`    | WhatsApp phone number ID       |
| `config.channels.whatsapp.allowedNumbers` | list   | `[]`    | E.164 numbers or `["*"]`       |
| `config.channels.matrix.enabled`          | bool   | `false` | Enable Matrix channel          |
| `config.channels.matrix.homeserver`       | string | `""`    | Matrix homeserver URL          |
| `config.channels.matrix.roomId`           | string | `""`    | Matrix room ID                 |
| `config.channels.matrix.allowedUsers`     | list   | `[]`    | Matrix user IDs                |
| `config.channels.irc.enabled`             | bool   | `false` | Enable IRC channel             |
| `config.channels.lark.enabled`            | bool   | `false` | Enable Lark/Feishu channel     |
| `config.channels.dingtalk.enabled`        | bool   | `false` | Enable DingTalk channel        |

### Secrets

| Key                                   | Type   | Default   | Description                         |
| ------------------------------------- | ------ | --------- | ----------------------------------- |
| `secret.create`                       | bool   | `true`    | Create API key secret               |
| `secret.apiKey`                       | string | `""`      | API key value                       |
| `secret.existingSecret`               | string | `""`      | Existing secret name                |
| `secret.existingSecretKey`            | string | `API_KEY` | Key name in the secret              |
| `channelSecrets.create`               | bool   | `false`   | Create channel secrets              |
| `channelSecrets.existingSecret`       | string | `""`      | Existing secret with channel tokens |
| `channelSecrets.telegramBotToken`     | string | `""`      | Telegram bot token                  |
| `channelSecrets.discordBotToken`      | string | `""`      | Discord bot token                   |
| `channelSecrets.slackBotToken`        | string | `""`      | Slack bot token                     |
| `channelSecrets.whatsappAccessToken`  | string | `""`      | WhatsApp access token               |
| `channelSecrets.whatsappVerifyToken`  | string | `""`      | WhatsApp verify token               |
| `channelSecrets.matrixAccessToken`    | string | `""`      | Matrix access token                 |
| `channelSecrets.larkAppSecret`        | string | `""`      | Lark app secret                     |
| `channelSecrets.dingtalkClientSecret` | string | `""`      | DingTalk client secret              |
| `channelSecrets.composioApiKey`       | string | `""`      | Composio API key                    |

### Persistence

| Key                         | Type   | Default | Description                     |
| --------------------------- | ------ | ------- | ------------------------------- |
| `persistence.enabled`       | bool   | `true`  | Enable PVC for `/zeroclaw-data` |
| `persistence.existingClaim` | string | `""`    | Use existing PVC                |
| `persistence.size`          | string | `10Gi`  | PVC requested size              |
| `persistence.storageClass`  | string | `""`    | StorageClass override           |

The init container enforces `0600` on SQLite databases and their `-wal`/`-shm` files under `/zeroclaw-data/.zeroclaw`, as required by ZeroClaw v0.8.6+.

### Networking

| Key                    | Type | Default | Description                  |
| ---------------------- | ---- | ------- | ---------------------------- |
| `ingress.enabled`      | bool | `false` | Create Ingress               |
| `httpRoute.enabled`    | bool | `false` | Create Gateway API HTTPRoute |
| `httpRoute.parentRefs` | list | `[]`    | Parent Gateway references    |
| `httpRoute.hostnames`  | list | `[]`    | HTTPRoute hostnames          |

## Channel Secrets

ZeroClaw reads channel tokens (Telegram bot token, Discord bot token, etc.) from `config.toml`, **not** from environment variables. The chart handles this through an init container that injects secret values into the generated `config.toml` at pod startup.

### How it works

1. The ConfigMap generates `config.toml` with `__SECRET_*__` placeholders for sensitive values
2. A Kubernetes Secret holds the actual tokens/passwords
3. An init container copies `config.toml` and replaces placeholders with real values from the mounted Secret
4. If a secret key is missing, the placeholder line is removed (the channel will use defaults or fail gracefully)

### Option A: Let Helm create the secret

```yaml
config:
  mode: daemon
  channels:
    telegram:
      enabled: true
      allowedUsers: ["myusername"]

channelSecrets:
  create: true
  telegramBotToken: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

### Option B: Reference an existing Kubernetes Secret

```bash
# Create the secret manually
kubectl create secret generic zeroclaw-channels \
  --from-literal=TELEGRAM_BOT_TOKEN="123456:ABC-DEF..." \
  --from-literal=DISCORD_BOT_TOKEN="MTIz..."
```

```yaml
config:
  mode: daemon
  channels:
    telegram:
      enabled: true
      allowedUsers: ["myusername"]
    discord:
      enabled: true
      allowedUsers: ["123456789"]

channelSecrets:
  existingSecret: zeroclaw-channels
```

### Custom key names

If your existing Secret uses different key names, override them via `channelSecrets.secretKeys`:

```yaml
channelSecrets:
  existingSecret: my-existing-secret
  secretKeys:
    telegramBotToken: MY_TG_TOKEN
    discordBotToken: MY_DISCORD_TOKEN
```

## Example: Full daemon with Telegram

```yaml
config:
  mode: daemon
  provider: anthropic
  model: anthropic/claude-sonnet-4-20250514
  memory:
    backend: sqlite
    embeddingProvider: openai
  channels:
    telegram:
      enabled: true
      allowedUsers: ["myusername", "123456789"]

secret:
  create: true
  apiKey: "sk-ant-..."

channelSecrets:
  create: true
  telegramBotToken: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

## Example: Daemon with WhatsApp

```yaml
config:
  mode: daemon
  provider: openrouter
  channels:
    whatsapp:
      enabled: true
      phoneNumberId: "123456789012345"
      allowedNumbers: ["+1234567890"]

secret:
  create: true
  apiKey: "sk-or-..."

channelSecrets:
  create: true
  whatsappAccessToken: "EAABx..."
  whatsappVerifyToken: "my-secret-verify-token"
```

## Example: Multiple channels

```yaml
config:
  mode: daemon
  provider: openrouter
  channels:
    telegram:
      enabled: true
      allowedUsers: ["alice", "bob"]
    discord:
      enabled: true
      guildId: "123456789"
      allowedUsers: ["111222333"]
    slack:
      enabled: true
      channelId: "C12345"
      allowedUsers: ["U12345"]

channelSecrets:
  create: true
  telegramBotToken: "..."
  discordBotToken: "..."
  slackBotToken: "xoxb-..."
```

## Advanced: Extra configuration

For options not covered by structured values (e.g., email channel, model routes, delegate agents), use `config.extraConfig` to append raw TOML:

```yaml
config:
  extraConfig: |
    [[model_routes]]
    hint = "reasoning"
    provider = "openrouter"
    model = "anthropic/claude-opus-4-20250514"

    [[model_routes]]
    hint = "fast"
    provider = "groq"
    model = "llama-3.3-70b-versatile"
```

## Exposing ZeroClaw

Use either `Ingress` **or** Gateway API `HTTPRoute` (mutually exclusive):

```yaml
# Ingress
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: zeroclaw.example.com
      paths:
        - path: /
          pathType: Prefix
```

```yaml
# Gateway API HTTPRoute
httpRoute:
  enabled: true
  parentRefs:
    - name: public-gateway
      namespace: gateway-system
      sectionName: http
  hostnames:
    - zeroclaw.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
```

## Health checks

The chart uses `/health` for readiness/liveness probes.

## Testing

Run:

```bash
helm lint ./chart/zeroclaw
helm template zeroclaw ./chart/zeroclaw >/dev/null
```

You can also run:

```bash
helm test zeroclaw
```
