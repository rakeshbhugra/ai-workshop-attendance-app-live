# syntax=docker/dockerfile:1
#
# Development image only — the Vite dev server with HMR.
# There is no prod target here on purpose: in production the SPA is a pile of
# static files baked into the backend image by the root Dockerfile, so nothing
# node-shaped ships.
FROM node:24-slim AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
# --host binds 0.0.0.0 so the port mapping reaches the host.
CMD ["npm", "run", "dev", "--", "--host"]
