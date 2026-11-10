# The trusted evaluation Job: same hardening, different image and network policy (app: evaluate), and it holds the ClickHouse password.
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-${RUN_ID}
  namespace: capstone
  labels: {app: evaluate, repo: "${REPO_LABEL}", run: "${RUN_ID}"}
spec:
  backoffLimit: 0
  activeDeadlineSeconds: ${DEADLINE_SECONDS}
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels: {app: evaluate, repo: "${REPO_LABEL}", run: "${RUN_ID}"}
    spec:
      restartPolicy: Never
      serviceAccountName: capstone-agent
      automountServiceAccountToken: false
      priorityClassName: capstone-agent
      securityContext: {runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: evaluate
          image: ${EVAL_IMAGE}
          imagePullPolicy: IfNotPresent
          command: ["/opt/agent/evaluate.sh"]
          env:
            - {name: REPO, value: "${REPO}"}
            - {name: FORGEJO_URL, value: "${FORGEJO_URL}"}
            - {name: BRANCH, value: "${BRANCH}"}
            - {name: AGENT_RUN_ID, value: "${AGENT_RUN_ID}"}
            - {name: RUN_ID, value: "${RUN_ID}"}
            - {name: ITERATION, value: "${ITERATION}"}
            - {name: PREV_COVERAGE, value: "${PREV_COVERAGE}"}
            - {name: ALLOW_SRC_CHANGES, value: "${ALLOW_SRC_CHANGES}"}
            - {name: CLICKHOUSE_URL, value: "${CLICKHOUSE_URL}"}
            - {name: CLICKHOUSE_USER, value: "${CLICKHOUSE_USER}"}
            - {name: HOME, value: /tmp/home}
          envFrom: [{secretRef: {name: "run-${RUN_ID}"}}]     # FORGEJO_TOKEN (read), CLICKHOUSE_PASSWORD
          securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: [ALL]}}
          resources:
            requests: {cpu: 250m, memory: 512Mi}
            limits: {cpu: "1", memory: 2Gi}
          volumeMounts:
            - {name: work, mountPath: /work}
            - {name: tmp, mountPath: /tmp}
      volumes:
        - {name: work, emptyDir: {sizeLimit: 3Gi}}
        - {name: tmp, emptyDir: {sizeLimit: 2Gi}}
