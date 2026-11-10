# Rendered by workflows/activities.py (Python string.Template placeholders); never applied by hand with these placeholders.
# Safety properties, each on purpose: non-root, read-only root filesystem, only /work and /tmp writable (emptyDir), no ServiceAccount token, all
# capabilities dropped, hard deadline, no retries (the workflow decides about retries), CPU/memory limits, lowest scheduling priority, and a per-run
# Secret that the worker deletes afterwards. The agent pod has NO ClickHouse, NO Temporal and NO Kubernetes access (see k8s/20-network-policy.yaml).
apiVersion: batch/v1
kind: Job
metadata:
  name: agent-${RUN_ID}
  namespace: capstone
  labels: {app: agent, repo: "${REPO_LABEL}", run: "${RUN_ID}"}
spec:
  backoffLimit: 0
  activeDeadlineSeconds: ${DEADLINE_SECONDS}
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels: {app: agent, repo: "${REPO_LABEL}", run: "${RUN_ID}"}
    spec:
      restartPolicy: Never
      serviceAccountName: capstone-agent
      automountServiceAccountToken: false
      priorityClassName: capstone-agent
      securityContext: {runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: agent
          image: ${AGENT_IMAGE}
          imagePullPolicy: IfNotPresent
          command: ["/opt/agent/run-agent.sh"]
          env:
            - {name: REPO, value: "${REPO}"}
            - {name: FORGEJO_URL, value: "${FORGEJO_URL}"}
            - {name: AGENT_RUN_ID, value: "${RUN_ID}"}
            - {name: TASK, value: "${TASK}"}
            - {name: TARGET_COVERAGE, value: "${TARGET_COVERAGE}"}
            - {name: FOCUS, value: "${FOCUS}"}
            - {name: ISSUE_NUMBER, value: "${ISSUE_NUMBER}"}
            - {name: MAX_BUDGET_USD, value: "${MAX_BUDGET_USD}"}
            - {name: MAX_ISSUES, value: "${MAX_ISSUES}"}
            - {name: PROMPT_VERSION, value: "${PROMPT_VERSION}"}
            - {name: MODEL, value: "${MODEL}"}
            - {name: OPEN_PR, value: "${OPEN_PR}"}
            - {name: HOME, value: /tmp/home}
          envFrom: [{secretRef: {name: "run-${RUN_ID}"}}]     # FORGEJO_TOKEN, ANTHROPIC_API_KEY (or the gateway key): per-run, deleted afterwards
          securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: [ALL]}}
          resources:
            requests: {cpu: 250m, memory: 512Mi}
            limits: {cpu: "1", memory: 1536Mi}
          volumeMounts:
            - {name: work, mountPath: /work}
            - {name: tmp, mountPath: /tmp}
      volumes:
        - {name: work, emptyDir: {sizeLimit: 2Gi}}
        - {name: tmp, emptyDir: {sizeLimit: 1Gi}}
