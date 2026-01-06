"""
Tests for find_image_sequence function.

This is a critical function that detects image sequences from various inputs.
"""
import os
import pytest


class TestFindImageSequenceFromDirectory:
    """Tests for finding sequences when given a directory path."""

    def test_finds_sequence_in_directory(self, sample_sequence_dir):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence(str(sample_sequence_dir))

        assert directory == str(sample_sequence_dir)
        assert len(files) == 10
        assert files[0] == "frame_0001.png"
        assert files[-1] == "frame_0010.png"

    def test_returns_largest_sequence_when_multiple(self, mixed_sequence_dir):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence(str(mixed_sequence_dir))

        # Should return the render sequence (5 files) not preview (3 files)
        assert len(files) == 5
        assert "render_" in files[0]

    def test_empty_directory_returns_empty(self, empty_dir):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence(str(empty_dir))

        assert directory is None
        assert files == []

    def test_non_image_files_ignored(self, non_image_dir):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence(str(non_image_dir))

        assert directory is None
        assert files == []

    def test_dot_notation_sequence(self, dot_notation_dir):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence(str(dot_notation_dir))

        assert len(files) == 5
        assert "render.0001.png" in files[0]


class TestFindImageSequenceFromFile:
    """Tests for finding sequences when given a file path."""

    def test_finds_sequence_from_file_path(self, sample_sequence_dir):
        from image_sequence_to_video import find_image_sequence

        file_path = sample_sequence_dir / "frame_0005.png"
        directory, files = find_image_sequence(str(file_path))

        assert directory == str(sample_sequence_dir)
        assert len(files) == 10

    def test_finds_sequence_from_first_file(self, sample_sequence_dir):
        from image_sequence_to_video import find_image_sequence

        file_path = sample_sequence_dir / "frame_0001.png"
        directory, files = find_image_sequence(str(file_path))

        assert directory == str(sample_sequence_dir)
        assert len(files) == 10

    def test_finds_sequence_from_last_file(self, sample_sequence_dir):
        from image_sequence_to_video import find_image_sequence

        file_path = sample_sequence_dir / "frame_0010.png"
        directory, files = find_image_sequence(str(file_path))

        assert directory == str(sample_sequence_dir)
        assert len(files) == 10

    def test_non_image_file_returns_empty(self, tmp_path):
        from image_sequence_to_video import find_image_sequence

        # Create a non-image file
        text_file = tmp_path / "document.txt"
        text_file.write_text("hello")

        directory, files = find_image_sequence(str(text_file))

        assert directory is None
        assert files == []


class TestFindImageSequenceEdgeCases:
    """Edge case tests for sequence detection."""

    def test_nonexistent_path_returns_empty(self):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence("/nonexistent/path/to/nowhere")

        assert directory is None
        assert files == []

    def test_empty_string_returns_empty(self):
        from image_sequence_to_video import find_image_sequence

        directory, files = find_image_sequence("")

        assert directory is None
        assert files == []

    def test_single_image_returns_single(self, tmp_path):
        from image_sequence_to_video import find_image_sequence

        # Create a single image (no sequence)
        single_dir = tmp_path / "single"
        single_dir.mkdir()
        (single_dir / "lonely_image.png").write_bytes(b'\x89PNG' + b'\x00' * 100)

        directory, files = find_image_sequence(str(single_dir))

        # Single non-numbered file should not be detected as sequence
        assert files == [] or len(files) == 1


class TestFindImageSequenceFormats:
    """Tests for different image format support."""

    def test_jpg_sequence(self, tmp_path):
        from image_sequence_to_video import find_image_sequence

        seq_dir = tmp_path / "jpg_seq"
        seq_dir.mkdir()

        for i in range(1, 6):
            (seq_dir / f"photo_{i:04d}.jpg").write_bytes(b'\xff\xd8\xff' + b'\x00' * 100)

        directory, files = find_image_sequence(str(seq_dir))

        assert len(files) == 5
        assert all(f.endswith('.jpg') for f in files)

    def test_exr_sequence(self, tmp_path):
        from image_sequence_to_video import find_image_sequence

        seq_dir = tmp_path / "exr_seq"
        seq_dir.mkdir()

        for i in range(1, 4):
            (seq_dir / f"render_{i:04d}.exr").write_bytes(b'\x76\x2f\x31\x01' + b'\x00' * 100)

        directory, files = find_image_sequence(str(seq_dir))

        assert len(files) == 3
        assert all(f.endswith('.exr') for f in files)

    def test_tiff_sequence(self, tmp_path):
        from image_sequence_to_video import find_image_sequence

        seq_dir = tmp_path / "tiff_seq"
        seq_dir.mkdir()

        for i in range(1, 4):
            (seq_dir / f"scan_{i:04d}.tiff").write_bytes(b'II*\x00' + b'\x00' * 100)

        directory, files = find_image_sequence(str(seq_dir))

        assert len(files) == 3
        assert all(f.endswith('.tiff') for f in files)


class TestFindImageSequenceMixedContent:
    """Tests for directories with mixed content."""

    def test_ignores_non_image_files_in_sequence_dir(self, tmp_path):
        from image_sequence_to_video import find_image_sequence

        seq_dir = tmp_path / "mixed_types"
        seq_dir.mkdir()

        # Create image sequence
        for i in range(1, 4):
            (seq_dir / f"frame_{i:04d}.png").write_bytes(b'\x89PNG' + b'\x00' * 100)

        # Create non-image files with similar names (should be ignored)
        (seq_dir / "frame_0004.txt").write_text("not an image")
        (seq_dir / "frame_0005.mp4").write_bytes(b'\x00' * 100)
        (seq_dir / "readme.md").write_text("documentation")

        directory, files = find_image_sequence(str(seq_dir))

        assert len(files) == 3
        assert all(f.endswith('.png') for f in files)
