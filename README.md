# Image Sequence to Video - Blender Addon

![Image Sequence to Video Banner](screenshots/Gumroad%20Banner.png)

An addon to speed up the rendering workflow where image sequences of rendered frames can be converted to video within the same Blender file you're working on, without any setup required.

![Blender](https://img.shields.io/badge/Blender-5.0%2B-orange)
![License](https://img.shields.io/badge/License-GPL--3.0-blue)
![Version](https://img.shields.io/badge/Version-1.0-green)

## What It Does

The addon reads your render framerate, resolution, and render output folder, then presents quick options for video encoding. It can use FFmpeg if installed, or launch a headless Blender process and render using Blender's own video encoder.

The addon mimics Blender's native video rendering and can preserve alpha channel for compatible formats. It's useful for working with rendered image frames and quickly converting them to videos to share or use.

![Main Panel](screenshots/Properties%20panel.png)

## Installation

1. Download the latest release (the `image_sequence_to_video` folder as a zip)
2. Open Blender and go to **Edit > Preferences > Add-ons**
3. Click **Install...** and select the downloaded zip file
4. Enable the addon by checking the checkbox

## Usage

Access the addon from:
- **Render Properties** panel (camera icon) > **Image Sequence to Video** section
- **Render** menu > **Image Sequence to Video**

![Render Menu Access](screenshots/Render%20button.png)

Click **Convert Image Sequence**, browse to your image sequence (select any file in the sequence), configure settings, and convert.

### FFmpeg Encoder (Fast)

When FFmpeg is installed and detected, you can use it for direct, fast encoding.

![FFmpeg Interface](screenshots/ffmpeg%20interface.png)

### Blender Encoder (Full Control)

Use Blender's Video Sequence Editor for encoding when you need color management options or don't have FFmpeg installed.

![Blender Interface](screenshots/Blender%20intreface.png)

### Conversion Progress

The panel shows real-time progress during conversion.

![Converting Status](screenshots/properties%20converting%20status.png)

### Completion

When done, quickly open the video or output folder directly from the panel.

![Conversion Complete](screenshots/Properties%20coversion%20completed.png)

## Features

- **Dual Encoder Support**: FFmpeg for speed, Blender VSE for full control
- **Codecs**: H.264/MP4, VP9/WebM, AV1/WebM, ProRes/MOV
- **Auto-detection**: Reads your scene's framerate and render output path
- **Alpha preservation**: WebM and ProRes formats support transparency
- **Output versioning**: Never overwrites existing files
- **Color management**: View transform, look modifiers, exposure/gamma (Blender mode)
- **Cross-platform**: Windows, macOS, Linux


## File Structure

After conversion, files are organized as:
```
your_render_folder/
├── frame_0001.png
├── frame_0002.png
├── ...
├── videos/
│   └── frame_v001.mp4
└── setup_files/
    └── frame_v001_setup.blend
```

## Requirements

- **Blender 5.0** or later
- **FFmpeg** (optional, for fast encoding)
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

## Troubleshooting

**FFmpeg not found**: Install FFmpeg and add it to your system PATH, or use the Blender encoder.

**Conversion seems stuck**: Check the System Console (**Window > Toggle System Console**) for progress details.

**Alpha not preserved**: Use VP9/WebM or ProRes codec and enable "Preserve Transparency".

## License

GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
