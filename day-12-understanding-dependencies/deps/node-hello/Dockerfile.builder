# A "builder" image with the dependencies baked in, for CI jobs that run tests without installing.
# Rebuild it only when package.json or package-lock.json changes. Tag it with the lockfile hash.
FROM node:22-bookworm
WORKDIR /opt/deps
COPY package.json package-lock.json ./
RUN npm ci
ENV NODE_PATH=/opt/deps/node_modules
