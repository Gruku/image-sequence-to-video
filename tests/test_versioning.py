"""
Tests for get_versioned_output_path function.

This function ensures output files don't overwrite existing ones.
"""
import os
import pytest


class TestVersionedOutputPath:
    """Tests for automatic file versioning."""

    def test_first_version_is_v001(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "render", "mp4")

        assert result.endswith("render_v001.mp4")
        assert str(output_dir) in result

    def test_increments_version_when_exists(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        # Create v001
        (output_dir / "render_v001.mp4").write_bytes(b'\x00')

        result = get_versioned_output_path(str(output_dir), "render", "mp4")

        assert result.endswith("render_v002.mp4")

    def test_skips_existing_versions(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        # Create v001, v002, v003
        (output_dir / "render_v001.mp4").write_bytes(b'\x00')
        (output_dir / "render_v002.mp4").write_bytes(b'\x00')
        (output_dir / "render_v003.mp4").write_bytes(b'\x00')

        result = get_versioned_output_path(str(output_dir), "render", "mp4")

        assert result.endswith("render_v004.mp4")

    def test_handles_gaps_in_versions(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        # Create v001 and v003 (gap at v002)
        (output_dir / "render_v001.mp4").write_bytes(b'\x00')
        (output_dir / "render_v003.mp4").write_bytes(b'\x00')

        result = get_versioned_output_path(str(output_dir), "render", "mp4")

        # Should fill the gap at v002
        assert result.endswith("render_v002.mp4")

    def test_different_base_names_independent(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        # Create v001 for "render"
        (output_dir / "render_v001.mp4").write_bytes(b'\x00')

        # "animation" should still get v001
        result = get_versioned_output_path(str(output_dir), "animation", "mp4")

        assert result.endswith("animation_v001.mp4")

    def test_different_extensions_independent(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        # Create v001 for mp4
        (output_dir / "render_v001.mp4").write_bytes(b'\x00')

        # webm should still get v001
        result = get_versioned_output_path(str(output_dir), "render", "webm")

        assert result.endswith("render_v001.webm")

    def test_webm_extension(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "video", "webm")

        assert result.endswith("video_v001.webm")

    def test_mov_extension(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "prores_out", "mov")

        assert result.endswith("prores_out_v001.mov")

    def test_base_name_with_underscores(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "my_cool_render", "mp4")

        assert result.endswith("my_cool_render_v001.mp4")

    def test_base_name_with_spaces(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "my render", "mp4")

        assert "my render_v001.mp4" in result


class TestVersioningEdgeCases:
    """Edge case tests for versioning."""

    def test_returns_full_absolute_path(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "test", "mp4")

        assert os.path.isabs(result)

    def test_path_contains_output_dir(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "test", "mp4")

        assert str(output_dir) in result

    def test_version_number_padded_to_3_digits(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        result = get_versioned_output_path(str(output_dir), "test", "mp4")

        # v001 not v1
        assert "_v001." in result

    def test_handles_many_existing_versions(self, output_dir):
        from image_sequence_to_video import get_versioned_output_path

        # Create 50 versions
        for i in range(1, 51):
            (output_dir / f"render_v{i:03d}.mp4").write_bytes(b'\x00')

        result = get_versioned_output_path(str(output_dir), "render", "mp4")

        assert result.endswith("render_v051.mp4")
