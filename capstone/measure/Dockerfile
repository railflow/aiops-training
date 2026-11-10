# Measurement image: the course builder image plus cloc and the .NET SDK, with measure.py and ship.py next to build.sh.
# Build from the repository root (aiops-training), after building builder:1 (see day-13-ci-at-scale-build-sh/ci/builder/Dockerfile):
#   docker build -f capstone/measure/Dockerfile -t measure:1 .
# NOT built on the author's machine (no Docker there). The pieces are pinned in versions.env; check the dotnet-install docs if the install step fails.
ARG BUILDER_IMAGE=builder:1
FROM ${BUILDER_IMAGE}

ARG DOTNET_CHANNEL=8.0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends cloc && rm -rf /var/lib/apt/lists/* \
 && curl -sfL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
 && bash /tmp/dotnet-install.sh --channel "${DOTNET_CHANNEL}" --install-dir /usr/share/dotnet && rm /tmp/dotnet-install.sh \
 && ln -s /usr/share/dotnet/dotnet /usr/local/bin/dotnet

ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
COPY capstone/measure/measure.py capstone/measure/ship.py /usr/local/bin/
RUN chmod +x /usr/local/bin/measure.py /usr/local/bin/ship.py
