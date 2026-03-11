#!/usr/bin/env python3
"""
Bootable USB Creator TUI
A safe, user-friendly tool for creating bootable USB drives.

WARNING: This tool writes raw data to disks. Use with extreme caution.
"""

import os
import platform
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
)
from textual.worker import Worker, get_current_worker


@dataclass(frozen=True)
class DiskInfo:
    """Represents a disk device."""

    device: str
    name: str
    size: str
    size_bytes: int
    model: str
    is_removable: bool
    is_usb: bool

    def __str__(self):
        return f"{self.device} ({self.model}, {self.size})"


class DiskUtils:
    """Utility functions for disk operations."""

    @staticmethod
    def get_disks() -> List[DiskInfo]:
        """Get list of removable USB disks."""
        system = platform.system()

        if system == "Linux":
            return DiskUtils._get_linux_disks()
        elif system == "Darwin":
            return DiskUtils._get_macos_disks()
        elif system == "Windows":
            return DiskUtils._get_windows_disks()
        else:
            raise OSError(f"Unsupported platform: {system}")

    @staticmethod
    def _get_linux_disks() -> List[DiskInfo]:
        """Get USB disks on Linux using lsblk."""
        disks = []
        try:
            # Get all block devices with details
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,MODEL,TYPE,RM,TRAN,SERIAL"],
                capture_output=True,
                text=True,
                check=True,
            )
            import json

            data = json.loads(result.stdout)

            for device in data.get("blockdevices", []):
                if device.get("type") != "disk":
                    continue

                device_name = device.get("name", "")
                device_path = f"/dev/{device_name}"

                # Check if it's removable (RM=1) and USB
                is_removable = device.get("rm") == "1" or device.get("rm") == True
                is_usb = device.get("tran") == "usb"

                # Also check /sys/class/block for removable attribute
                removable_file = f"/sys/class/block/{device_name}/removable"
                if os.path.exists(removable_file):
                    try:
                        with open(removable_file, "r") as f:
                            is_removable = f.read().strip() == "1"
                    except:
                        pass

                # Only include removable USB devices
                if not (is_removable or is_usb):
                    continue

                # Skip loop devices, ram disks, etc
                if device_name.startswith(("loop", "ram", "dm-")):
                    continue

                size_str = device.get("size", "Unknown")
                model = device.get("model", "Unknown").strip()

                # Parse size for sorting
                size_bytes = DiskUtils._parse_size(size_str)

                disks.append(
                    DiskInfo(
                        device=device_path,
                        name=device_name,
                        size=size_str,
                        size_bytes=size_bytes,
                        model=model if model else "Unknown USB Device",
                        is_removable=is_removable,
                        is_usb=is_usb,
                    )
                )

        except Exception as e:
            print(f"Error getting disks: {e}")

        return sorted(disks, key=lambda d: d.device)

    @staticmethod
    def _get_macos_disks() -> List[DiskInfo]:
        """Get USB disks on macOS using diskutil."""
        disks = []
        try:
            # Get list of all disks
            result = subprocess.run(
                ["diskutil", "list", "-plist"], capture_output=True, text=True, check=True
            )

            # Parse plist output
            import plistlib

            plist = plistlib.loads(result.stdout.encode())

            for disk in plist.get("AllDisksAndPartitions", []):
                device_id = disk.get("DeviceIdentifier", "")
                device_path = f"/dev/{device_id}"

                # Get disk info
                info_result = subprocess.run(
                    ["diskutil", "info", "-plist", device_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                info = plistlib.loads(info_result.stdout.encode())

                # Check if removable and USB
                is_removable = info.get("RemovableMedia", False)
                is_internal = info.get("Internal", True)
                protocol = info.get("BusProtocol", "").lower()
                is_usb = "usb" in protocol

                # Only include external removable USB devices
                if not (is_removable and not is_internal and is_usb):
                    continue

                size_bytes = info.get("TotalSize", 0)
                size_str = DiskUtils._format_size(size_bytes)
                model = info.get("MediaName", "Unknown USB Device")

                disks.append(
                    DiskInfo(
                        device=device_path,
                        name=device_id,
                        size=size_str,
                        size_bytes=size_bytes,
                        model=model,
                        is_removable=is_removable,
                        is_usb=is_usb,
                    )
                )

        except Exception as e:
            print(f"Error getting disks: {e}")

        return sorted(disks, key=lambda d: d.device)

    @staticmethod
    def _get_windows_disks() -> List[DiskInfo]:
        """Get USB disks on Windows using PowerShell."""
        disks = []
        try:
            # Use PowerShell to get disk info
            ps_command = """
            Get-Disk | Where-Object { $_.BusType -eq 'USB' -and $_.IsReadOnly -eq $false } |
            Select-Object DeviceID, FriendlyName, Size, MediaType, BusType | ConvertTo-Json
            """
            result = subprocess.run(
                ["powershell", "-Command", ps_command], capture_output=True, text=True, check=True
            )

            import json

            data = json.loads(result.stdout)

            # Handle single disk (not in array)
            if isinstance(data, dict):
                data = [data]

            for disk in data:
                device_id = disk.get("DeviceID", 0)
                device_path = f"\\\\.\\PhysicalDrive{device_id}"
                size_bytes = disk.get("Size", 0)
                size_str = DiskUtils._format_size(size_bytes)
                model = disk.get("FriendlyName", "Unknown USB Device")

                disks.append(
                    DiskInfo(
                        device=device_path,
                        name=f"PhysicalDrive{device_id}",
                        size=size_str,
                        size_bytes=size_bytes,
                        model=model,
                        is_removable=True,
                        is_usb=True,
                    )
                )

        except Exception as e:
            print(f"Error getting disks: {e}")

        return sorted(disks, key=lambda d: d.device)

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse size string to bytes."""
        size_str = size_str.upper().strip()
        multipliers = {
            "B": 1,
            "K": 1024,
            "KB": 1024,
            "M": 1024**2,
            "MB": 1024**2,
            "G": 1024**3,
            "GB": 1024**3,
            "T": 1024**4,
            "TB": 1024**4,
        }

        match = re.match(r"([\d.]+)\s*([A-Z]*)", size_str)
        if match:
            num = float(match.group(1))
            unit = match.group(2) or "B"
            return int(num * multipliers.get(unit, 1))
        return 0

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def unmount_disk(device: str) -> bool:
        """Unmount/eject a disk before writing."""
        system = platform.system()

        try:
            if system == "Linux":
                # Unmount all partitions of this device
                result = subprocess.run(
                    ["lsblk", "-J", "-o", "NAME,MOUNTPOINT", device], capture_output=True, text=True
                )
                import json

                data = json.loads(result.stdout)

                for dev in data.get("blockdevices", []):
                    for child in dev.get("children", []):
                        mountpoint = child.get("mountpoint")
                        if mountpoint:
                            subprocess.run(["umount", mountpoint], check=False)

            elif system == "Darwin":
                # Unmount disk on macOS
                subprocess.run(["diskutil", "unmountDisk", device], check=False)

            elif system == "Windows":
                # Windows doesn't need explicit unmount for raw write
                pass

            return True
        except Exception as e:
            print(f"Warning: Could not unmount disk: {e}")
            return False

    @staticmethod
    def write_iso(
        device: str, iso_path: str, progress_callback: Callable[[int], None], dry_run: bool = False
    ) -> tuple[bool, str]:
        """Write ISO to disk. Returns (success, message)."""
        system = platform.system()

        try:
            # Get ISO size for progress calculation
            iso_size = os.path.getsize(iso_path)

            if dry_run:
                # Simulate writing
                for i in range(101):
                    progress_callback(i)
                    time.sleep(0.05)
                return True, "Dry run completed successfully"

            if system in ("Linux", "Darwin"):
                # Use dd for Unix-like systems
                # Use 4MB block size for better performance
                cmd = [
                    "dd",
                    f"if={iso_path}",
                    f"of={device}",
                    "bs=4M",
                    "status=progress",
                    "conv=fsync",
                ]

                # For macOS, use lowercase 'm' for bs
                if system == "Darwin":
                    cmd[3] = "bs=4m"

                # Run dd with progress parsing
                process = subprocess.Popen(
                    cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
                )

                # Parse progress from stderr
                while True:
                    line = process.stderr.readline()
                    if not line and process.poll() is not None:
                        break

                    # Try to extract bytes written from dd output
                    match = re.search(r"(\d+)\s*bytes", line)
                    if match:
                        bytes_written = int(match.group(1))
                        progress = min(100, int(bytes_written * 100 / iso_size))
                        progress_callback(progress)

                return_code = process.wait()

                if return_code == 0:
                    progress_callback(100)
                    return True, "ISO written successfully"
                else:
                    return False, f"dd failed with return code {return_code}"

            elif system == "Windows":
                # Use PowerShell for Windows
                # This is a simplified version - Windows raw disk access is complex
                ps_cmd = f"""
                $iso = Get-Item '{iso_path}'
                $device = '{device}'
                $buffer = New-Object byte[] (4MB)
                $stream = [System.IO.File]::OpenRead($iso.FullName)
                $writer = [System.IO.File]::OpenWrite($device)

                $total = $iso.Length
                $written = 0
                $lastProgress = 0

                while ($read = $stream.Read($buffer, 0, $buffer.Length)) {{
                    $writer.Write($buffer, 0, $read)
                    $written += $read
                    $progress = [math]::Floor(($written / $total) * 100)
                    if ($progress -ne $lastProgress) {{
                        Write-Host "PROGRESS: $progress"
                        $lastProgress = $progress
                    }}
                }}

                $stream.Close()
                $writer.Close()
                """

                process = subprocess.Popen(
                    ["powershell", "-Command", ps_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break

                    match = re.search(r"PROGRESS:\s*(\d+)", line)
                    if match:
                        progress_callback(int(match.group(1)))

                return_code = process.wait()

                if return_code == 0:
                    progress_callback(100)
                    return True, "ISO written successfully"
                else:
                    return False, f"Write failed with return code {return_code}"

        except Exception as e:
            return False, f"Error writing ISO: {str(e)}"


class WarningScreen(Screen):
    """Initial warning screen."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="centered"):
            yield Static("⚠️  WARNING  ⚠️", classes="warning-title")
            yield Static(
                "This tool writes raw data to USB devices.\n\n"
                "Incorrect use can DESTROY DATA on the wrong disk.\n\n"
                "- Only USB devices will be shown\n"
                "- You must confirm the disk selection TWICE\n"
                "- Ensure you have backups of important data\n"
                "- Do not remove the USB drive during writing",
                classes="warning-text",
            )

            with Horizontal(classes="button-row"):
                yield Button("I Understand, Continue", variant="primary", id="continue")
                yield Button("Exit", variant="error", id="exit")
        yield Footer()

    @on(Button.Pressed, "#continue")
    def start_app(self) -> None:
        self.app.push_screen("select")

    @on(Button.Pressed, "#exit")
    def exit_app(self) -> None:
        self.app.exit()


class SelectionScreen(Screen):
    """Screen for selecting ISO and USB device."""

    disks: List[DiskInfo] = []
    selected_iso: reactive[Optional[str]] = reactive(None)
    selected_disk: reactive[Optional[DiskInfo]] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(classes="main-container"):
            yield Static("BOOTABLE USB CREATOR", classes="title")

            # ISO Selection
            with Vertical(classes="section"):
                yield Static("STEP 1: SELECT ISO FILE", classes="section-title")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="Path to ISO file...", id="iso_path")
                    yield Button("Browse", id="browse", variant="primary")
                yield Static("No ISO selected", id="iso_info", classes="info-panel")

            # USB Selection
            with Vertical(classes="section"):
                yield Static("STEP 2: SELECT USB DEVICE", classes="section-title")
                with Horizontal(classes="input-row"):
                    yield Select(
                        options=[],
                        id="disk_select",
                        prompt="Select target USB drive...",
                    )
                    yield Button("🔄 Refresh", id="refresh", variant="primary")
                yield Static(
                    "Waiting for device selection...", id="disk_info", classes="info-panel"
                )

            # Options
            with Vertical(classes="section"):
                yield Static("OPTIONS", classes="section-title")
                with Horizontal(classes="input-row"):
                    yield Checkbox("Dry Run (Simulation Only)", id="dry_run")
                    yield Static(
                        "Safe mode: No changes will be made to the disk",
                        id="option_info",
                        classes="option-hint",
                    )

            # Action buttons
            with Horizontal(classes="button-row"):
                yield Button("Proceed to Flash", variant="success", id="proceed", disabled=True)
                yield Button("Exit", variant="error", id="exit")

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_disks()

    def refresh_disks(self) -> None:
        """Refresh the list of USB disks."""
        self.disks = DiskUtils.get_disks()

        select = self.query_one("#disk_select", Select)
        options = [(str(disk), disk) for disk in self.disks]
        select.set_options(options)

        # Reset selection on refresh to avoid stale references
        self.selected_disk = None
        # Handle different Textual versions for NULL/BLANK
        try:
            select.value = Select.NULL
        except AttributeError:
            select.value = getattr(Select, "BLANK", None)

        if not self.disks:
            self.query_one("#disk_info", Static).update(
                "❌ No USB devices found. Insert a USB drive and click Refresh."
            )
        else:
            self.query_one("#disk_info", Static).update("")

    @on(Button.Pressed, "#browse")
    def browse_files(self) -> None:
        self.app.push_screen(FilePickerScreen())

    @on(Button.Pressed, "#refresh")
    def handle_refresh(self) -> None:
        self.refresh_disks()

    @on(Button.Pressed, "#proceed")
    def handle_proceed(self) -> None:
        if self.selected_iso and self.selected_disk:
            dry_run = self.query_one("#dry_run", Checkbox).value
            self.app.push_screen(ConfirmScreen(self.selected_iso, self.selected_disk, dry_run))

    @on(Button.Pressed, "#exit")
    def handle_exit(self) -> None:
        self.app.exit()

    @on(Input.Changed, "#iso_path")
    def iso_path_changed(self, event: Input.Changed) -> None:
        path = event.value.strip()
        if not path:
            self.selected_iso = None
            self.query_one("#iso_info", Static).update("No ISO selected")
        elif os.path.isfile(path) and path.lower().endswith(".iso"):
            self.selected_iso = path
            size = os.path.getsize(path)
            self.query_one("#iso_info", Static).update(
                f"✅ [bold]ISO Selected:[/bold] {os.path.basename(path)}\n"
                f"   [bold]Size:[/bold] {DiskUtils._format_size(size)}\n"
                f"   [bold]Path:[/bold] {path}"
            )
        else:
            self.selected_iso = None
            self.query_one("#iso_info", Static).update("❌ Please enter a valid ISO file path")
        self.update_proceed_button()

    @on(Select.Changed, "#disk_select")
    def disk_selection_changed(self, event: Select.Changed) -> None:
        # Handle different Textual versions for NULL/BLANK
        is_null = False
        try:
            is_null = event.value == Select.NULL
        except AttributeError:
            is_null = event.value == getattr(Select, "BLANK", None)

        self.selected_disk = event.value if not is_null else None
        if self.selected_disk:
            disk = self.selected_disk
            self.query_one("#disk_info", Static).update(
                f"✅ [bold]Selected Device:[/bold] {disk.device}\n"
                f"   [bold]Model:[/bold] {disk.model}\n"
                f"   [bold]Size:[/bold] {disk.size}\n"
                f"   [bold]Type:[/bold] {'USB Removable' if disk.is_usb else 'External'}"
            )
        else:
            self.query_one("#disk_info", Static).update("")
        self.update_proceed_button()

    @on(Checkbox.Changed, "#dry_run")
    def dry_run_changed(self, event: Checkbox.Changed) -> None:
        info = self.query_one("#option_info", Static)
        if event.value:
            info.update("✅ Safe mode enabled: Simulation only")
        else:
            info.update("⚠️ [bold]Warning:[/bold] Data will be written to the disk")

    def update_proceed_button(self) -> None:
        """Enable/disable proceed button based on selections."""
        can_proceed = self.selected_iso is not None and self.selected_disk is not None
        self.query_one("#proceed", Button).disabled = not can_proceed


class ISOFileTree(DirectoryTree):
    """A DirectoryTree that only shows ISO files and directories."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [path for path in paths if path.is_dir() or path.suffix.lower() == ".iso"]


class FilePickerScreen(Screen):
    """File picker screen using DirectoryTree."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="main-container"):
            yield Static("SELECT ISO FILE", classes="title")
            yield Label("Navigate to your ISO file and press Enter or click 'Select':")
            yield ISOFileTree(Path.home(), id="file_tree")

            with Horizontal(classes="button-row"):
                yield Button("Select", id="select", variant="primary")
                yield Button("Cancel", id="cancel", variant="error")

        yield Footer()

    @on(DirectoryTree.FileSelected)
    def handle_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self._select_file(str(event.path))

    def _select_file(self, file_path: str) -> None:
        if file_path.lower().endswith(".iso"):
            # Set the ISO path in parent screen
            parent = self.app.screen_stack[-2]
            parent.query_one("#iso_path", Input).value = file_path
            self.app.pop_screen()

    @on(Button.Pressed, "#select")
    def select_highlighted_file(self) -> None:
        tree = self.query_one("#file_tree", ISOFileTree)
        if tree.cursor_node and tree.cursor_node.data:
            path = tree.cursor_node.data
            if isinstance(path, (str, Path)):
                self._select_file(str(path))

    @on(Button.Pressed, "#cancel")
    def cancel_picker(self) -> None:
        self.app.pop_screen()


class ConfirmScreen(Screen):
    """Final confirmation screen with safety check."""

    def __init__(self, iso_path: str, disk: DiskInfo, dry_run: bool = False):
        super().__init__()
        self.iso_path = iso_path
        self.disk = disk
        self.dry_run = dry_run
        self.confirmed = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="main-container"):
            yield Static("⚠️ FINAL CONFIRMATION ⚠️", classes="danger-title")

            with Container(classes="confirm-box"):
                yield Static("You are about to write:", classes="confirm-label")
                yield Static(f"💿 ISO: {self.iso_path}", classes="confirm-value")
                yield Static(f"   Size: {DiskUtils._format_size(os.path.getsize(self.iso_path))}")

                yield Static("")
                yield Static("To USB device:", classes="confirm-label")
                yield Static(f"🔌 Device: {self.disk.device}", classes="confirm-value danger")
                yield Static(f"   Model: {self.disk.model}")
                yield Static(f"   Size: {self.disk.size}")

                if self.dry_run:
                    yield Static("")
                    yield Static("[DRY RUN MODE - No actual writing will occur]", classes="info")

            yield Static("")
            yield Static(
                f"🔒 To proceed, type the device name below:\n   Type: {self.disk.name}",
                classes="confirm-instruction",
            )

            yield Input(placeholder=f"Type '{self.disk.name}' to confirm...", id="confirm_input")

            with Horizontal(classes="button-row"):
                yield Button("Write ISO to USB", variant="error", id="write", disabled=True)
                yield Button("Go Back", id="back")

        yield Footer()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "confirm_input":
            self.confirmed = event.value.strip() == self.disk.name
            self.query_one("#write", Button).disabled = not self.confirmed

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "write":
            self.app.push_screen(WriteScreen(self.iso_path, self.disk, self.dry_run))
        else:
            self.app.pop_screen()


class WriteScreen(Screen):
    """Screen showing write progress."""

    progress: reactive[int] = reactive(0)

    def __init__(self, iso_path: str, disk: DiskInfo, dry_run: bool = False):
        super().__init__()
        self.iso_path = iso_path
        self.disk = disk
        self.dry_run = dry_run
        self.result = None
        self.message = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="main-container"):
            yield Static("Writing ISO to USB...", classes="title")

            if self.dry_run:
                yield Static("[DRY RUN MODE]", classes="info")

            with Container(classes="progress-box"):
                yield ProgressBar(total=100, show_eta=False, id="progress")
                yield Static("0%", id="progress_text", classes="progress-text")

            yield RichLog(id="log", highlight=True)

            with Horizontal(classes="button-row"):
                yield Button("Finish", variant="primary", id="finish", disabled=True)

        yield Footer()

    def on_mount(self) -> None:
        self.start_write()

    def start_write(self) -> None:
        """Start the write operation in a worker."""
        self.run_worker(self.do_write, thread=True)

    def do_write(self) -> None:
        """Perform the actual write operation."""
        worker = get_current_worker()

        def update_progress(value: int):
            self.app.call_from_thread(self.update_progress_ui, value)

        # Unmount disk first
        self.app.call_from_thread(self.log_message, "Unmounting disk...")
        DiskUtils.unmount_disk(self.disk.device)

        # Write ISO
        self.app.call_from_thread(
            self.log_message,
            f"{'Simulating' if self.dry_run else 'Writing'} ISO to {self.disk.device}...",
        )

        success, message = DiskUtils.write_iso(
            self.disk.device, self.iso_path, update_progress, self.dry_run
        )

        self.result = success
        self.message = message

        if success:
            self.app.call_from_thread(self.log_message, f"✅ {message}")
            self.app.call_from_thread(self.enable_finish)
        else:
            self.app.call_from_thread(self.log_message, f"❌ {message}")
            self.app.call_from_thread(self.enable_finish)

    def update_progress_ui(self, value: int) -> None:
        """Update progress bar."""
        self.progress = value
        self.query_one("#progress", ProgressBar).progress = value
        self.query_one("#progress_text", Static).update(f"{value}%")

    def log_message(self, message: str) -> None:
        """Add message to log."""
        self.query_one("#log", RichLog).write(message)

    def enable_finish(self) -> None:
        """Enable finish button."""
        self.query_one("#finish", Button).disabled = False

    @on(Button.Pressed, "#finish")
    def finish_writing(self) -> None:
        self.app.exit(0 if self.result else 1)


class BootableUSBApp(App):
    """Main application."""

    CSS = """
    Screen {
        align: center middle;
    }

    .centered {
        width: 80%;
        height: auto;
        border: solid $primary;
        padding: 2;
        text-align: center;
    }

    .main-container {
        width: 80;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1;
        width: 100%;
    }

    .section {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    .section-title {
        text-style: bold underline;
        color: $secondary;
        margin-bottom: 1;
    }

    .input-row {
        height: 3;
        width: 100%;
        align: left middle;
    }

    .input-row Input, .input-row Select {
        width: 1fr;
    }

    .input-row Button {
        width: 16;
        margin-left: 1;
    }

    .info-panel {
        color: $text-muted;
        height: 4;
        border: solid $surface-lighten-2;
        padding: 0 1;
        margin-top: 1;
        background: $surface-lighten-1;
    }

    .checkbox-row {
        height: 3;
        align: left middle;
    }

    .option-hint {
        margin-left: 2;
        color: $text-muted;
        text-style: italic;
    }

    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
        margin-bottom: 1;
    }

    .button-row Button {
        min-width: 20;
        margin: 0 2;
    }

    .confirm-box {
        border: solid $error;
        padding: 1;
        margin: 1 0;
    }

    .confirm-label {
        text-style: bold;
    }

    .confirm-value {
        text-style: bold;
        color: $text;
    }

    .confirm-value.danger {
        color: $error;
    }

    .confirm-instruction {
        text-align: center;
        text-style: bold;
        color: $warning;
    }

    .progress-box {
        align: center middle;
        height: auto;
        margin: 2 0;
    }

    .progress-text {
        text-align: center;
        text-style: bold;
        margin-top: 1;
    }

    .info {
        text-style: bold;
        color: $success;
        text-align: center;
    }

    Select {
        margin: 1 0;
    }

    #file_tree {
        height: 15;
        border: solid $surface;
        margin: 1 0;
        background: $surface;
    }

    #log {
        height: 10;
        border: solid $surface;
        margin: 1 0;
    }
    """

    SCREENS = {
        "warning": WarningScreen,
        "select": SelectionScreen,
    }

    def on_mount(self) -> None:
        self.push_screen("warning")


def check_root():
    """Check if running with appropriate privileges."""
    system = platform.system()

    if system in ("Linux", "Darwin"):
        if os.geteuid() != 0:
            print("⚠️  Warning: This tool should be run as root (sudo) for raw disk access.")
            print("   Without root privileges, USB device detection may fail.")
            print()
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != "yes":
                sys.exit(1)

    elif system == "Windows":
        try:
            import ctypes

            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠️  Warning: This tool should be run as Administrator.")
                print("   Without admin privileges, USB device detection may fail.")
                print()
                response = input("Continue anyway? (yes/no): ")
                if response.lower() != "yes":
                    sys.exit(1)
        except:
            pass


if __name__ == "__main__":
    # Check for root/admin privileges
    check_root()

    # Run the app
    app = BootableUSBApp()
    app.run()
