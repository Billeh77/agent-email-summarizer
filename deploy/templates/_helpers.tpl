{{- define "email-summarizer.triggerAuthentication" -}}
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: temporal-auth
  namespace: {{ .namespace }}
spec:
  secretTargetRef:
    - parameter: apiKey
      name: temporal-credentials
      key: api-key
{{- end -}}

{{- define "email-summarizer.scaledObject" -}}
{{- $defaults := .defaults | default dict -}}
{{- $worker := .worker -}}
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: {{ $worker.name }}-scaler
  namespace: {{ .namespace }}
spec:
  scaleTargetRef:
    name: {{ $worker.name }}
  minReplicaCount: {{ $worker.minReplicas | default $defaults.minReplicas }}
  maxReplicaCount: {{ $worker.maxReplicas | default $defaults.maxReplicas }}
  cooldownPeriod: {{ $worker.cooldownPeriod | default $defaults.cooldownPeriod }}
  pollingInterval: {{ $worker.pollingInterval | default $defaults.pollingInterval }}
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: {{ $worker.scaleDownStabilization | default $defaults.scaleDownStabilization }}
  triggers:
    - type: temporal
      metadata:
        endpointFromEnv: TEMPORAL_ENDPOINT
        namespaceFromEnv: TEMPORAL_NAMESPACE
        taskQueue: {{ $worker.taskQueue }}
        targetQueueSize: "{{ $worker.targetQueueSize | default $defaults.targetQueueSize }}"
        queueTypes: "{{ $worker.queueTypes | default $defaults.queueTypes }}"
        activationTargetQueueSize: "{{ $worker.activationTargetQueueSize | default $defaults.activationTargetQueueSize }}"
      authenticationRef:
        name: temporal-auth
        kind: TriggerAuthentication
{{- end -}}
