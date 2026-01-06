# Development Setup Guide

This guide helps you set up a development environment for the Image Sequence to Video addon.

## Prerequisites

- **Python 3.10+** (matching Blender's Python version)
- **Blender 5.0+**
- **VS Code** (recommended)
- **Git**

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/image-sequence-to-video.git
   cd image-sequence-to-video
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Install fake-bpy-module for autocomplete:**
   ```bash
   # For latest Blender version
   pip install fake-bpy-module-latest

   # Or for specific version
   pip install fake-bpy-module-4.3
   ```

5. **Open in VS Code:**
   ```bash
   code .
   ```

6. **Install recommended extensions:**
   VS Code will prompt you to install recommended extensions. Accept to get:
   - Python
   - Pylance
   - Black Formatter
   - Ruff
   - Blender Development

## Project Structure

```
image-sequence-to-video/
├── image_sequence_to_video.py   # Main addon (single file)
├── README.md                     # User documentation
├── LICENSE                       # GPL-3.0 license
├── CHANGELOG.md                  # Version history
├── pyproject.toml               # Project config & pytest settings
├── requirements-dev.txt         # Development dependencies
├── .gitignore
├── .vscode/
│   ├── settings.json            # Python/editor settings
│   ├── launch.json              # Debug configurations
│   ├── tasks.json               # Build tasks
│   └── extensions.json          # Recommended extensions
├── tests/
│   ├── conftest.py              # Pytest fixtures & bpy mock
│   ├── test_utility_functions.py
│   ├── test_sequence_detection.py
│   ├── test_ffmpeg_args.py
│   ├── test_versioning.py
│   └── test_natural_sort.py
├── docs/
│   ├── TESTING_GUIDE.md         # Manual testing procedures
│   └── DEVELOPMENT_SETUP.md     # This file
└── gumroad/
    ├── product_description.md
    ├── cover_image_specs.md
    └── demo_video_script.md
```

## Running Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_utility_functions.py -v
```

### Run with coverage report:
```bash
pytest tests/ -v --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Run tests in VS Code:
- Use the Testing sidebar (beaker icon)
- Or press `Ctrl+Shift+P` > "Python: Run All Tests"

## VS Code Tasks

Access via `Ctrl+Shift+P` > "Tasks: Run Task":

| Task | Description |
|------|-------------|
| Run All Tests | Execute pytest |
| Run Tests with Coverage | pytest + coverage report |
| Install Addon to Blender 5.0 | Copy addon to Blender's addons folder |
| Lint with Ruff | Check code style |
| Type Check with MyPy | Static type analysis |
| Create Distribution ZIP | Package for release |

## Debugging in Blender

### Setup (one-time):
1. Install `debugpy` in Blender's Python:
   ```bash
   # Find Blender's Python path
   # Windows: C:\Program Files\Blender Foundation\Blender 5.0\5.0\python\bin\python.exe

   "C:\...\python.exe" -m pip install debugpy
   ```

2. Or install the [Blender Development](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development) VS Code extension.

### Debugging workflow:

1. **In Blender**, start debug server:
   - Press `F3`, search "Debug: Start Debug Server"
   - Or run in Python console:
     ```python
     import debugpy
     debugpy.listen(5678)
     print("Waiting for debugger...")
     ```

2. **In VS Code**, attach debugger:
   - Run "Python: Attach to Blender" configuration
   - Set breakpoints in `image_sequence_to_video.py`

3. **In Blender**, trigger your code:
   - Use the addon UI
   - Breakpoints will pause execution

## Installing the Addon for Testing

### Method 1: VS Code task
Run the "Install Addon to Blender 5.0" task.

### Method 2: Manual
Copy `image_sequence_to_video.py` to:
- **Windows:** `%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\`
- **macOS:** `~/Library/Application Support/Blender/5.0/scripts/addons/`
- **Linux:** `~/.config/blender/5.0/scripts/addons/`

### Method 3: Symlink (recommended for development)
```bash
# Windows (run as admin)
mklink "%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\image_sequence_to_video.py" "C:\path\to\repo\image_sequence_to_video.py"

# macOS/Linux
ln -s /path/to/repo/image_sequence_to_video.py ~/.config/blender/5.0/scripts/addons/
```

After symlinking, changes to the file are immediately available - just reload the addon in Blender (disable/enable or press F3 > "Reload Scripts").

## Code Style

This project uses:
- **Black** for formatting (line length: 120)
- **Ruff** for linting
- **MyPy** for type checking (optional)

Format on save is enabled in VS Code settings.

### Manual formatting:
```bash
black image_sequence_to_video.py
ruff check image_sequence_to_video.py --fix
```

## Understanding the Mock System

Tests run without Blender by using a mock `bpy` module. See `tests/conftest.py`:

```python
# The mock is installed before any imports
sys.modules['bpy'] = mock_bpy

# Tests can then import the addon
from image_sequence_to_video import format_time
```

**What can be tested without Blender:**
- Utility functions (format_time, format_size, etc.)
- Sequence detection logic
- FFmpeg argument generation
- File versioning

**What requires Blender for testing:**
- UI panels and operators
- Actual video rendering
- Blender API interactions

## Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```

2. Make changes to `image_sequence_to_video.py`

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

4. Test in Blender manually (see TESTING_GUIDE.md)

5. Update CHANGELOG.md

6. Commit and push:
   ```bash
   git add .
   git commit -m "Add your feature"
   git push origin feature/your-feature
   ```

## Release Process

1. Update version in `bl_info` (image_sequence_to_video.py)
2. Update version in `pyproject.toml`
3. Update CHANGELOG.md with release date
4. Run full test suite
5. Manual testing in Blender
6. Create distribution ZIP:
   ```bash
   # Via VS Code task or manually:
   zip -r dist/image_sequence_to_video_vX.Y.zip \
       image_sequence_to_video.py README.md LICENSE CHANGELOG.md
   ```
7. Create GitHub release with ZIP
8. Upload to Gumroad

## Troubleshooting

### "No module named 'bpy'" in tests
Ensure `conftest.py` is being loaded. Run from project root:
```bash
pytest tests/ -v
```

### Addon not appearing in Blender
- Check Blender console for errors (Window > Toggle System Console on Windows)
- Verify file is in correct addons folder
- Try disabling and re-enabling

### FFmpeg not found
- Verify FFmpeg is installed: `ffmpeg -version`
- Check it's in system PATH
- On Windows, may need to restart after adding to PATH

### Tests failing after code changes
Run tests with verbose output:
```bash
pytest tests/ -v --tb=long
```
