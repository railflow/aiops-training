# Example docs site image (the Starlight project in day-28-write-good-docs/docs-as-code/starlight-site/; the course site itself is Next.js): build with Node, serve with unprivileged nginx. Build context is the REPOSITORY ROOT (so nginx.conf is in context):
#   docker build -f day-28-write-good-docs/docs-as-code/deploy/Dockerfile -t docs-site:1.0 .
# Dockerfile.dockerignore (BuildKit) keeps node_modules, dist and .git out of the context.
# Both base images are pinned by tag AND digest (read on 2026-11-05; they WILL be stale: refresh them as in Day 24).
FROM node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS build
WORKDIR /site
COPY day-28-write-good-docs/docs-as-code/starlight-site/package.json day-28-write-good-docs/docs-as-code/starlight-site/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY day-28-write-good-docs/docs-as-code/starlight-site/ .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30.6-alpine-slim@sha256:5d8bb9437d74a600ec5dbf90c035451c724dc33eac8d3a71078f6f8612c345f6
# Replaces the image's config so every writable path is under /tmp and the root filesystem can be read-only.
COPY --chown=101:101 day-28-write-good-docs/docs-as-code/deploy/nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=101:101 /site/dist /usr/share/nginx/html
EXPOSE 8080
USER 101
