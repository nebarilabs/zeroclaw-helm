{{/*
Expand the name of the chart.
*/}}
{{- define "zeroclaw.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "zeroclaw.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "zeroclaw.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels.
*/}}
{{- define "zeroclaw.labels" -}}
helm.sh/chart: {{ include "zeroclaw.chart" . }}
{{ include "zeroclaw.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "zeroclaw.selectorLabels" -}}
app.kubernetes.io/name: {{ include "zeroclaw.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use.
*/}}
{{- define "zeroclaw.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "zeroclaw.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Resolve API key secret name.
*/}}
{{- define "zeroclaw.apiKeySecretName" -}}
{{- if .Values.secret.create -}}
{{- printf "%s-secret" (include "zeroclaw.fullname" .) -}}
{{- else if .Values.secret.existingSecret -}}
{{- .Values.secret.existingSecret -}}
{{- else -}}
{{- fail "secret.existingSecret must be set when secret.create=false" -}}
{{- end -}}
{{- end -}}

{{/*
Resolve persistence claim name.
*/}}
{{- define "zeroclaw.pvcName" -}}
{{- if .Values.persistence.existingClaim -}}
{{- .Values.persistence.existingClaim -}}
{{- else -}}
{{- printf "%s-data" (include "zeroclaw.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Resolve channel secrets secret name.
Returns empty string if no channel secrets are configured.
*/}}
{{- define "zeroclaw.channelSecretsName" -}}
{{- if .Values.channelSecrets.existingSecret -}}
{{- .Values.channelSecrets.existingSecret -}}
{{- else if .Values.channelSecrets.create -}}
{{- printf "%s-channel-secrets" (include "zeroclaw.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Check if channel secrets volume should be mounted.
Returns "true" if either create or existingSecret is set.
*/}}
{{- define "zeroclaw.hasChannelSecrets" -}}
{{- if or .Values.channelSecrets.create .Values.channelSecrets.existingSecret -}}
true
{{- end -}}
{{- end -}}

{{/*
Helper to render a TOML string list from a Helm list value.
Usage: {{ include "zeroclaw.tomlStringList" .Values.config.autonomy.allowedCommands }}
Output: ["git", "npm", "cargo"]
*/}}
{{- define "zeroclaw.tomlStringList" -}}
[{{ range $i, $v := . }}{{ if $i }}, {{ end }}{{ $v | quote }}{{ end }}]
{{- end -}}

{{/*
Build list of enabled channel aliases for agent binding.
Output: ["discord.default"] or ["telegram.default", "discord.default"]
*/}}
{{- define "zeroclaw.enabledChannels" -}}
{{- $channels := list -}}
{{- if .Values.config.channels.telegram.enabled -}}
{{- $channels = append $channels "telegram.default" -}}
{{- end -}}
{{- if .Values.config.channels.discord.enabled -}}
{{- $channels = append $channels "discord.default" -}}
{{- end -}}
{{- if .Values.config.channels.slack.enabled -}}
{{- $channels = append $channels "slack.default" -}}
{{- end -}}
{{- if .Values.config.channels.whatsapp.enabled -}}
{{- $channels = append $channels "whatsapp.default" -}}
{{- end -}}
{{- if .Values.config.channels.matrix.enabled -}}
{{- $channels = append $channels "matrix.default" -}}
{{- end -}}
{{- if .Values.config.channels.imessage.enabled -}}
{{- $channels = append $channels "imessage.default" -}}
{{- end -}}
{{- if .Values.config.channels.irc.enabled -}}
{{- $channels = append $channels "irc.default" -}}
{{- end -}}
{{- if .Values.config.channels.lark.enabled -}}
{{- $channels = append $channels "lark.default" -}}
{{- end -}}
{{- if .Values.config.channels.dingtalk.enabled -}}
{{- $channels = append $channels "dingtalk.default" -}}
{{- end -}}
{{ include "zeroclaw.tomlStringList" $channels -}}
{{- end -}}
