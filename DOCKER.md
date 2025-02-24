# Docker Support for epub2audio

This project provides Docker configuration to make it easy to develop and run the application in a consistent environment.

## Quick Start with Docker

### Using Docker Directly

1. Build the Docker image:
```bash
docker build -t epub2audio .
```

2. Run the application on an EPUB file:
```bash
# Assuming your EPUB file is in the current directory
docker run -v $(pwd):/input -v $(pwd)/audiobooks:/output epub2audio /input/my-book.epub --output-dir /output
```

### Using Docker Compose

1. Place your EPUB files in the `./input` directory (or set the `INPUT_DIR` environment variable).

2. Run the application:
```bash
docker-compose run app
```

To process a specific file:
```bash
docker-compose run app /input/my-book.epub --output-dir /output
```

## Development with Docker

### Using Docker Compose

For development work, use the development container:

```bash
docker-compose run --service-ports dev
```

This starts a development environment with all dependencies installed, and mounts your local source code into the container.

### Using VS Code Dev Containers

This project includes a devcontainer configuration for VS Code:

1. Install the "Remote - Containers" extension in VS Code
2. Open the project folder in VS Code
3. When prompted, click "Reopen in Container" or use the command palette to run "Remote-Containers: Reopen in Container"

The devcontainer provides:
- All runtime and development dependencies
- Preconfigured VS Code with Python extensions
- Ruff for linting and formatting
- Git and GitHub CLI
- Direct access to local kokoro-tts fork

## Volumes and File Access

The Docker configurations set up the following volumes:

- `/app` - The project code
- `/input` - Directory to read EPUB files from
- `/output` - Directory to write audiobook files to
- `/app/kokoro-tts` - Mount point for the local kokoro-tts fork (development environment only)

## Environment Variables

- `INPUT_DIR` - Override the default input directory (default: `./input`)
- `OUTPUT_DIR` - Override the default output directory (default: `./audiobooks`) 