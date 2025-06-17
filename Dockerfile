# ---------- Builder Stage ---------- #
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder
WORKDIR /app

# install build-deps
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers

# copy and install your Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync

# Download & unpack Node Exporter
ARG NODE_EXPORTER_VERSION=1.9.1
ARG TARGETARCH
RUN wget -qO- \
    https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-${TARGETARCH}.tar.gz \
    | tar xz --strip-components=1 -C /usr/local/bin node_exporter-${NODE_EXPORTER_VERSION}.linux-${TARGETARCH}/node_exporter

# ---------- Production Stage ---------- #
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS production
WORKDIR /app

# bring in virtualenv and Node Exporter
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /usr/local/bin/node_exporter /usr/local/bin/node_exporter

# copy your app
COPY app/ /app/app/
COPY tailwind.config.js package.json package-lock.json ./
COPY src/ /app/src/
COPY settings.toml config.py ./
COPY migrations/ /app/migrations/
COPY start.sh ./
RUN chmod +x start.sh

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080 9100

# launch both Node Exporter and your app
CMD ["./start.sh"]
