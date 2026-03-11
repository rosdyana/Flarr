#!/usr/bin/env python3
"""Bootable USB Creator - Simple Version.

Ultra-lightweight, no external dependencies.
Uses only Python standard library.

WARNING: This tool writes raw data to disks. Use with extreme caution.
"""

import json
import os
import platform
import re
import subprocess
import sys


def clear():
    """Clear the terminal."""
    os.system("cls" if platform.system() == "Windows" else "clear")


def print_header():
    """Print the application header."""
    print("=" * 60)
    print("     BOOTABLE USB CREATOR - Simple Version")
    print("=" * 60)
    print()


def print_warning():
    """Print the warning message."""
    print("⚠️  WARNING - READ CAREFULLY ⚠️")
    print("-" * 60)
    print("""
This tool writes raw data to USB devices.

INCORRECT USE CAN DESTROY DATA ON THE WRONG DISK!

Safety features:
  • Only removable USB devices are shown
  • You must confirm the disk selection TWICE
  • Device details are displayed for verification

Always ensure you have backups of important data.
""")
    print("-" * 60)
    print()


def confirm(msg="Continue?"):
    """Ask for yes/no confirmation."""
    while True:
        resp = input(f"{msg} (yes/no): ").strip().lower()
        if resp in ("yes", "y"):
            return True
        if resp in ("no", "n"):
            return False
        print("Please type 'yes' or 'no'")


def format_size(size_bytes):
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def parse_size(size_str):
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


def get_linux_disks():
    """Get USB disks on Linux."""
    disks = []
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,SIZE,MODEL,TYPE,RM,TRAN,SERIAL"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)

        for device in data.get("blockdevices", []):
            if device.get("type") != "disk":
                continue

            device_name = device.get("name", "")
            device_path = f"/dev/{device_name}"

            is_removable = device.get("rm") in ("1", True)
            is_usb = device.get("tran") == "usb"

            removable_file = f"/sys/class/block/{device_name}/removable"
            if os.path.exists(removable_file):
                try:
                    with open(removable_file) as f:
                        is_removable = f.read().strip() == "1"
                except OSError:
                    pass

            if not (is_removable or is_usb):
                continue

            if device_name.startswith(("loop", "ram", "dm-")):
                continue

            size_str = device.get("size", "Unknown")
            model = device.get("model", "Unknown USB").strip()

            disks.append(
                {
                    "device": device_path,
                    "name": device_name,
                    "size": size_str,
                    "size_bytes": parse_size(size_str),
                    "model": model if model else "Unknown USB Device",
                    "is_usb": is_usb,
                }
            )
    except Exception as e:
        print(f"Error detecting disks: {e}")

    return disks


def get_macos_disks():
    """Get USB disks on macOS."""
    disks = []
    try:
        import plistlib

        result = subprocess.run(["diskutil", "list", "-plist"], capture_output=True, check=True)
        plist = plistlib.loads(result.stdout)

        for disk in plist.get("AllDisksAndPartitions", []):
            device_id = disk.get("DeviceIdentifier", "")
            device_path = f"/dev/{device_id}"

            info_result = subprocess.run(
                ["diskutil", "info", "-plist", device_path], capture_output=True, check=True
            )
            info = plistlib.loads(info_result.stdout)

            is_removable = info.get("RemovableMedia", False)
            is_internal = info.get("Internal", True)
            protocol = info.get("BusProtocol", "").lower()
            is_usb = "usb" in protocol

            if not (is_removable and not is_internal and is_usb):
                continue

            size_bytes = info.get("TotalSize", 0)
            model = info.get("MediaName", "Unknown USB")

            disks.append(
                {
                    "device": device_path,
                    "name": device_id,
                    "size": format_size(size_bytes),
                    "size_bytes": size_bytes,
                    "model": model,
                    "is_usb": True,
                }
            )
    except Exception as e:
        print(f"Error detecting disks: {e}")

    return disks


def get_windows_disks():
    """Get USB disks on Windows."""
    disks = []
    try:
        ps_command = """
        Get-Disk | Where-Object { $_.BusType -eq 'USB' } |
        Select-Object DeviceID, FriendlyName, Size | ConvertTo-Json
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_command], capture_output=True, text=True, check=True
        )

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        for disk in data:
            device_id = disk.get("DeviceID", 0)
            size_bytes = disk.get("Size", 0)
            model = disk.get("FriendlyName", "Unknown USB")

            disks.append(
                {
                    "device": f"\\\\.\\PhysicalDrive{device_id}",
                    "name": f"PhysicalDrive{device_id}",
                    "size": format_size(size_bytes),
                    "size_bytes": size_bytes,
                    "model": model,
                    "is_usb": True,
                }
            )
    except Exception as e:
        print(f"Error detecting disks: {e}")

    return disks


def get_usb_disks():
    """Get list of USB disks based on platform."""
    system = platform.system()

    if system == "Linux":
        return get_linux_disks()
    elif system == "Darwin":
        return get_macos_disks()
    elif system == "Windows":
        return get_windows_disks()
    else:
        print(f"Unsupported platform: {system}")
        return []


def select_iso():
    """Let user select an ISO file."""
    print("\n📁 ISO FILE SELECTION")
    print("-" * 60)

    while True:
        path = input("Enter path to ISO file: ").strip()

        if not path:
            print("Please enter a path")
            continue

        path = os.path.expanduser(path)

        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            continue

        if not os.path.isfile(path):
            print(f"❌ Not a file: {path}")
            continue

        if not path.lower().endswith(".iso"):
            print("⚠️  Warning: File doesn't have .iso extension")
            if not confirm("Continue anyway?"):
                continue

        size = os.path.getsize(path)
        print(f"✅ Selected: {path}")
        print(f"   Size: {format_size(size)}")

        return path


def select_usb_disk():
    """Let user select a USB disk."""
    print("\n🔌 USB DEVICE SELECTION")
    print("-" * 60)

    disks = get_usb_disks()

    if not disks:
        print("❌ No USB devices found!")
        print("   - Insert a USB drive")
        print("   - Run with sudo/admin privileges")
        return None

    print("\nAvailable USB devices:")
    print()

    for i, disk in enumerate(disks, 1):
        print(f"  [{i}] {disk['device']}")
        print(f"      Model: {disk['model']}")
        print(f"      Size:  {disk['size']}")
        print()

    while True:
        try:
            choice = input(f"Select device (1-{len(disks)}): ").strip()
            idx = int(choice) - 1

            if 0 <= idx < len(disks):
                return disks[idx]
            else:
                print(f"Please enter a number between 1 and {len(disks)}")
        except ValueError:
            print("Please enter a valid number")


def final_confirm(iso_path, disk, dry_run=False):
    """Final confirmation with safety check."""
    print("\n" + "=" * 60)
    print("⚠️  FINAL CONFIRMATION - READ CAREFULLY")
    print("=" * 60)
    print()
    print("You are about to write:")
    print(f"  💿 ISO: {iso_path}")
    print(f"     Size: {format_size(os.path.getsize(iso_path))}")
    print()
    print("To USB device:")
    print(f"  🔌 Device: {disk['device']} ***")
    print(f"     Model:  {disk['model']}")
    print(f"     Size:   {disk['size']}")
    print()

    if dry_run:
        print("[DRY RUN MODE - No actual writing will occur]")
        print()

    print("⚠️  ALL DATA ON THIS USB DEVICE WILL BE ERASED!")
    print()
    print("=" * 60)
    print()

    # Safety check: type device name
    print(f"🔒 To proceed, type the device name: {disk['name']}")
    confirm_input = input("Type device name to confirm: ").strip()

    if confirm_input != disk["name"]:
        print("❌ Device name does not match. Operation cancelled.")
        return False

    return True


def unmount_disk(device):
    """Unmount/eject disk before writing."""
    system = platform.system()

    try:
        if system == "Linux":
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,MOUNTPOINT", device], capture_output=True, text=True
            )
            data = json.loads(result.stdout)

            for dev in data.get("blockdevices", []):
                for child in dev.get("children", []):
                    mountpoint = child.get("mountpoint")
                    if mountpoint:
                        print(f"  Unmounting {mountpoint}...")
                        subprocess.run(["umount", mountpoint], capture_output=True)

        elif system == "Darwin":
            print(f"  Unmounting {device}...")
            subprocess.run(["diskutil", "unmountDisk", device], capture_output=True)

    except Exception as e:
        print(f"  Warning: Could not unmount: {e}")


def write_iso(device, iso_path, dry_run=False):
    """Write ISO to USB device."""
    system = platform.system()
    if dry_run:
        print("\n[DRY RUN - Simulating write...]")
        for i in range(0, 101, 10):
            print(f"  Progress: {i}%")
            import time

            time.sleep(0.2)
        print("\n✅ Dry run completed successfully!")
        return True

    print("\n📝 Writing ISO to USB...")
    print("   This may take several minutes. Do not remove the USB drive.")
    print()

    # Unmount first
    print("Preparing disk...")
    unmount_disk(device)

    try:
        if system in ("Linux", "Darwin"):
            # Use dd
            cmd = ["dd", f"if={iso_path}", f"of={device}", "bs=4M", "status=progress", "conv=fsync"]
            if system == "Darwin":
                cmd[3] = "bs=4m"

            print(f"Running: {' '.join(cmd)}")
            print()

            result = subprocess.run(cmd)

            if result.returncode == 0:
                print("\n✅ ISO written successfully!")
                return True
            else:
                print(f"\n❌ Write failed with code {result.returncode}")
                return False

        elif system == "Windows":
            # Windows requires special handling
            print("Windows detected. Using PowerShell...")
            print("⚠️  Windows raw disk writing requires special handling.")
            print("   Please use a tool like Rufus on Windows instead.")
            return False

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def check_privileges():
    """Check if running with appropriate privileges."""
    system = platform.system()

    if system in ("Linux", "Darwin"):
        if os.geteuid() != 0:
            print("⚠️  Warning: Not running as root.")
            print("   USB device detection may fail without root privileges.")
            print()
            if not confirm("Continue anyway?"):
                sys.exit(1)

    elif system == "Windows":
        try:
            import ctypes

            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠️  Warning: Not running as Administrator.")
                print("   USB device detection may fail without admin privileges.")
                print()
                if not confirm("Continue anyway?"):
                    sys.exit(1)
        except Exception:
            pass


def main():
    """Main application flow."""
    clear()
    print_header()

    # Check privileges
    check_privileges()

    # Show warning
    print_warning()

    if not confirm("Do you understand and wish to continue?"):
        print("\nExiting...")
        sys.exit(0)

    # Select ISO
    clear()
    print_header()
    iso_path = select_iso()

    # Select USB
    clear()
    print_header()
    disk = select_usb_disk()

    if disk is None:
        print("\nNo USB device selected. Exiting...")
        sys.exit(1)

    # Ask for dry run
    print()
    dry_run = confirm("Run in dry-run mode (test without writing)?")

    # Final confirmation
    clear()
    print_header()

    if not final_confirm(iso_path, disk, dry_run):
        print("\nOperation cancelled.")
        sys.exit(1)

    # Write ISO
    success = write_iso(disk["device"], iso_path, dry_run)

    print()
    if success:
        print("=" * 60)
        print("🎉 Bootable USB created successfully!")
        print("=" * 60)
        print()
        print("You can now boot from this USB device.")
        print("Remember to select it in your BIOS/UEFI boot menu.")
    else:
        print("=" * 60)
        print("❌ Operation failed")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(1)
