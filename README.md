# cEDH Analyzer

A modern terminal UI tool for analyzing competitive EDH (cEDH) decklists. Scrapes tournament data from EDHTop16, fetches detailed decklists from Moxfield, and performs statistical analytics to optimize your deck construction.

![cEDH Analyzer TUI](https://img.shields.io/badge/TUI-Textual-blue)
![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green)
![uv](https://img.shields.io/badge/Package%20Manager-uv-purple)

## Features

- 🎨 **Beautiful Terminal UI** - Modern TUI built with Textual
- 📊 **Real-time Progress** - Stacked progress bars for each analysis stage
- 💾 **Resume Support** - Automatically saves progress, resume interrupted analyses
- 📋 **Clipboard Integration** - Results automatically copied for Moxfield import
- 🏷️ **Smart Card Tagging** - Categorizes cards by usage and performance

## Installation

### Prerequisites

- Python 3.11 or higher
- Chrome browser (for web scraping)
- [uv](https://github.com/astral-sh/uv) package manager

### Quick Start

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/cedh-analyzer.git
cd cedh-analyzer

# Install dependencies and run
uv run cedh
```

### Development Setup

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/cedh_analyzer --cov-report=html
```

## Usage

1. **Launch the app:**
   ```bash
   uv run cedh
   ```

2. **Enter a commander URL** from EDHTop16 (default: Kinnan, Bonder Prodigy)

3. **Watch the analysis progress** through 5 stages:
   - EDH16 Scrape - Fetches tournament data
   - Moxfield Scrape - Downloads decklists
   - Preprocess - Normalizes card data
   - Basic Analytics - Analyzes usage patterns
   - Win Rate Analytics - Calculates performance metrics

4. **Results are copied to your clipboard** - paste directly into Moxfield

### Resuming Analysis

If the analysis is interrupted, the app will automatically detect the saved progress on next launch and offer to resume or start fresh.

## Card Tags

Cards are tagged based on their characteristics:

### Core Cards (by usage rate)
| Tag | Meaning |
|-----|---------|
| `#1_core` | Present in 99%+ of decks |
| `#2_essential` | Present in 95-99% of decks |
| `#3_common` | Present in 90-94% of decks |

### Performance Tags
| Tag | Meaning |
|-----|---------|
| `#4_high_spice` | Top performer, <3 appearances (rare tech) |
| `#5_medium_spice` | Top performer, 3-10 appearances |
| `#6_low_spice` | Top performer, >10 appearances |
| `#7_potential_traps` | High appearance, low performance |
| `#8_bad_cards` | Bottom 20% performers |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` / `Ctrl+C` | Quit |
| `Enter` | Confirm / Start |
| `Escape` | Cancel / Close modal |

## Project Structure

```
cedh-analyzer/
├── pyproject.toml          # Project configuration (uv)
├── src/
│   └── cedh_analyzer/
│       ├── app.py          # Main Textual application
│       ├── config.py       # Configuration constants
│       ├── state.py        # State management
│       ├── stages/         # Analysis pipeline stages
│       │   ├── edh16_scrape.py
│       │   ├── moxfield_scrape.py
│       │   ├── preprocess.py
│       │   ├── basic_analytics.py
│       │   └── winrate_analytics.py
│       └── widgets/        # Custom TUI widgets
│           └── progress_stack.py
└── tests/                  # Test suite
```

## Tech Stack

- **UI Framework**: [Textual](https://textual.textualize.io/) - Modern TUI framework
- **Package Manager**: [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- **Web Scraping**: Selenium with stealth mode, BeautifulSoup
- **Data Analysis**: Pandas, NumPy
- **Clipboard**: pyperclip

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
