# EPUB to Audiobook Converter

A command-line tool and library that converts EPUB ebooks to OGG audiobooks with chapter markers, using local text-to-speech processing with [Kokoro](https://hf.co/hexgrad/Kokoro-82M).

## Features

- Converts EPUB 3.0 files to OGG audiobooks
- Local text-to-speech processing using Kokoro
- Support for 9 languages with multiple voices:
  - 🇺🇸 American English (11F, 9M voices)
  - 🇬🇧 British English (4F, 4M voices)
  - 🇯🇵 Japanese (4F, 1M voices)
  - 🇨🇳 Mandarin Chinese (4F, 4M voices)
  - 🇪🇸 Spanish (1F, 2M voices)
  - 🇫🇷 French (1F voice)
  - 🇮🇳 Hindi (2F, 2M voices)
  - 🇮🇹 Italian (1F, 1M voices)
  - 🇧🇷 Brazilian Portuguese (1F, 2M voices)
- Chapter markers in output files
- Configurable voice selection and speech rate
- Progress reporting with optional quiet mode
- Metadata preservation from EPUB to audio file

## Requirements

- Python 3.10 or higher
- Dependencies listed in `pyproject.toml`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/clayrosenthal/epub2audio.git
cd epub2audio
```

2. Install using mise (recommended):
```bash
mise install
```

Or manually with a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate 
pip install -e .
```

## Usage

### Basic Usage

Convert an EPUB file to an audiobook with default settings:

```bash
epub2audio input.epub
```

The audiobook will be saved as `Book_Title.ogg`, but can be set with `--output`.

### Voice Selection

The tool supports multiple voices across different languages. Here are some notable voices:

#### American English
- `af_bella` (Female, Grade A-) - High quality with extended training
- `af_heart` (Female, Grade A) - Best overall quality
- `af_nicole` (Female, Grade B-) - Good quality with extended training
- `am_fenrir` (Male, Grade C+) - Best male voice option

#### British English
- `bf_emma` (Female, Grade B-) - Best British female voice
- `bm_fable` (Male, Grade C) - Best British male voice

#### Other Languages
- `ff_siwis` (French Female, Grade B-)
- `jf_alpha` (Japanese Female, Grade C+)
- `if_sara` (Italian Female, Grade C)
- `hf_alpha` (Hindi Female, Grade C)

To use a specific voice:
```bash
epub2audio input.epub --voice af_bella
```

### Advanced Options

```bash
epub2audio input.epub \
  --output output.ogg \
  --voice af_bella \
  --speech-rate 1.0 \
  --quiet
```

### Command Line Options

- `input.epub`: Path to input EPUB file
- `--output-dir`, `-o`: Directory for output audiobook files (default: ./audiobooks)
- `--voice`, `-v`: Name of the voice to use (default: af_heart)
- `--speech-rate`, `-r`: Speech rate multiplier (default: 1.0)
- `--quiet`, `-q`: Suppress progress reporting
- `--verbose`, `-v`: Output more verbose logs

## Voice Quality Grades

Voices are graded based on quality and training data:

- **A**: Exceptional quality, extensive training
- **B**: Good quality, suitable for most uses
- **C**: Average quality, may have minor issues
- **D**: Basic quality, may have noticeable issues
- **F**: Limited quality, recommended only if necessary

Modifiers (+/-) indicate slight variations within each grade.

## Development

### Project Structure

```
src/
├── __init__.py
├── epub_processor.py      # EPUB parsing and text extraction
├── audio_converter.py     # TTS conversion using Kokoro
├── audio_handler.py       # OGG creation, chapter markers, metadata
├── epub2audio.py          # Main class, command line interface
├── voices.py              # Voice definitions and management
├── helpers.py             # Utility functions
└── config.py              # Configuration settings
```

### Running Tests

Using mise:
```bash
# Run all tests
mise run test

# Run integration tests
mise run test-integration

# Run with coverage
mise run test-coverage
```

Or manually:
```bash
# Run all tests
pytest

# Run integration tests
pytest --run-integration

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

The project uses:
- Ruff for formatting and linting
- MyPy for type checking
- Pytest for testing

To format and lint code:
```bash
mise run format  # Format code
mise run lint    # Check code
mise run fix     # Auto-fix issues
```

## Error Handling

#### Critical Errors (Exit with error code)
1. Invalid/corrupted EPUB file
2. Invalid voice model selection
3. File system errors (read/write permissions)
4. Insufficient disk space

#### Non-Critical Errors (Warning and continue)
1. Non-text elements in EPUB
2. Unsupported metadata fields
3. Minor formatting issues

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`mise run test`)
5. Format code (`mise run format`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

1. Follow Google Python style guide
2. Add tests for new features
3. Update documentation as needed
4. Keep commits focused and atomic

## License

AGPL-3.0-or-later - See LICENSE file for details

## Acknowledgments

- [Kokoro](https://github.com/hexgrad/kokoro) for text-to-speech processing
  - [Huggingface](https://hf.co/hexgrad/Kokoro-82M) for model weights
- [ebooklib](https://github.com/aerkalov/ebooklib) for EPUB handling
- [mutagen](https://github.com/quodlibet/mutagen) for audio metadata
- Voice training data contributors (see individual voice attributions)
