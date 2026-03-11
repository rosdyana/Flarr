# 🔌 Flarr - Bootable USB Creator

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A **safe**, **user-friendly** tool for creating bootable USB drives from ISO files. Built with multiple safety layers to prevent accidental data loss.

> ⚠️ **Warning**: This tool writes raw data to disks. While designed with safety in mind, always double-check your selections and ensure you have backups of important data.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🛡️ **Safety First** | USB-only detection, double confirmation, device verification |
| 🖥️ **Two Interfaces** | Full TUI (rich interface) and Simple CLI (no dependencies) |
| 🧪 **Dry-Run Mode** | Test the process without actually writing |
| 📊 **Progress Tracking** | Real-time progress bar during write operations |
| 🔄 **Auto-Unmount** | Automatically unmounts disk before writing |
| 🌐 **Cross-Platform** | Linux, macOS, and Windows support |
| 📦 **Zero Dependencies** | Simple version works with Python stdlib only |

## 🚀 Quick Start

### Using `uv` (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/rosdyana/bootable-usb-creator.git
cd bootable-usb-creator

# Setup environment
uv sync

# Run the simple version
uv run python bootable_usb_simple.py

# Or run the full TUI version
uv sync --extra tui
uv run python bootable_usb.py
```

### Traditional pip

```bash
# Clone the repository
git clone https://github.com/rosdyana/bootable-usb-creator.git
cd bootable-usb-creator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .

# For TUI version
pip install -e ".[tui]"

# Run
python bootable_usb_simple.py
# or
python bootable_usb.py
```

## 📋 Requirements

- Python 3.8 or higher
- **Root/Administrator privileges** (for raw disk access)
- USB drive (4GB minimum, 8GB+ recommended)
- ISO file to write

## 🖥️ Usage

### Simple CLI Version

```bash
# Linux/macOS
sudo uv run python bootable_usb_simple.py

# Windows (Administrator PowerShell)
uv run python bootable_usb_simple.py
```

The simple version provides:
1. ⚠️ Warning acknowledgment
2. 📁 ISO file path input
3. 🔌 USB device selection from detected devices
4. ✏️ Type device name to confirm
5. 📝 Write with progress indication

### Full TUI Version

```bash
# Linux/macOS
sudo uv run python bootable_usb.py

# Windows (Administrator PowerShell)
uv run python bootable_usb.py
```

The TUI version provides:
- Interactive file browser
- Rich visual interface
- Real-time progress bar
- Dry-run mode checkbox

### Using Installed Scripts

After `pip install -e .` or `uv sync`:

```bash
bootable-usb        # Simple version
bootable-usb-tui    # TUI version
```

## 🛡️ Safety Features

### 1. USB-Only Detection
Only removable USB devices are displayed. Internal drives are filtered out based on:
- Device transport type (USB)
- Removable media flag
- Mount points and partition info

### 2. Double Confirmation
- First: Acknowledge warning screen
- Second: Type the exact device name to proceed

### 3. Device Information Display
Before writing, the following is shown:
```
Device: /dev/sdb
Model:  SanDisk Ultra USB 3.0
Size:   14.9 GB
```

### 4. Dry-Run Mode
Test the entire process without writing any data.

### 5. Auto-Unmount
The disk is automatically unmounted before writing to prevent conflicts.

## 📸 Screenshots

### Simple Version
```
============================================================
     BOOTABLE USB CREATOR - Simple Version
============================================================

⚠️  WARNING - READ CAREFULLY ⚠️
------------------------------------------------------------

This tool writes raw data to USB devices.

INCORRECT USE CAN DESTROY DATA ON THE WRONG DISK!
...
```

### TUI Version
```
┌─────────────────────────────────────────────────────────┐
│  Create Bootable USB                            2:30 PM │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1: Select ISO File                                │
│  [Path to ISO...                    ] [Browse]          │
│  ✅ ISO selected: ubuntu-22.04.iso (4.5 GB)             │
│                                                         │
│  Step 2: Select USB Device                              │
│  [🔄 Refresh]                                           │
│  ┌──────────────────────────────────────────────┐       │
│  │ Select USB device...                         │       │
│  └──────────────────────────────────────────────┘       │
│  ✅ Device: /dev/sdb                                    │
│     Model: SanDisk Ultra USB 3.0                        │
│     Size: 14.9 GB                                       │
└─────────────────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### "No USB devices found"

**Cause**: Missing privileges or no USB inserted

**Solution**:
```bash
# Linux/macOS - Run with sudo
sudo bootable-usb

# Windows - Run PowerShell as Administrator
```

### "Permission denied"

**Cause**: Raw disk access requires elevated privileges

**Solution**: Run as root (Linux/macOS) or Administrator (Windows)

### Write fails on Windows

**Cause**: Windows raw disk access is complex and may require additional drivers

**Solution**: Use the Linux version via WSL, or use Windows-specific tools like Rufus

### USB not showing correct size

**Cause**: Disk may have multiple partitions or be in an inconsistent state

**Solution**:
```bash
# Linux - Check disk with fdisk
sudo fdisk -l /dev/sdX

# macOS - Check with diskutil
diskutil list

# Windows - Check with diskpart
```

## 🏗️ Project Structure

```
bootable-usb-creator/
├── bootable_usb.py           # Full TUI version (textual)
├── bootable_usb_simple.py    # Simple CLI version (stdlib only)
├── pyproject.toml            # Project configuration
├── uv.lock                   # Dependency lock file
├── README.md                 # This file
├── LICENSE                   # MIT License
├── CONTRIBUTING.md           # Contribution guidelines
└── .python-version           # Python version specification
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Code style guidelines
- Safety considerations
- Pull request process

### Quick Development Setup

```bash
# Clone
git clone https://github.com/rosdyana/bootable-usb-creator.git
cd bootable-usb-creator

# Setup with uv
uv sync --extra dev

# Activate environment
source .venv/bin/activate

# Make changes...

# Run checks
ruff check .
ruff format .
pytest
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [Rufus](https://rufus.ie/) (Windows) and [Etcher](https://www.balena.io/etcher/)
- Built with [Textual](https://textual.textualize.io/) for the TUI version
- Powered by [uv](https://github.com/astral-sh/uv) for fast Python package management

## 🔗 Related Projects

- [Rufus](https://rufus.ie/) - Windows bootable USB creator
- [balenaEtcher](https://www.balena.io/etcher/) - Cross-platform GUI tool
- [Ventoy](https://www.ventoy.net/) - Multi-boot USB solution
- [WoeUSB](https://github.com/WoeUSB/WoeUSB) - Windows ISO to USB for Linux

## ⚠️ Disclaimer

This software is provided "as is", without warranty of any kind. The authors are not responsible for any data loss or damage caused by the use of this software. Always verify the target device before writing and maintain backups of important data.

---

Made with ❤️ and safety in mind.
