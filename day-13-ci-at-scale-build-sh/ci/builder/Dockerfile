# The "baked" builder image: every tool the central build.sh may call, installed once.
# Build from the repository root (aiops-training):   docker build -f day-13-ci-at-scale-build-sh/ci/builder/Dockerfile -t builder:1 .
FROM eclipse-temurin:21-jdk

ARG TARGETARCH
ARG KUBECTL_VERSION=v1.32.0
ARG TRIVY_VERSION=v0.58.1
ARG BUILDKIT_VERSION=v0.18.2
ARG OPA_VERSION=v1.0.0
ARG GITLEAKS_VERSION=8.21.2

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git curl ca-certificates jq maven python3 python3-venv python3-pip nodejs npm golang-go \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
      | sh -s -- -b /usr/local/bin "${TRIVY_VERSION}" \
 && curl -sfLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
 && chmod +x /usr/local/bin/kubectl \
 && curl -sfL "https://github.com/moby/buildkit/releases/download/${BUILDKIT_VERSION}/buildkit-${BUILDKIT_VERSION}.linux-${TARGETARCH}.tar.gz" \
      | tar -xz -C /usr/local bin/buildctl \
 && case "${TARGETARCH}" in amd64) GL=x64 ;; *) GL="${TARGETARCH}" ;; esac \
 && curl -sfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${GL}.tar.gz" \
      | tar -xz -C /usr/local/bin gitleaks \
 && curl -sfLo /usr/local/bin/opa "https://openpolicyagent.org/downloads/${OPA_VERSION}/opa_linux_${TARGETARCH}_static" \
 && chmod +x /usr/local/bin/opa

COPY tools/build.sh tools/check-docs-touched.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/build.sh /usr/local/bin/check-docs-touched.sh \
 && gitleaks version && trivy --version | head -1 && kubectl version --client | head -1 && buildctl --version && opa version | head -1

WORKDIR /workspace
