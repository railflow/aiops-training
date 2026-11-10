# Worker image (kubectl included: the KubernetesJobRunner shells out to it). Build from the repository root (aiops-training):
#   docker build -f capstone/workflows/Dockerfile -t capstone-worker:1 .      then:  kind load docker-image capstone-worker:1 --name ai-ops-training
# NOT built on the author's machine (no Docker).
FROM python:3.12-slim
ARG KUBECTL_VERSION=v1.32.0
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/* \
 && curl -sfLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" && chmod +x /usr/local/bin/kubectl
WORKDIR /app
COPY capstone/workflows/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY capstone/workflows/*.py /app/
# worker.py adds <its dir>/../measure to sys.path, which is /measure in this layout
COPY capstone/measure/ship.py /measure/ship.py
COPY capstone/agent/job-agent.yaml.tpl capstone/agent/job-eval.yaml.tpl /app/templates/
ENV TEMPLATES_DIR=/app/templates
USER 10001
CMD ["python", "worker.py"]
