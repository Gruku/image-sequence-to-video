"""
Tests for _natural_sort_key function.

Natural sorting ensures frame_2.png comes before frame_10.png.
"""
import pytest


class TestNaturalSortKey:
    """Tests for natural sorting of file names."""

    def test_basic_natural_sort(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['frame_10.png', 'frame_2.png', 'frame_1.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['frame_1.png', 'frame_2.png', 'frame_10.png']

    def test_padded_numbers_sort_correctly(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['frame_0010.png', 'frame_0002.png', 'frame_0001.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['frame_0001.png', 'frame_0002.png', 'frame_0010.png']

    def test_mixed_padding_sorts_correctly(self):
        from image_sequence_to_video import _natural_sort_key

        # Some with padding, some without
        files = ['frame_10.png', 'frame_002.png', 'frame_1.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['frame_1.png', 'frame_002.png', 'frame_10.png']

    def test_alphabetic_prefix_then_number(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['b_10.png', 'a_2.png', 'a_10.png', 'a_1.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['a_1.png', 'a_2.png', 'a_10.png', 'b_10.png']

    def test_case_insensitive(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['Frame_2.png', 'frame_1.png', 'FRAME_3.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        # Case-insensitive sort
        assert sorted_files == ['frame_1.png', 'Frame_2.png', 'FRAME_3.png']

    def test_multiple_numbers_in_name(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['shot01_frame10.png', 'shot01_frame2.png', 'shot02_frame1.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['shot01_frame2.png', 'shot01_frame10.png', 'shot02_frame1.png']

    def test_dot_notation_sorting(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['render.0010.png', 'render.0002.png', 'render.0001.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['render.0001.png', 'render.0002.png', 'render.0010.png']

    def test_large_numbers(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['frame_1000.png', 'frame_100.png', 'frame_10.png', 'frame_1.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['frame_1.png', 'frame_10.png', 'frame_100.png', 'frame_1000.png']

    def test_no_numbers(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['charlie.png', 'alpha.png', 'bravo.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['alpha.png', 'bravo.png', 'charlie.png']

    def test_only_numbers(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['10.png', '2.png', '1.png', '100.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['1.png', '2.png', '10.png', '100.png']

    def test_empty_list(self):
        from image_sequence_to_video import _natural_sort_key

        files = []
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == []

    def test_single_item(self):
        from image_sequence_to_video import _natural_sort_key

        files = ['frame_0001.png']
        sorted_files = sorted(files, key=_natural_sort_key)

        assert sorted_files == ['frame_0001.png']


class TestNaturalSortKeyDirectValue:
    """Tests that directly check the key function output."""

    def test_returns_list(self):
        from image_sequence_to_video import _natural_sort_key

        result = _natural_sort_key("test_123.png")

        assert isinstance(result, list)

    def test_numbers_are_integers_in_key(self):
        from image_sequence_to_video import _natural_sort_key

        result = _natural_sort_key("frame_0001.png")

        # Should have integer 1 somewhere in the key
        assert any(isinstance(x, int) for x in result)

    def test_text_parts_are_lowercase(self):
        from image_sequence_to_video import _natural_sort_key

        result = _natural_sort_key("FRAME_0001.PNG")

        # All string parts should be lowercase
        for part in result:
            if isinstance(part, str):
                assert part == part.lower()
