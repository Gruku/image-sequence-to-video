"""
Pytest configuration and shared fixtures for Image Sequence to Video tests.

This module sets up a mock bpy module so tests can run without Blender.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add parent directory to path to import the addon
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_bpy():
    """Create a comprehensive mock bpy module for testing without Blender."""
    mock = MagicMock()

    # Mock submodules
    mock.props = MagicMock()
    mock.types = MagicMock()
    mock.utils = MagicMock()
    mock.context = MagicMock()
    mock.data = MagicMock()
    mock.ops = MagicMock()
    mock.path = MagicMock()
    mock.app = MagicMock()

    # Mock commonly used types as actual classes
    mock.types.PropertyGroup = type('PropertyGroup', (), {})
    mock.types.Operator = type('Operator', (), {'bl_options': set()})
    mock.types.Panel = type('Panel', (), {})

    # Mock property functions to return MagicMock that can be used as decorators/descriptors
    mock.props.StringProperty = MagicMock(return_value="")
    mock.props.EnumProperty = MagicMock(return_value="")
    mock.props.IntProperty = MagicMock(return_value=0)
    mock.props.BoolProperty = MagicMock(return_value=False)
    mock.props.FloatProperty = MagicMock(return_value=0.0)
    mock.props.PointerProperty = MagicMock(return_value=None)

    # Mock bpy.path.abspath to just return the path
    mock.path.abspath = lambda x: x

    return mock


@pytest.fixture(scope="session", autouse=True)
def install_bpy_mock():
    """Install the bpy mock before any imports."""
    mock_bpy = create_mock_bpy()

    # Install mock modules
    sys.modules['bpy'] = mock_bpy
    sys.modules['bpy.props'] = mock_bpy.props
    sys.modules['bpy.types'] = mock_bpy.types
    sys.modules['bpy.utils'] = mock_bpy.utils

    yield mock_bpy

    # Cleanup after all tests
    for mod in ['bpy', 'bpy.props', 'bpy.types', 'bpy.utils']:
        sys.modules.pop(mod, None)


@pytest.fixture
def sample_sequence_dir(tmp_path):
    """Create a temporary directory with a sample image sequence (10 frames)."""
    seq_dir = tmp_path / "sequence"
    seq_dir.mkdir()

    # Create dummy PNG files with minimal valid PNG header
    png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    for i in range(1, 11):
        (seq_dir / f"frame_{i:04d}.png").write_bytes(png_header)

    return seq_dir


@pytest.fixture
def mixed_sequence_dir(tmp_path):
    """Create a directory with multiple image sequences."""
    seq_dir = tmp_path / "mixed"
    seq_dir.mkdir()

    png_header = b'\x89PNG' + b'\x00' * 100
    jpg_header = b'\xff\xd8\xff' + b'\x00' * 100

    # First sequence: render_ (5 frames)
    for i in range(1, 6):
        (seq_dir / f"render_{i:04d}.png").write_bytes(png_header)

    # Second sequence: preview_ (3 frames)
    for i in range(1, 4):
        (seq_dir / f"preview_{i:04d}.jpg").write_bytes(jpg_header)

    return seq_dir


@pytest.fixture
def dot_notation_dir(tmp_path):
    """Create a directory with dot notation naming (render.0001.png)."""
    seq_dir = tmp_path / "dot_notation"
    seq_dir.mkdir()

    png_header = b'\x89PNG' + b'\x00' * 100

    for i in range(1, 6):
        (seq_dir / f"render.{i:04d}.png").write_bytes(png_header)

    return seq_dir


@pytest.fixture
def empty_dir(tmp_path):
    """Create an empty temporary directory."""
    empty = tmp_path / "empty"
    empty.mkdir()
    return empty


@pytest.fixture
def non_image_dir(tmp_path):
    """Create a directory with non-image files only."""
    dir_path = tmp_path / "non_images"
    dir_path.mkdir()

    (dir_path / "file_0001.txt").write_text("not an image")
    (dir_path / "file_0002.mp4").write_bytes(b'\x00' * 100)
    (dir_path / "file_0003.pdf").write_bytes(b'%PDF' + b'\x00' * 100)

    return dir_path


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory for versioning tests."""
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    return out_dir


@pytest.fixture
def fixtures_dir():
    """Return path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"
