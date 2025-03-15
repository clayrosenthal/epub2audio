FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set environment variables
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies required for audio processing
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    git

WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY pyproject.toml ./

# Create and activate virtual environment, then install dependencies
RUN python3.12 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-deps -e . && \
    uv pip compile pyproject.toml | uv pip install --no-deps -r -

# Copy the rest of the application
COPY . .

# Set the entrypoint to the main Python script
ENTRYPOINT ["python", "-m", "src.cli"] 