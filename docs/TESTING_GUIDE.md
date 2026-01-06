# Image Sequence to Video - Manual Testing Guide

This guide covers manual testing procedures for the addon. Use it before releases or after significant changes.

## Prerequisites

- Blender 5.0+ installed
- FFmpeg installed and in PATH (optional, for FFmpeg encoder tests)
- Sample image sequences for testing

## Setting Up Test Sequences

### 1. Simple Numbered Sequence
Create a folder with 10+ PNG files:
```
test_sequences/simple/
  frame_0001.png
  frame_0002.png
  ...
  frame_0010.png
```

### 2. Alpha Channel Sequence
Create PNG files with transparency (32-bit depth):
```
test_sequences/alpha/
  alpha_0001.png
  alpha_0002.png
  ...
```

### 3. Various Naming Patterns
Test different naming conventions:
```
test_sequences/dot_notation/    -> render.0001.png, render.0002.png
test_sequences/underscore/      -> render_0001.png, render_0002.png
test_sequences/no_padding/      -> render_1.png, render_2.png, render_10.png
```

## Test Scenarios

### T1: Basic FFmpeg Conversion

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enable addon in Edit > Preferences > Add-ons | Addon appears, no errors |
| 2 | Open Render Properties panel | "Image Sequence to Video" section visible |
| 3 | Click "Convert Image Sequence" | Dialog opens |
| 4 | Browse to simple sequence folder | Path populates correctly |
| 5 | Keep FFmpeg encoder selected | "FFmpeg found" indicator shows (if installed) |
| 6 | Set quality to MEDIUM, codec to H.264 | Settings applied |
| 7 | Click OK | Progress indicator appears |
| 8 | Wait for completion | "Complete!" message with file size shown |
| 9 | Click "Open Video" | Video plays in system player |
| 10 | Verify video | Correct frame count, no artifacts |

### T2: Blender VSE Conversion

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open conversion dialog | Dialog appears |
| 2 | Select "Blender (Full Control)" encoder | Color management options appear |
| 3 | Enable "Override Color Settings" | View transform dropdown enables |
| 4 | Set View Transform to "Filmic" | Setting applied |
| 5 | Set Action to "Create & Open Setup" | |
| 6 | Click OK | New Blender instance opens |
| 7 | Verify VSE setup | Image strip present, correct frame range |
| 8 | Check render settings | Codec, FPS, resolution correct |
| 9 | Render animation (Ctrl+F12) | Video renders successfully |

### T3: Alpha Channel Preservation (WebM)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select alpha sequence folder | Path set |
| 2 | Choose "VP9 / WebM" codec | Alpha option enabled |
| 3 | Enable "Preserve Transparency" | Checkbox checked |
| 4 | Use FFmpeg encoder | |
| 5 | Click OK and wait | Video created |
| 6 | Open resulting WebM | Transparency preserved |
| 7 | Test in video editor | Alpha channel visible |

### T4: Alpha Channel Preservation (ProRes)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select alpha sequence folder | |
| 2 | Choose "ProRes / MOV" codec | Alpha option enabled |
| 3 | Enable "Preserve Transparency" | |
| 4 | Use FFmpeg encoder | |
| 5 | Convert | MOV file created |
| 6 | Open in video editor | Alpha channel intact |

### T5: Cancellation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start converting large sequence (100+ frames) | Progress shows |
| 2 | Click "Cancel" button | "Cancellation requested" message |
| 3 | Wait 2-3 seconds | Process terminates |
| 4 | Verify state | Panel shows "Cancelled", can start new conversion |

### T6: Error Handling - No Sequence Found

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enter path to empty folder | |
| 2 | Click OK | Error: "No valid image sequence found" |
| 3 | Verify state | Can try again with different path |

### T7: Error Handling - FFmpeg Not Found

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Temporarily rename/hide FFmpeg | |
| 2 | Select FFmpeg encoder | "FFmpeg not found" warning shows |
| 3 | Try to convert | Error message about missing FFmpeg |
| 4 | Switch to Blender encoder | Conversion works |

### T8: Automatic Versioning

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Convert sequence | Creates video_v001.mp4 |
| 2 | Convert same sequence again | Creates video_v002.mp4 |
| 3 | Convert third time | Creates video_v003.mp4 |
| 4 | Verify all files exist | No overwrites occurred |

### T9: All Codec Tests

For each codec, test with MEDIUM quality:

| Codec | Extension | Key Check |
|-------|-----------|-----------|
| H.264 / MP4 | .mp4 | Plays in browser, widely compatible |
| VP9 / WebM | .webm | Plays in Chrome/Firefox |
| AV1 / WebM | .webm | Small file size (slow encoding) |
| ProRes / MOV | .mov | Opens in professional editors |

### T10: Quality Level Tests (H.264)

| Quality | Expected CRF | File Size |
|---------|--------------|-----------|
| LOWEST | 28 | Smallest |
| LOW | 24 | Small |
| MEDIUM | 20 | Balanced |
| HIGH | 16 | Large |
| HIGHEST | 12 | Largest |

### T11: Frame Rate Tests

| FPS | Test |
|-----|------|
| 24 | Standard film |
| 30 | Standard video |
| 60 | High frame rate |
| 120 | Maximum supported |

### T12: Cross-Platform FFmpeg Detection (if applicable)

**Windows paths to check:**
- `C:\ffmpeg\bin\ffmpeg.exe`
- `C:\Program Files\ffmpeg\bin\ffmpeg.exe`
- Scoop: `~\scoop\shims\ffmpeg.exe`
- PATH

**macOS paths to check:**
- `/usr/local/bin/ffmpeg`
- `/opt/homebrew/bin/ffmpeg` (Apple Silicon)
- `/opt/local/bin/ffmpeg` (MacPorts)

**Linux paths to check:**
- `/usr/bin/ffmpeg`
- `/usr/local/bin/ffmpeg`
- `/snap/bin/ffmpeg`

## Regression Checklist

Before each release, verify all items:

- [ ] Addon enables without errors
- [ ] FFmpeg encoder works (if FFmpeg installed)
- [ ] Blender VSE encoder works
- [ ] All codecs produce valid output (H.264, VP9, AV1, ProRes)
- [ ] Alpha channel preserved with WebM
- [ ] Alpha channel preserved with ProRes
- [ ] Cancellation terminates process cleanly
- [ ] Error messages display correctly
- [ ] Progress monitoring updates in real-time
- [ ] File size displays correctly during encoding
- [ ] Elapsed time displays correctly
- [ ] Versioning prevents overwrites
- [ ] Panel UI renders correctly in all states
- [ ] "Open Video" button works
- [ ] "Open Folder" button works
- [ ] Reset/Try Again button works
- [ ] Color management settings apply (Blender encoder)
- [ ] Quality settings affect output

## Automated Test Suite

Run the pytest test suite for unit tests:

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html
```

## Reporting Issues

When reporting bugs, include:
1. Blender version
2. Operating system
3. FFmpeg version (if applicable)
4. Steps to reproduce
5. Expected vs actual behavior
6. Error messages from Blender's console
