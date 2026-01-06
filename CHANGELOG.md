# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2024-12-28

### Added
- Dual encoder support: FFmpeg (fast) and Blender VSE (full control)
- AV1 codec support for best compression
- ProRes codec with alpha channel preservation
- Color management override for Blender VSE mode (view transform, look, exposure, gamma)
- Automatic output versioning to prevent file overwrites (v001, v002, etc.)
- Real-time progress monitoring with file size and elapsed time display
- Cross-platform FFmpeg path detection (Windows, macOS, Linux)
- Status file fallback for robust script communication
- Cancel button to stop conversions in progress

### Changed
- Improved Blender 5.0+ API compatibility (sequences -> strips)
- Enhanced error handling with detailed logging
- Better subprocess management to prevent hanging on Windows

### Fixed
- Windows console window hiding for background processes
- FFmpeg pipe buffer overflow causing hangs (now uses DEVNULL)
- Status parsing reliability with JSON fallback

## [2.3.0] - 2024-11-15

### Added
- VP9/WebM codec support with transparency
- Quality presets (Lowest to Highest)
- Frame rate configuration (1-120 fps)

### Changed
- Improved image sequence detection algorithm
- Better natural sorting for numbered files

## [2.2.0] - 2024-10-01

### Added
- Background rendering with progress monitoring
- Output folder quick access buttons

### Fixed
- Path handling for sequences with spaces
- Cross-platform path normalization

## [2.1.0] - 2024-08-15

### Added
- H.264/MP4 codec support
- Basic quality settings

### Changed
- Moved panel to Render properties

## [2.0.0] - 2024-07-01

### Added
- Complete rewrite with modern architecture
- Blender VSE integration
- Setup file creation (.blend)

### Changed
- Minimum Blender version: 5.0.0
- New UI in Render properties panel

## [1.0.0] - 2024-05-01

### Added
- Initial release
- Basic image sequence to video conversion
- PNG, JPG, TIFF, EXR, BMP support
