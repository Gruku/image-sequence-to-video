"""
Unit tests for utility functions that don't heavily depend on bpy.

Tests cover: format_time, format_size, check_for_alpha_channel
"""
import pytest


class TestFormatTime:
    """Tests for format_time function."""

    def test_zero_seconds(self):
        from image_sequence_to_video import format_time
        assert format_time(0) == "0m 0s"

    def test_seconds_only(self):
        from image_sequence_to_video import format_time
        assert format_time(45) == "0m 45s"

    def test_one_minute(self):
        from image_sequence_to_video import format_time
        assert format_time(60) == "1m 0s"

    def test_minutes_and_seconds(self):
        from image_sequence_to_video import format_time
        assert format_time(125) == "2m 5s"

    def test_one_hour(self):
        from image_sequence_to_video import format_time
        assert format_time(3600) == "60m 0s"

    def test_negative_returns_zero(self):
        from image_sequence_to_video import format_time
        assert format_time(-10) == "0m 0s"

    def test_negative_large_returns_zero(self):
        from image_sequence_to_video import format_time
        assert format_time(-1000) == "0m 0s"

    def test_very_large_returns_ellipsis(self):
        from image_sequence_to_video import format_time
        # More than a week (7 * 24 * 60 * 60 = 604800 seconds)
        assert format_time(86400 * 8) == "..."

    def test_exactly_one_week_not_ellipsis(self):
        from image_sequence_to_video import format_time
        # Exactly one week should NOT return ellipsis (boundary)
        result = format_time(86400 * 7)
        assert result != "..."

    def test_just_under_week_limit(self):
        from image_sequence_to_video import format_time
        result = format_time(86400 * 7 - 1)
        assert result != "..."
        assert "m" in result and "s" in result

    def test_float_seconds(self):
        from image_sequence_to_video import format_time
        # Should handle floats by truncating
        assert format_time(65.7) == "1m 5s"


class TestFormatSize:
    """Tests for format_size function."""

    def test_zero_bytes(self):
        from image_sequence_to_video import format_size
        assert format_size(0) == "0 B"

    def test_bytes_small(self):
        from image_sequence_to_video import format_size
        assert format_size(500) == "500 B"

    def test_bytes_boundary(self):
        from image_sequence_to_video import format_size
        assert format_size(1023) == "1023 B"

    def test_exactly_1kb(self):
        from image_sequence_to_video import format_size
        result = format_size(1024)
        assert "KB" in result
        assert "1.0" in result

    def test_kilobytes(self):
        from image_sequence_to_video import format_size
        result = format_size(2048)
        assert "KB" in result
        assert "2.0" in result

    def test_kilobytes_fractional(self):
        from image_sequence_to_video import format_size
        result = format_size(1536)  # 1.5 KB
        assert "KB" in result
        assert "1.5" in result

    def test_megabytes_boundary(self):
        from image_sequence_to_video import format_size
        result = format_size(1024 * 1024 - 1)
        assert "KB" in result

    def test_exactly_1mb(self):
        from image_sequence_to_video import format_size
        result = format_size(1024 * 1024)
        assert "MB" in result
        assert "1.00" in result

    def test_megabytes(self):
        from image_sequence_to_video import format_size
        result = format_size(5 * 1024 * 1024)
        assert "MB" in result
        assert "5.00" in result

    def test_megabytes_fractional(self):
        from image_sequence_to_video import format_size
        result = format_size(int(2.5 * 1024 * 1024))
        assert "MB" in result
        assert "2.50" in result

    def test_large_megabytes(self):
        from image_sequence_to_video import format_size
        result = format_size(500 * 1024 * 1024)  # 500 MB
        assert "MB" in result
        assert "500" in result


class TestCheckForAlphaChannel:
    """Tests for check_for_alpha_channel function."""

    def test_png_supports_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.png") is True

    def test_exr_supports_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.exr") is True

    def test_tiff_supports_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.tiff") is True

    def test_tif_supports_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.tif") is True

    def test_jpg_no_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.jpg") is False

    def test_jpeg_no_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.jpeg") is False

    def test_bmp_no_alpha(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.bmp") is False

    def test_case_insensitive_png(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/IMAGE.PNG") is True

    def test_case_insensitive_exr(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/IMAGE.EXR") is True

    def test_case_insensitive_jpg(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/IMAGE.JPG") is False

    def test_mixed_case(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/Image.Png") is True
        assert check_for_alpha_channel("/path/to/Image.Tiff") is True

    def test_path_with_dots(self):
        from image_sequence_to_video import check_for_alpha_channel
        # Should use the last extension
        assert check_for_alpha_channel("/path/to/image.backup.png") is True
        assert check_for_alpha_channel("/path/to/image.0001.exr") is True

    def test_unknown_extension(self):
        from image_sequence_to_video import check_for_alpha_channel
        assert check_for_alpha_channel("/path/to/image.xyz") is False
        assert check_for_alpha_channel("/path/to/image.webp") is False
