FROM node:22-bookworm-slim
WORKDIR /app
# Dependency manifests first: this layer is rebuilt only when they change.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
# Source code last: edits here do not invalidate the install layer.
COPY index.js ./
CMD ["node", "index.js"]
