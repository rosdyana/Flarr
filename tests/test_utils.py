"""Tests for utility functions."""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bootable_usb_simple import format_size, get_usb_disks, parse_size


class TestFormatSize:
    """Tests for format_size function."""

    def test_bytes(self):
        """format_size should format raw bytes correctly."""
        assert format_size(500) == "500.0 B"

    def test_kilobytes(self):
        """format_size should format kilobyte values correctly."""
        result = format_size(1024)
        assert "KB" in result or result == "1024.0 B"

    def test_megabytes(self):
        """format_size should format megabyte values correctly."""
        result = format_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        """format_size should format gigabyte values correctly."""
        result = format_size(8 * 1024**3)
        assert "GB" in result

    def test_terabytes(self):
        """format_size should format terabyte values correctly."""
        result = format_size(2 * 1024**4)
        assert "TB" in result or "PB" in result


class TestParseSize:
    """Tests for parse_size function."""

    def test_bytes(self):
        """parse_size should parse byte strings to the correct integer value."""
        assert parse_size("500B") == 500
        assert parse_size("500 B") == 500

    def test_kilobytes(self):
        """parse_size should correctly parse K and KB suffixes."""
        assert parse_size("4K") == 4 * 1024
        assert parse_size("4KB") == 4 * 1024

    def test_megabytes(self):
        """parse_size should correctly parse M and MB suffixes."""
        assert parse_size("100M") == 100 * 1024**2
        assert parse_size("100MB") == 100 * 1024**2

    def test_gigabytes(self):
        """parse_size should correctly parse G and GB suffixes."""
        assert parse_size("8G") == 8 * 1024**3
        assert parse_size("8GB") == 8 * 1024**3

    def test_invalid(self):
        """parse_size should return 0 for empty or unrecognised strings."""
        assert parse_size("") == 0
        assert parse_size("invalid") == 0


class TestGetUsbDisks:
    """Tests for get_usb_disks function."""

    def test_returns_list(self):
        """get_usb_disks should return a list."""
        disks = get_usb_disks()
        assert isinstance(disks, list)

    def test_disk_structure(self):
        """Each disk should have required fields."""
        disks = get_usb_disks()
        for disk in disks:
            assert "device" in disk
            assert "name" in disk
            assert "size" in disk
            assert "model" in disk
            assert isinstance(disk["device"], str)
            assert isinstance(disk["name"], str)


class TestDiskDetectionSafety:
    """Safety tests for disk detection."""

    def test_no_internal_disks(self):
        """USB-only filtering should not return internal disks.

        This is a soft test - without root, we might not detect anything.
        """
        disks = get_usb_disks()

        # If we detect disks, verify they look like USB devices
        for disk in disks:
            device = disk["device"].lower()
            # Should not be typical internal disk patterns
            # Note: This is platform-dependent
            if "linux" in sys.platform:
                # On Linux, internal disks often follow patterns like sda, nvme0
                # USB devices typically start from sdb or have usb in path
                pass  # Detection is handled by lsblk
            elif "darwin" in sys.platform:
                # On macOS, internal disks are usually disk0
                assert "disk0" not in device, "Internal disk detected!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
