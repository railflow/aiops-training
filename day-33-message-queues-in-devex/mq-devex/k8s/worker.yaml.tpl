# One consumer = one tiny Deployment. Rendered by deploy-worker.sh (name, script, args, extra env). Code comes from the ConfigMap mq-devex-code.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${NAME}
  namespace: mq-devex
  labels: {app: ${NAME}, part-of: mq-devex}
spec:
  replicas: 1
  selector:
    matchLabels: {app: ${NAME}}
  template:
    metadata:
      labels: {app: ${NAME}, part-of: mq-devex}
    spec:
      securityContext: {runAsNonRoot: true, runAsUser: 10001, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: worker
          image: python:3.12-slim
          command: ["sh", "-c", "pip install --quiet --no-cache-dir --target /tmp/deps ${PIP} && PYTHONPATH=/tmp/deps:/app exec python /app/${SCRIPT} ${ARGS}"]
          env:
            - {name: NATS_URL, value: "nats://nats.data.svc.cluster.local:4222"}
            - {name: STATE_DIR, value: /state}
            - {name: HOME, value: /tmp}
${EXTRA_ENV}
          securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}}
          resources:
            requests: {cpu: 20m, memory: 64Mi}
            limits: {memory: 192Mi}
          volumeMounts:
            - {name: code, mountPath: /app, readOnly: true}
            - {name: state, mountPath: /state}
            - {name: tmp, mountPath: /tmp}
      volumes:
        - {name: code, configMap: {name: mq-devex-code}}
        - {name: state, emptyDir: {}}
        - {name: tmp, emptyDir: {}}
