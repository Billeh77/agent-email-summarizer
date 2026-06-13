FROM acrarataaistaging5366d209.azurecr.io/agent-base-image:3.0.5 AS base

# Builder stage to install workspace dependencies
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS uv_tool

FROM base AS builder

WORKDIR /workspace

# Install system dependencies (git for git+ssh deps)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    rust \
    cargo \
    protobuf-dev \
    protoc \
    git \
    curl

ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod +x /install.sh && /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:$PATH"

# Copy workspace root files
COPY --from=root pyproject.toml uv.lock ./

# Copy connector workspace member
COPY --from=root workflows/summarize_email ./workflows/summarize_email
# Uncomment to copy other workflows as needed


# Sync dependencies for the connector workspace (this will install common and its deps)
RUN --mount=type=secret,id=GH_TOKEN \
    export GH_TOKEN=$(cat /run/secrets/GH_TOKEN) && \
    git config --global url."https://x-access-token:${GH_TOKEN}@github.com/Arata-AI".insteadOf "git@github.com:Arata-AI" && \
    git config --global --add url."https://x-access-token:${GH_TOKEN}@github.com/Arata-AI".insteadOf "ssh://git@github.com/Arata-AI" && \
    uv sync --no-dev --frozen --package summarize_email

# Production stage
FROM base AS prod

RUN apk update \
 && apk upgrade \
 && apk add --no-cache libgcc

# Copy the complete .venv with all dependencies from builder
COPY --from=builder --chown=nonroot:nonroot /workspace/.venv /workspace/.venv

# Copy the workspace structure to maintain editable installs
COPY --from=root --chown=nonroot:nonroot workflows/summarize_email /workspace/workflows/summarize_email
# Uncomment to copy other workflows as needed


# Copy and set permissions for entrypoint script
COPY --from=root --chown=nonroot:nonroot logging.yaml /workspace/workflows/summarize_email/logging.yaml
COPY --chown=nonroot:nonroot --chmod=755 workflows/summarize_email/entrypoint.sh /app/entrypoint.sh

WORKDIR /workspace/workflows/summarize_email
ENV VIRTUAL_ENV=/workspace/.venv
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONPATH="/workspace/.venv/lib/python3.12/site-packages:/workspace/workflows/summarize_email/src"

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

USER nonroot

# Run the worker
ENTRYPOINT [ "/app/entrypoint.sh" ]
