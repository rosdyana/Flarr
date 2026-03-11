# Contributing to Bootable USB Creator

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## 🚨 Important Safety Note

This tool performs **raw disk operations**. Any bug or error could result in **data loss** for users. Please be extra careful when modifying:

- Disk detection logic
- Device filtering (ensuring only USB/removable devices are shown)
- Confirmation flows
- Write operations

## Development Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Python 3.8 or higher

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/bootable-usb-creator.git
cd bootable-usb-creator

# Create virtual environment and install dependencies
uv sync --extra dev

# Activate the environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

## Running the Application

```bash
# Simple version (no dependencies)
python bootable_usb_simple.py

# Full TUI version
python bootable_usb.py

# Or use the installed scripts
bootable-usb
bootable-usb-tui
```

## Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check code
ruff check .

# Format code
ruff format .
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=.
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature (`git checkout -b feature/amazing-feature`)
3. **Make your changes** with clear, descriptive commits
4. **Test thoroughly** - especially disk detection and safety features
5. **Run linters** (`ruff check .` and `ruff format .`)
6. **Update documentation** if needed
7. **Submit a Pull Request** with a clear description

## What We're Looking For

### 🐛 Bug Fixes
- Disk detection issues
- Platform-specific problems
- Safety feature improvements

### ✨ Features
- Better progress indicators
- ISO verification
- Boot verification
- Additional safety checks

### 📝 Documentation
- Usage examples
- Troubleshooting guides
- Translation help

## Safety Guidelines

When contributing code that handles disk operations:

1. **Never assume** a device is safe to write to
2. **Always verify** device properties (removable, USB, etc.)
3. **Require explicit user confirmation** for destructive operations
4. **Test on all platforms** you have access to
5. **Consider edge cases** (empty disks, read-only devices, etc.)

## Code of Conduct

- Be respectful and constructive
- Focus on user safety
- Welcome newcomers
- Give credit where due

## Questions?

- Open an [issue](https://github.com/yourusername/bootable-usb-creator/issues)
- Start a [discussion](https://github.com/yourusername/bootable-usb-creator/discussions)

Thank you for contributing! 🎉
