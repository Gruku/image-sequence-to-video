bl_info = {
    "name": "Image Sequence to Video",
    "author": "Claude",
    "version": (2, 4),
    "blender": (5, 0, 0),
    "location": "Render > Image Sequence to Video",
    "description": "Convert rendered image sequences to video files (FFmpeg or Blender)",
    "category": "Render",
}

import bpy
import os
import re
import subprocess
import tempfile
import time
import uuid
from bpy.props import (
    StringProperty,
    EnumProperty,
    IntProperty,
    BoolProperty,
    FloatProperty,
    PointerProperty,
)
import platform
import shutil


# =============================================================================
# Addon Preferences
# =============================================================================

class ImageSequenceToVideoPreferences(bpy.types.AddonPreferences):
    """Addon preferences for FFmpeg configuration."""
    bl_idname = __name__

    ffmpeg_path: StringProperty(
        name="FFmpeg Path",
        description="Path to FFmpeg executable. Leave empty for auto-detection",
        default="",
        subtype='FILE_PATH'
    )

    def draw(self, context):
        layout = self.layout

        # FFmpeg path setting
        box = layout.box()
        box.label(text="FFmpeg Configuration", icon='SETTINGS')

        row = box.row()
        row.prop(self, "ffmpeg_path", text="FFmpeg Path")

        # Show detection status
        ffmpeg_location = find_ffmpeg()
        if ffmpeg_location:
            box.label(text=f"FFmpeg found: {ffmpeg_location}", icon='CHECKMARK')
        else:
            box.label(text="FFmpeg not found", icon='ERROR')
            box.label(text="Download from: https://ffmpeg.org/download.html")

        # Help text
        box.separator()
        box.label(text="Leave path empty for auto-detection, or set manually if FFmpeg is not found.")


def get_addon_preferences():
    """Get addon preferences safely."""
    try:
        return bpy.context.preferences.addons[__name__].preferences
    except (KeyError, AttributeError):
        return None


# =============================================================================
# Global State Management
# =============================================================================

class RenderProcessManager:
    """Centralized manager for tracking background render processes."""
    
    _processes = {}
    _output_files = {}
    _start_times = {}
    
    @classmethod
    def add(cls, render_id, process, output_file):
        cls._processes[render_id] = process
        cls._output_files[render_id] = output_file
        cls._start_times[render_id] = time.time()
    
    @classmethod
    def get_process(cls, render_id):
        return cls._processes.get(render_id)
    
    @classmethod
    def get_output_file(cls, render_id):
        return cls._output_files.get(render_id)
    
    @classmethod
    def get_start_time(cls, render_id):
        return cls._start_times.get(render_id, 0)
    
    @classmethod
    def remove(cls, render_id):
        cls._processes.pop(render_id, None)
        cls._output_files.pop(render_id, None)
        cls._start_times.pop(render_id, None)
    
    @classmethod
    def is_running(cls, render_id):
        proc = cls._processes.get(render_id)
        if proc is None:
            return False
        return proc.poll() is None
    
    @classmethod
    def terminate(cls, render_id):
        """Terminate a running render process."""
        proc = cls._processes.get(render_id)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    
    @classmethod
    def cleanup_all(cls):
        """Terminate all running processes."""
        for render_id in list(cls._processes.keys()):
            cls.terminate(render_id)
            cls.remove(render_id)


# =============================================================================
# Utility Functions
# =============================================================================

def find_image_sequence(path):
    """
    Find and analyze image sequences at the given path.
    
    Args:
        path: Path to a directory, file within a sequence, or filename prefix
        
    Returns:
        Tuple of (directory, sorted_file_list) or (None, []) if not found
    """
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.exr', '.bmp'}
    
    # Handle the case where path ends with a filename prefix
    if path and not os.path.exists(path):
        parent_dir = os.path.dirname(path)
        if os.path.isdir(parent_dir):
            filename_prefix = os.path.basename(path)
            matching_files = []
            
            # Build pattern to match prefix followed by digits and image extension
            try:
                pattern = re.compile(
                    rf"^{re.escape(filename_prefix)}\d+\.({'|'.join(ext[1:] for ext in IMAGE_EXTENSIONS)})$",
                    re.IGNORECASE
                )
                for f in os.listdir(parent_dir):
                    if pattern.match(f):
                        matching_files.append(f)
                        
                if matching_files:
                    return parent_dir, sorted(matching_files, key=_natural_sort_key)
            except re.error:
                pass
    
    # If path is a file, extract directory and pattern
    if os.path.isfile(path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        base, ext = os.path.splitext(filename)
        
        if ext.lower() not in IMAGE_EXTENSIONS:
            return None, []
        
        # Extract base name by removing trailing numbers
        pattern_match = re.search(r'(.*?)(\d+)$', base)
        if pattern_match:
            base_name = pattern_match.group(1)
            files = []
            
            try:
                pattern = re.compile(rf"^{re.escape(base_name)}\d+{re.escape(ext)}$", re.IGNORECASE)
                for f in os.listdir(directory):
                    if pattern.match(f):
                        files.append(f)
                return directory, sorted(files, key=_natural_sort_key)
            except re.error:
                pass
    
    # If path is a directory, look for image sequences
    elif os.path.isdir(path):
        directory = path
        try:
            all_files = os.listdir(directory)
        except OSError:
            return None, []
        
        # Group files by potential sequences
        sequences = {}
        for filename in all_files:
            base, ext = os.path.splitext(filename)
            if ext.lower() not in IMAGE_EXTENSIONS:
                continue
            
            # Try different naming patterns
            patterns = [
                (r'(.*?)(\d+)$', lambda m: m.group(1)),   # name0001 or name_0001
                (r'(.*?)\.(\d+)$', lambda m: m.group(1)), # name.0001
            ]
            
            for pat, extract_base in patterns:
                match = re.search(pat, base)
                if match:
                    base_name = extract_base(match)
                    if base_name not in sequences:
                        sequences[base_name] = []
                    sequences[base_name].append(filename)
                    break
        
        # Find the sequence with the most files
        if sequences:
            base_name = max(sequences, key=lambda k: len(sequences[k]))
            return directory, sorted(sequences[base_name], key=_natural_sort_key)
    
    return None, []


def _natural_sort_key(s):
    """Sort key for natural ordering of numbered files."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def check_for_alpha_channel(image_path):
    """Check if the image format commonly supports alpha channels."""
    ext = os.path.splitext(image_path)[1].lower()
    alpha_formats = {'.png', '.exr', '.tiff', '.tif'}
    return ext in alpha_formats


def format_time(seconds):
    """Format seconds into a human-readable string."""
    # Handle edge cases
    if seconds < 0:
        seconds = 0
    if seconds > 86400 * 7:  # More than a week - clearly wrong
        return "..."
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def format_size(bytes_size):
    """Format bytes into a human-readable string."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / 1024 / 1024:.2f} MB"


def find_ffmpeg():
    """
    Find FFmpeg executable on the system.

    Checks in order:
    1. Manual path from addon preferences
    2. shutil.which() (PATH lookup)
    3. 'where' command on Windows
    4. Common installation paths

    Returns:
        Path to FFmpeg executable or None if not found
    """
    def verify_ffmpeg(path):
        """Verify that a path points to a working FFmpeg executable."""
        if not path or not os.path.isfile(path):
            return False
        try:
            kwargs = {'capture_output': True, 'text': True, 'timeout': 5}
            if platform.system() == "Windows":
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run([path, '-version'], **kwargs)
            return result.returncode == 0
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return False

    # 1. Check manual path from addon preferences
    prefs = get_addon_preferences()
    if prefs and prefs.ffmpeg_path:
        manual_path = bpy.path.abspath(prefs.ffmpeg_path)
        if verify_ffmpeg(manual_path):
            return manual_path

    # 2. Use shutil.which() - most reliable cross-platform PATH lookup
    which_result = shutil.which('ffmpeg')
    if which_result and verify_ffmpeg(which_result):
        return which_result

    # 3. On Windows, try 'where' command as fallback
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ['where', 'ffmpeg'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                # 'where' can return multiple paths, take the first valid one
                for line in result.stdout.strip().split('\n'):
                    path = line.strip()
                    if path and verify_ffmpeg(path):
                        return path
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            pass

    # 4. Check common installation paths
    common_paths = []

    if platform.system() == "Windows":
        # Get common base paths
        program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        user_home = os.path.expanduser('~')

        common_paths = [
            # Standard locations
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\ffmpeg.exe",
            os.path.join(program_files, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(program_files, 'ffmpeg', 'ffmpeg.exe'),
            os.path.join(program_files_x86, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            # User directory
            os.path.join(user_home, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(user_home, 'ffmpeg', 'ffmpeg.exe'),
            # Scoop (package manager)
            os.path.join(user_home, 'scoop', 'shims', 'ffmpeg.exe'),
            os.path.join(user_home, 'scoop', 'apps', 'ffmpeg', 'current', 'bin', 'ffmpeg.exe'),
            # Chocolatey
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            # Winget / MSIX
            os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages', 'Gyan.FFmpeg_*', 'ffmpeg-*', 'bin', 'ffmpeg.exe') if local_app_data else '',
            # ImageMagick bundle
            os.path.join(program_files, 'ImageMagick*', 'ffmpeg.exe'),
            # Video editors that bundle FFmpeg
            os.path.join(program_files, 'Shotcut', 'ffmpeg.exe'),
            os.path.join(local_app_data, 'Programs', 'ffmpeg', 'bin', 'ffmpeg.exe') if local_app_data else '',
        ]
    elif platform.system() == "Darwin":  # macOS
        common_paths = [
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",  # Apple Silicon Homebrew
            "/opt/local/bin/ffmpeg",     # MacPorts
            os.path.expanduser("~/bin/ffmpeg"),
            "/Applications/FFmpeg/ffmpeg",
        ]
    else:  # Linux
        common_paths = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
            os.path.expanduser("~/.local/bin/ffmpeg"),
            os.path.expanduser("~/bin/ffmpeg"),
            "/opt/ffmpeg/bin/ffmpeg",
        ]

    # Handle glob patterns in paths (for winget, imagemagick, etc.)
    import glob
    expanded_paths = []
    for path in common_paths:
        if path and ('*' in path):
            expanded_paths.extend(glob.glob(path))
        elif path:
            expanded_paths.append(path)

    for path in expanded_paths:
        if os.path.isfile(path):
            return path

    return None


def get_ffmpeg_codec_args(codec, quality, preserve_alpha=False):
    """
    Get FFmpeg arguments for the specified codec and quality.
    
    Returns:
        Tuple of (output_extension, codec_args_list)
    """
    # CRF values for quality levels (lower = better quality, bigger file)
    crf_map = {
        'LOWEST': 28,
        'LOW': 24,
        'MEDIUM': 20,
        'HIGH': 16,
        'HIGHEST': 12,
    }
    crf = crf_map.get(quality, 20)
    
    # Bitrate for codecs that don't support CRF well
    bitrate_map = {
        'LOWEST': '2M',
        'LOW': '4M',
        'MEDIUM': '8M',
        'HIGH': '15M',
        'HIGHEST': '30M',
    }
    bitrate = bitrate_map.get(quality, '8M')
    
    if codec == 'H264':
        return 'mp4', [
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', str(crf),
            '-pix_fmt', 'yuv420p',  # Compatibility
            '-movflags', '+faststart',  # Web streaming optimization
        ]
    
    elif codec == 'WEBM':
        pix_fmt = 'yuva420p' if preserve_alpha else 'yuv420p'
        return 'webm', [
            '-c:v', 'libvpx-vp9',
            '-crf', str(crf),
            '-b:v', '0',  # Use CRF mode
            '-pix_fmt', pix_fmt,
            '-row-mt', '1',  # Multi-threaded
        ]
    
    elif codec == 'AV1':
        return 'webm', [
            '-c:v', 'libaom-av1',
            '-crf', str(crf),
            '-b:v', '0',
            '-pix_fmt', 'yuv420p',
            '-cpu-used', '4',  # Speed/quality tradeoff (0-8, higher=faster)
            '-row-mt', '1',
        ]
    
    elif codec == 'PRORES':
        # ProRes quality profiles
        prores_profile = {
            'LOWEST': '0',   # Proxy
            'LOW': '1',      # LT
            'MEDIUM': '2',   # Standard
            'HIGH': '3',     # HQ
            'HIGHEST': '4',  # 4444
        }
        profile = prores_profile.get(quality, '2')
        return 'mov', [
            '-c:v', 'prores_ks',
            '-profile:v', profile,
            '-pix_fmt', 'yuva444p10le' if preserve_alpha else 'yuv422p10le',
        ]
    
    # Default fallback to H264
    return 'mp4', ['-c:v', 'libx264', '-crf', str(crf), '-pix_fmt', 'yuv420p']


def get_versioned_output_path(output_dir, base_name, extension):
    """
    Get a versioned output path that doesn't exist yet.
    
    Returns:
        Full path to the output file
    """
    version = 1
    max_versions = 999
    
    while version <= max_versions:
        output_file = os.path.join(output_dir, f"{base_name}_v{version:03d}.{extension}")
        if not os.path.exists(output_file):
            return output_file
        version += 1
    
    # Fallback with timestamp
    import time
    timestamp = int(time.time())
    return os.path.join(output_dir, f"{base_name}_{timestamp}.{extension}")


# =============================================================================
# Script Generation
# =============================================================================

def generate_video_setup_script(image_dir, files, output_dir, setup_dir, fps=24, 
                                quality='MEDIUM', codec='H264', preserve_alpha=False,
                                view_transform='Standard', look='None', 
                                exposure=0.0, gamma=1.0, status_file=None):
    """
    Generate Python script to set up VSE and render settings.
    
    This script will be executed in a background Blender instance.
    """
    if not files:
        return None
    
    # Normalize paths for cross-platform compatibility
    image_dir = image_dir.replace('\\', '/')
    output_dir = output_dir.replace('\\', '/')
    setup_dir = setup_dir.replace('\\', '/')
    
    first_image = os.path.join(image_dir, files[0]).replace('\\', '/')
    
    # Determine base name for output file
    directory_name = os.path.basename(image_dir)
    if not directory_name or directory_name in (".", ".."):
        directory_name = "rendered_video"

    file_base = os.path.splitext(files[0])[0]
    file_base = re.sub(r'\d+$', '', file_base)  # Remove trailing numbers
    file_base = file_base.strip('_- ')  # Remove trailing separators (same as FFmpeg path)
    base_name = file_base if file_base else directory_name
    
    # Quality mapping
    quality_settings = {
        'LOWEST':  {'crf': 'LOWEST',  'bitrate': 2000},
        'LOW':     {'crf': 'LOW',     'bitrate': 4000},
        'MEDIUM':  {'crf': 'MEDIUM',  'bitrate': 6000},
        'HIGH':    {'crf': 'HIGH',    'bitrate': 10000},
        'HIGHEST': {'crf': 'HIGHEST', 'bitrate': 20000},
    }
    
    q = quality_settings[quality]
    
    # Codec configurations - note: these will be inserted inside main() so need proper indentation
    codec_configs = {
        'H264': {
            'extension': 'mp4',
            'setup': f'''    bpy.context.scene.render.ffmpeg.format = 'MPEG4'
    bpy.context.scene.render.ffmpeg.codec = 'H264'
    bpy.context.scene.render.ffmpeg.constant_rate_factor = '{q["crf"]}'
    bpy.context.scene.render.ffmpeg.gopsize = 18
    bpy.context.scene.render.ffmpeg.use_max_b_frames = False
    bpy.context.scene.render.ffmpeg.max_b_frames = 0'''
        },
        'WEBM': {
            'extension': 'webm',
            'setup': f'''    bpy.context.scene.render.ffmpeg.format = 'WEBM'
    bpy.context.scene.render.ffmpeg.codec = 'WEBM'
    bpy.context.scene.render.ffmpeg.video_bitrate = {q["bitrate"]}
    bpy.context.scene.render.ffmpeg.minrate = 0
    bpy.context.scene.render.ffmpeg.maxrate = 0
    bpy.context.scene.render.ffmpeg.buffersize = 0
    bpy.context.scene.render.ffmpeg.gopsize = 250
    bpy.context.scene.render.ffmpeg.use_autosplit = False'''
        },
        'AV1': {
            'extension': 'webm',
            'setup': f'''    bpy.context.scene.render.ffmpeg.format = 'WEBM'
    bpy.context.scene.render.ffmpeg.codec = 'AV1'
    bpy.context.scene.render.ffmpeg.video_bitrate = {q["bitrate"]}
    bpy.context.scene.render.ffmpeg.gopsize = 250'''
        },
        'PRORES': {
            'extension': 'mov',
            'setup': '''    bpy.context.scene.render.ffmpeg.format = 'QUICKTIME'
    bpy.context.scene.render.ffmpeg.codec = 'PRORES' '''
        },
    }
    
    config = codec_configs.get(codec, codec_configs['H264'])
    file_extension = config['extension']
    codec_setup = config['setup']
    
    # Create file list string for script
    files_list_str = repr(files)
    
    # Handle status file path (escape for string literal)
    status_file_path = status_file.replace('\\', '/') if status_file else ""
    
    script = f'''
import bpy
import os
import sys

print("=" * 60)
print("Image Sequence to Video - Setup Script")
print("=" * 60)

# Status file for fallback communication
STATUS_FILE = "{status_file_path}"

def main():
    # Configuration
    IMAGE_DIR = "{image_dir}"
    FILES = {files_list_str}
    OUTPUT_DIR = "{output_dir}"
    SETUP_DIR = "{setup_dir}"
    BASE_NAME = "{base_name}"
    FPS = {fps}
    PRESERVE_ALPHA = {preserve_alpha}

    print(f"Image directory: {{IMAGE_DIR}}")
    print(f"Number of frames: {{len(FILES)}}")
    print(f"FPS: {{FPS}}")
    print(f"Codec: {codec}")
    print(f"Preserve alpha: {{PRESERVE_ALPHA}}")
    print(f"Output directory: {{OUTPUT_DIR}}")
    print(f"Setup directory: {{SETUP_DIR}}")
    print(f"Base name: {{BASE_NAME}}")
    print(f"Status file: {{STATUS_FILE}}")
    
    # Verify source directory exists
    if not os.path.isdir(IMAGE_DIR):
        print(f"ERROR: Image directory does not exist: {{IMAGE_DIR}}")
        sys.exit(1)
    
    # Verify at least one source file exists
    first_image_path = os.path.join(IMAGE_DIR, FILES[0])
    if not os.path.isfile(first_image_path):
        print(f"ERROR: First image not found: {{first_image_path}}")
        sys.exit(1)
    
    print(f"First image verified: {{first_image_path}}")

    # Clear default startup
    print("Creating fresh Blender session...")
    try:
        bpy.ops.wm.read_homefile(use_empty=True)
    except Exception as e:
        print(f"Warning: Could not read home file: {{e}}")

    # Set up Video Editing workspace if available
    if 'Video Editing' in bpy.data.workspaces:
        bpy.context.window.workspace = bpy.data.workspaces['Video Editing']
    else:
        # Set up sequencer manually
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.type = 'SEQUENCE_EDITOR'
                break

    # Ensure sequencer view
    for area in bpy.context.screen.areas:
        if area.type == 'SEQUENCE_EDITOR':
            for space in area.spaces:
                if space.type == 'SEQUENCE_EDITOR':
                    space.view_type = 'SEQUENCER'
                    break
            break

    # Create sequence editor and add image strip
    print("Creating sequence editor...")
    
    # Ensure sequence editor exists
    if not bpy.context.scene.sequence_editor:
        bpy.context.scene.sequence_editor_create()
    
    seq_editor = bpy.context.scene.sequence_editor
    
    # Build the files list for the operator
    files_for_op = [{{"name": f}} for f in sorted(FILES)]
    
    print(f"Adding image strip with {{len(FILES)}} frames...")
    print(f"Directory: {{IMAGE_DIR}}")
    print(f"First file: {{FILES[0]}}")
    
    image_strip = None
    
    # Method 1: Try the new Blender 5.0 API (strips instead of sequences)
    try:
        if hasattr(seq_editor, 'strips'):
            strips = seq_editor.strips
            print("Using Blender 5.0+ API (.strips)")
        elif hasattr(seq_editor, 'sequences'):
            strips = seq_editor.sequences
            print("Using legacy API (.sequences)")
        else:
            raise AttributeError("Cannot find strips or sequences attribute on sequence_editor")
        
        image_strip = strips.new_image(
            name="Image Sequence",
            filepath=first_image_path,
            channel=1,
            frame_start=1
        )
        
        # Add remaining frames
        for img_file in sorted(FILES)[1:]:
            image_strip.elements.append(img_file)
        
        print(f"Image strip created with {{len(image_strip.elements)}} frames")
        
    except Exception as api_error:
        print(f"Low-level API failed: {{api_error}}")
        print("Trying operator method...")
        
        # Method 2: Try operator (may fail in background mode without proper context)
        try:
            bpy.ops.sequencer.image_strip_add(
                directory=IMAGE_DIR + os.sep,
                files=files_for_op,
                frame_start=1,
                frame_end=len(FILES),
                channel=1,
                relative_path=False
            )
            print("Image strip added successfully via operator")
            
            # Get the strip that was just added
            if hasattr(seq_editor, 'strips'):
                image_strip = seq_editor.strips[-1] if seq_editor.strips else None
            elif hasattr(seq_editor, 'sequences'):
                image_strip = seq_editor.sequences[-1] if seq_editor.sequences else None
                
        except Exception as op_error:
            print(f"ERROR: All methods failed to create image strip")
            print(f"API error: {{api_error}}")
            print(f"Operator error: {{op_error}}")
            print(f"Available attributes on sequence_editor: {{dir(seq_editor)}}")
            sys.exit(1)
    
    if image_strip is None:
        print("ERROR: Image strip was not created")
        sys.exit(1)

    # Set timeline
    sequence_length = len(FILES)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = sequence_length

    print(f"Timeline: frames 1-{{sequence_length}}")

    # Configure render settings
    bpy.context.scene.render.fps = FPS
    
    # Blender 5.0+ requires setting media_type before file_format for video output
    try:
        # New Blender 5.0+ API: must set media_type to VIDEO before setting FFMPEG
        if hasattr(bpy.context.scene.render.image_settings, 'media_type'):
            bpy.context.scene.render.image_settings.media_type = 'VIDEO'
            print("Set media_type to VIDEO (Blender 5.0+ API)")
        bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
    except TypeError as e:
        # Fallback: Try setting media_type if the error is about FFMPEG not being found
        print(f"Initial file_format set failed: {{e}}")
        if hasattr(bpy.context.scene.render.image_settings, 'media_type'):
            bpy.context.scene.render.image_settings.media_type = 'VIDEO'
            bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
            print("Retry with media_type=VIDEO succeeded")

    # Apply codec settings
    print("Applying codec settings...")
{codec_setup}
    print("Codec settings applied")

    # Handle alpha channel
    try:
        temp_img = bpy.data.images.load(first_image_path)
        has_alpha = temp_img.depth in (32, 128)
        print(f"Image depth: {{temp_img.depth}}, has alpha: {{has_alpha}}")
        
        if has_alpha and PRESERVE_ALPHA:
            bpy.context.scene.render.film_transparent = True
            if bpy.context.scene.render.ffmpeg.format == 'WEBM':
                bpy.context.scene.render.image_settings.color_mode = 'RGBA'
            print("Alpha channel will be preserved")
        else:
            bpy.context.scene.render.film_transparent = False
            bpy.context.scene.render.image_settings.color_mode = 'RGB'
            print("No alpha channel preservation")
        
        # Get image dimensions
        width, height = temp_img.size
        print(f"Detected resolution: {{width}}x{{height}}")
        bpy.data.images.remove(temp_img)
    except Exception as e:
        print(f"Warning: Could not analyze first image: {{e}}")
        width, height = 1920, 1080
        bpy.context.scene.render.film_transparent = False
        bpy.context.scene.render.image_settings.color_mode = 'RGB'

    # Set resolution
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.context.scene.render.resolution_percentage = 100

    # Color management
    try:
        bpy.context.scene.view_settings.view_transform = '{view_transform}'
        bpy.context.scene.view_settings.look = '{look}'
        bpy.context.scene.view_settings.exposure = {exposure}
        bpy.context.scene.view_settings.gamma = {gamma}
        print("Color management configured")
    except Exception as e:
        print(f"Warning: Could not set color management: {{e}}")

    # Create directories
    print(f"Creating output directory: {{OUTPUT_DIR}}")
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Cannot create output directory: {{e}}")
        sys.exit(1)
        
    print(f"Creating setup directory: {{SETUP_DIR}}")
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Cannot create setup directory: {{e}}")
        sys.exit(1)

    # Determine output filename with versioning
    # Check both video file AND blend file to keep versions in sync
    version = 1
    max_versions = 999
    while version <= max_versions:
        output_file = os.path.join(OUTPUT_DIR, f"{{BASE_NAME}}_v{{version:03d}}.{file_extension}")
        blend_file_path = os.path.join(SETUP_DIR, f"{{BASE_NAME}}_v{{version:03d}}_setup.blend")
        
        video_exists = os.path.exists(output_file)
        blend_exists = os.path.exists(blend_file_path)
        
        print(f"Checking v{{version:03d}}: video={{video_exists}}, blend={{blend_exists}}")
        
        # Use this version if NEITHER file exists
        if not video_exists and not blend_exists:
            break
        version += 1
    
    if version > max_versions:
        print(f"ERROR: Too many versions exist (max {{max_versions}}), please clean up old files")
        sys.exit(1)

    print(f"Using version: v{{version:03d}}")
    print(f"Output video path: {{output_file}}")
    print(f"Setup blend path: {{blend_file_path}}")

    bpy.context.scene.render.filepath = output_file

    # Save blend file
    print(f"Saving blend file...")
    try:
        bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)
    except Exception as e:
        print(f"ERROR: Failed to save blend file: {{e}}")
        sys.exit(1)
    
    # Verify file was created
    if not os.path.exists(blend_file_path):
        print(f"ERROR: Blend file was not created at expected path: {{blend_file_path}}")
        # List directory contents for debugging
        if os.path.exists(SETUP_DIR):
            print(f"Setup directory contents: {{os.listdir(SETUP_DIR)}}")
        sys.exit(1)
    
    file_size = os.path.getsize(blend_file_path)
    print(f"Blend file created successfully ({{file_size}} bytes)")

    print("=" * 60)
    print(f"Setup complete. Blend file saved to {{blend_file_path}}", flush=True)
    print(f"Video will be rendered to {{output_file}}", flush=True)
    print("=" * 60, flush=True)
    
    # Write status to JSON file as fallback for stdout parsing
    if STATUS_FILE:
        try:
            import json
            status_data = {{
                "blend_file": blend_file_path,
                "output_file": output_file,
                "success": True
            }}
            with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
                json.dump(status_data, sf)
            print(f"Status written to: {{STATUS_FILE}}", flush=True)
        except Exception as e:
            print(f"Warning: Could not write status file: {{e}}", flush=True)

# Run main function with error handling
if __name__ == "__main__":
    try:
        main()
        # Ensure all output is flushed
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
    except SystemExit:
        raise  # Re-raise SystemExit to preserve exit codes
    except Exception as e:
        print(f"FATAL ERROR: {{e}}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
'''
    
    return script


# =============================================================================
# Property Group
# =============================================================================

class ImageSequenceToVideoProperties(bpy.types.PropertyGroup):
    """Properties for tracking render state and conversion settings."""

    # Render state tracking
    render_state: EnumProperty(
        name="Render State",
        items=[
            ('IDLE', "Idle", "Ready for new conversion"),
            ('RENDERING', "Rendering", "Conversion in progress"),
            ('FINISHED', "Finished", "Conversion completed"),
            ('ERROR', "Error", "Error occurred"),
            ('CANCELLED', "Cancelled", "Conversion was cancelled"),
        ],
        default='IDLE'
    )

    progress_message: StringProperty(
        name="Progress Message",
        default=""
    )

    output_file: StringProperty(
        name="Output File",
        default=""
    )

    setup_file: StringProperty(
        name="Setup File",
        default=""
    )

    start_time: FloatProperty(
        name="Start Time",
        default=0.0
    )

    render_id: StringProperty(
        name="Render ID",
        default=""
    )

    frame_count: IntProperty(
        name="Frame Count",
        default=0
    )

    # Conversion settings (stored here so execute operator can access them)
    sequence_path: StringProperty(
        name="Image Sequence",
        description="Path to image sequence (directory or any file in the sequence)",
        default="",
        subtype='FILE_PATH'
    )

    fps: IntProperty(
        name="Frame Rate",
        description="Output video frame rate",
        default=24,
        min=1,
        max=120
    )

    quality: EnumProperty(
        name="Quality",
        items=[
            ('LOWEST', "Lowest", "Smallest file size, lower quality"),
            ('LOW', "Low", "Small file size"),
            ('MEDIUM', "Medium", "Balanced quality and size"),
            ('HIGH', "High", "High quality"),
            ('HIGHEST', "Highest", "Maximum quality, largest file"),
        ],
        default='MEDIUM'
    )

    codec: EnumProperty(
        name="Codec / Format",
        items=[
            ('H264', "H.264 / MP4", "Widely compatible, good compression"),
            ('WEBM', "VP9 / WebM", "Open format, supports transparency"),
            ('AV1', "AV1 / WebM", "Modern codec, best compression (slow)"),
            ('PRORES', "ProRes / MOV", "Professional editing, large files"),
        ],
        default='H264'
    )

    preserve_alpha: BoolProperty(
        name="Preserve Transparency",
        description="Keep alpha channel (requires VP9/WebM codec)",
        default=False
    )

    action: EnumProperty(
        name="Action",
        items=[
            ('RENDER', "Convert Now", "Create video immediately in background"),
            ('OPEN', "Create & Open Setup", "Create setup file and open in new Blender"),
            ('SETUP', "Create Setup Only", "Just create the .blend setup file"),
        ],
        default='RENDER'
    )

    encoder: EnumProperty(
        name="Encoder",
        items=[
            ('FFMPEG', "FFmpeg (Fast)", "Use FFmpeg directly - much faster"),
            ('BLENDER', "Blender (Full Control)", "Use Blender's VSE - slower but more options"),
        ],
        default='FFMPEG'
    )

    override_color_management: BoolProperty(
        name="Override Color Settings",
        description="Use custom color management instead of defaults",
        default=False
    )

    view_transform: EnumProperty(
        name="View Transform",
        items=[
            ('Standard', "Standard", "sRGB display"),
            ('Filmic', "Filmic", "High dynamic range"),
            ('AgX', "AgX", "Modern filmic look"),
            ('Raw', "Raw", "No transform"),
        ],
        default='Standard'
    )

    look: EnumProperty(
        name="Look",
        items=[
            ('None', "None", "No look modifier"),
            ('Very Low Contrast', "Very Low Contrast", ""),
            ('Low Contrast', "Low Contrast", ""),
            ('Medium Contrast', "Medium Contrast", ""),
            ('High Contrast', "High Contrast", ""),
            ('Very High Contrast', "Very High Contrast", ""),
        ],
        default='None'
    )

    exposure: FloatProperty(
        name="Exposure",
        default=0.0,
        min=-10.0,
        max=10.0,
        step=10
    )

    gamma: FloatProperty(
        name="Gamma",
        default=1.0,
        min=0.1,
        max=5.0,
        step=10
    )


# =============================================================================
# Operators
# =============================================================================

class RENDER_OT_image_sequence_to_video_check_progress(bpy.types.Operator):
    """Monitor video rendering progress in the background."""
    bl_idname = "render.image_sequence_to_video_check_progress"
    bl_label = "Check Video Rendering Progress"
    
    _timer = None
    render_id: StringProperty(default="")
    
    def modal(self, context, event):
        props = context.scene.image_sequence_to_video_props
        
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}
        
        if props.render_state not in ('RENDERING', 'CANCELLED'):
            return self.cancel(context)
        
        # Handle cancellation request
        if props.render_state == 'CANCELLED':
            RenderProcessManager.terminate(props.render_id)
            RenderProcessManager.remove(props.render_id)
            props.progress_message = "Conversion cancelled by user"
            self._redraw_ui(context)
            return self.cancel(context)
        
        output_file = props.output_file
        
        # Calculate elapsed time with protection against invalid start_time
        if props.start_time > 0:
            elapsed = time.time() - props.start_time
        else:
            elapsed = 0
        
        # Sanity check - if elapsed is negative or absurdly large, reset it
        if elapsed < 0 or elapsed > 86400 * 7:  # More than a week is clearly wrong
            elapsed = 0
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            size_str = format_size(file_size)
            time_str = format_time(elapsed)
            
            if RenderProcessManager.is_running(props.render_id):
                props.progress_message = f"Encoding: {size_str} | Time: {time_str}"
            else:
                # Process completed
                props.render_state = 'FINISHED'
                props.progress_message = f"Complete! Size: {size_str} | Time: {time_str}"
                RenderProcessManager.remove(props.render_id)
                self._redraw_ui(context)
                return self.cancel(context)
        else:
            # File doesn't exist yet
            if not RenderProcessManager.is_running(props.render_id):
                # Process ended without creating file = error
                props.render_state = 'ERROR'
                props.progress_message = "Render process ended without creating output"
                RenderProcessManager.remove(props.render_id)
                self._redraw_ui(context)
                return self.cancel(context)
            else:
                props.progress_message = f"Initializing... | Time: {format_time(elapsed)}"
        
        self._redraw_ui(context)
        return {'PASS_THROUGH'}
    
    def _redraw_ui(self, context):
        """Force UI redraw in Properties panel."""
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.tag_redraw()
    
    def execute(self, context):
        props = context.scene.image_sequence_to_video_props
        
        if props.render_state != 'RENDERING':
            return {'CANCELLED'}
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        return {'CANCELLED'}


class RENDER_OT_image_sequence_to_video_cancel(bpy.types.Operator):
    """Cancel the current video conversion."""
    bl_idname = "render.image_sequence_to_video_cancel"
    bl_label = "Cancel Conversion"
    bl_description = "Stop the current video conversion"
    
    def execute(self, context):
        props = context.scene.image_sequence_to_video_props
        
        if props.render_state == 'RENDERING':
            props.render_state = 'CANCELLED'
            self.report({'INFO'}, "Cancellation requested...")
        
        return {'FINISHED'}


class RENDER_OT_image_sequence_to_video_reset(bpy.types.Operator):
    """Reset the addon to idle state."""
    bl_idname = "render.image_sequence_to_video_reset"
    bl_label = "Reset State"
    bl_description = "Clear status and start fresh"

    def execute(self, context):
        props = context.scene.image_sequence_to_video_props
        props.render_state = 'IDLE'
        props.progress_message = ""
        props.output_file = ""
        props.setup_file = ""
        props.start_time = 0.0
        props.render_id = ""
        props.frame_count = 0
        return {'FINISHED'}


class RENDER_OT_image_sequence_to_video_execute(bpy.types.Operator):
    """Execute the conversion with settings from scene properties."""
    bl_idname = "render.image_sequence_to_video_execute"
    bl_label = "Execute Conversion"
    bl_description = "Start the video conversion"

    def execute(self, context):
        props = context.scene.image_sequence_to_video_props

        # If already rendering, just acknowledge
        if props.render_state == 'RENDERING':
            return {'FINISHED'}

        # Reset state
        props.render_state = 'IDLE'
        props.progress_message = ""
        props.output_file = ""
        props.setup_file = ""

        # Normalize and validate path
        path = bpy.path.abspath(props.sequence_path)
        directory, files = find_image_sequence(path)

        if not directory or not files:
            self.report({'ERROR'}, "No valid image sequence found at the specified path")
            props.render_state = 'ERROR'
            props.progress_message = "No image sequence found"
            return {'CANCELLED'}

        # Set up output directories
        parent_dir = os.path.dirname(directory)
        output_dir = os.path.join(parent_dir, "videos")
        setup_dir = os.path.join(parent_dir, "setup_files")

        try:
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(setup_dir, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Cannot create output directories: {e}")
            return {'CANCELLED'}

        # Handle codec/alpha compatibility
        codec = props.codec
        if props.preserve_alpha and codec not in ('WEBM', 'PRORES'):
            codec = 'WEBM'
            self.report({'INFO'}, "Using VP9/WebM for transparency support")

        # Branch based on encoder selection
        if props.encoder == 'FFMPEG':
            return self._execute_ffmpeg(context, directory, files, output_dir, codec, props)
        else:
            return self._execute_blender(context, directory, files, output_dir, setup_dir, codec, props)

    def _execute_ffmpeg(self, context, directory, files, output_dir, codec, props):
        """Execute conversion using FFmpeg directly."""

        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self.report({'ERROR'}, "FFmpeg not found. Please install FFmpeg or use Blender encoder.")
            props.render_state = 'ERROR'
            props.progress_message = "FFmpeg not found"
            return {'CANCELLED'}

        # Get output extension and codec args
        extension, codec_args = get_ffmpeg_codec_args(
            codec, props.quality, props.preserve_alpha
        )

        # Determine base name from directory or first file
        directory_name = os.path.basename(directory)
        file_base = os.path.splitext(files[0])[0]
        file_base = re.sub(r'\d+$', '', file_base)  # Remove trailing numbers
        base_name = file_base.strip('_- ') if file_base.strip('_- ') else directory_name

        # Get versioned output path
        output_file = get_versioned_output_path(output_dir, base_name, extension)

        # Build the input pattern for FFmpeg
        first_file = files[0]
        match = re.search(r'(\d+)\.(\w+)$', first_file)
        if match:
            num_str = match.group(1)
            num_digits = len(num_str)
            ext = match.group(2)
            pattern = re.sub(r'\d+\.(\w+)$', f'%0{num_digits}d.{ext}', first_file)
            input_pattern = os.path.join(directory, pattern)
            start_number = int(num_str)
        else:
            self.report({'ERROR'}, "Could not determine image sequence pattern")
            props.render_state = 'ERROR'
            props.progress_message = "Invalid sequence pattern"
            return {'CANCELLED'}

        # Build FFmpeg command
        cmd = [
            ffmpeg_path,
            '-y',
            '-framerate', str(props.fps),
            '-start_number', str(start_number),
            '-i', input_pattern,
        ]
        cmd.extend(codec_args)
        cmd.append(output_file)

        print(f"[ImageSeqToVideo] FFmpeg command: {' '.join(cmd)}")

        render_id = str(uuid.uuid4())
        props.render_id = render_id
        props.frame_count = len(files)
        props.output_file = output_file

        # Start FFmpeg process
        try:
            if platform.system() == "Windows":
                CREATE_NO_WINDOW = 0x08000000
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            RenderProcessManager.add(render_id, proc, output_file)

            props.render_state = 'RENDERING'
            props.progress_message = "FFmpeg encoding..."
            props.start_time = time.time()

            # Start progress monitor
            bpy.ops.render.image_sequence_to_video_check_progress(
                'INVOKE_DEFAULT',
                render_id=render_id
            )

            self.report({'INFO'}, f"FFmpeg converting to: {output_file}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to start FFmpeg: {e}")
            props.render_state = 'ERROR'
            props.progress_message = f"FFmpeg error: {e}"
            return {'CANCELLED'}

    def _execute_blender(self, context, directory, files, output_dir, setup_dir, codec, props):
        """Execute conversion using Blender's VSE."""

        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "blender_video_setup.py")
        status_file = os.path.join(temp_dir, "blender_video_status.json")

        # Generate setup script
        script = generate_video_setup_script(
            image_dir=directory,
            files=files,
            output_dir=output_dir,
            setup_dir=setup_dir,
            fps=props.fps,
            quality=props.quality,
            codec=codec,
            preserve_alpha=props.preserve_alpha,
            view_transform=props.view_transform if props.override_color_management else 'Standard',
            look=props.look if props.override_color_management else 'None',
            exposure=props.exposure if props.override_color_management else 0.0,
            gamma=props.gamma if props.override_color_management else 1.0,
            status_file=status_file,
        )

        if not script:
            self.report({'ERROR'}, "Failed to generate setup script")
            return {'CANCELLED'}

        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script)
        except IOError as e:
            self.report({'ERROR'}, f"Cannot write setup script: {e}")
            return {'CANCELLED'}

        blender_exe = bpy.app.binary_path
        render_id = str(uuid.uuid4())
        props.render_id = render_id
        props.frame_count = len(files)

        if os.path.exists(status_file):
            try:
                os.unlink(status_file)
            except OSError:
                pass

        try:
            return self._execute_action(context, blender_exe, script_path,
                                       setup_dir, output_dir, props, render_id,
                                       status_file)
        finally:
            for temp_file in [script_path, status_file]:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except OSError:
                    pass

    def _execute_action(self, context, blender_exe, script_path, setup_dir,
                       output_dir, props, render_id, status_file):
        """Execute the selected action (setup, open, or render)."""

        print(f"[ImageSeqToVideo] Running setup script: {script_path}")

        result = subprocess.run(
            [blender_exe, "--background", "--python", script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

        print(f"[ImageSeqToVideo] Return code: {result.returncode}")
        if result.stdout:
            print(f"[ImageSeqToVideo] === STDOUT ===\n{result.stdout}")
        if result.stderr:
            print(f"[ImageSeqToVideo] === STDERR ===\n{result.stderr}")

        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            self.report({'ERROR'}, f"Setup script failed (code {result.returncode})")
            props.render_state = 'ERROR'
            props.progress_message = f"Script error: {error_msg[:100]}"
            return {'CANCELLED'}

        blend_file = None
        output_file = None

        for line in combined_output.splitlines():
            line = line.strip()
            if "Setup complete. Blend file saved to " in line:
                marker = "Setup complete. Blend file saved to "
                idx = line.find(marker)
                if idx != -1:
                    blend_file = line[idx + len(marker):].strip()
            elif "Video will be rendered to " in line:
                marker = "Video will be rendered to "
                idx = line.find(marker)
                if idx != -1:
                    output_file = line[idx + len(marker):].strip()

        if not blend_file and os.path.exists(status_file):
            try:
                import json
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                blend_file = status_data.get('blend_file')
                output_file = status_data.get('output_file')
            except Exception:
                pass

        if not blend_file:
            self.report({'ERROR'}, "Could not determine blend file path")
            props.render_state = 'ERROR'
            props.progress_message = "Script ran but didn't report blend file location"
            if os.path.exists(setup_dir):
                contents = os.listdir(setup_dir)
                blend_files = [f for f in contents if f.endswith('.blend')]
                if blend_files:
                    blend_files.sort(key=lambda f: os.path.getmtime(os.path.join(setup_dir, f)), reverse=True)
                    blend_file = os.path.join(setup_dir, blend_files[0])

            if not blend_file:
                return {'CANCELLED'}

        if not os.path.exists(blend_file):
            self.report({'ERROR'}, f"Blend file not found at: {blend_file}")
            props.render_state = 'ERROR'
            props.progress_message = f"File missing: {os.path.basename(blend_file)}"
            return {'CANCELLED'}

        props.setup_file = blend_file
        props.output_file = output_file or ""

        if props.action == 'SETUP':
            self.report({'INFO'}, f"Setup file created: {blend_file}")
            props.render_state = 'FINISHED'
            props.progress_message = f"Setup saved to {setup_dir}"
            return {'FINISHED'}

        elif props.action == 'OPEN':
            if platform.system() == "Windows":
                subprocess.Popen([blender_exe, blend_file],
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([blender_exe, blend_file])

            self.report({'INFO'}, f"Opening: {blend_file}")
            props.render_state = 'FINISHED'
            props.progress_message = "Setup file opened in new Blender"
            return {'FINISHED'}

        else:  # RENDER
            cmd = [blender_exe, "--background", blend_file, "--render-anim"]

            if platform.system() == "Windows":
                CREATE_NO_WINDOW = 0x08000000
                proc = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
            else:
                proc = subprocess.Popen(cmd)

            RenderProcessManager.add(render_id, proc, output_file)

            props.render_state = 'RENDERING'
            props.progress_message = "Starting conversion..."
            props.start_time = time.time()

            bpy.ops.render.image_sequence_to_video_check_progress(
                'INVOKE_DEFAULT',
                render_id=render_id
            )

            self.report({'INFO'}, f"Converting to: {output_file}")
            return {'FINISHED'}


class RENDER_OT_image_sequence_to_video(bpy.types.Operator):
    """Convert an image sequence to a video file."""
    bl_idname = "render.image_sequence_to_video"
    bl_label = "Image Sequence to Video"
    bl_description = "Convert rendered image sequences to video files"
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        props = context.scene.image_sequence_to_video_props

        # Reset state if not rendering
        if props.render_state != 'RENDERING':
            props.render_state = 'IDLE'
            props.progress_message = ""
            props.output_file = ""
            props.setup_file = ""
            props.render_id = ""

        # Pre-populate path from render output if available
        if not props.sequence_path and bpy.context.scene.render.filepath:
            render_path = bpy.path.abspath(bpy.context.scene.render.filepath)
            if render_path:
                props.sequence_path = render_path

        # Match scene FPS
        props.fps = bpy.context.scene.render.fps

        return context.window_manager.invoke_props_dialog(self, width=420, confirm_text="Convert")

    def execute(self, context):
        # Trigger the conversion via the execute operator
        return bpy.ops.render.image_sequence_to_video_execute()
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.image_sequence_to_video_props

        # If not idle, don't show anything in popup - Panel shows status
        if props.render_state != 'IDLE':
            layout.label(text="See Render panel for status", icon='INFO')
            return

        # Main form - use scene props
        layout.prop(props, "sequence_path")

        # Encoder selection box
        box = layout.box()
        box.label(text="Encoder", icon='RENDER_ANIMATION')
        row = box.row()
        row.prop(props, "encoder", expand=True)

        # Show FFmpeg status
        ffmpeg_path = find_ffmpeg()
        if props.encoder == 'FFMPEG':
            if ffmpeg_path:
                # Truncate path if too long
                display_path = ffmpeg_path
                if len(display_path) > 45:
                    display_path = "..." + display_path[-42:]
                box.label(text=f"Found: {display_path}", icon='CHECKMARK')
            else:
                box.label(text="FFmpeg not found!", icon='ERROR')
                box.label(text="Set path in addon preferences or install FFmpeg")
                box.operator("preferences.addon_show", text="Open Addon Preferences", icon='PREFERENCES').module = __name__

        # Video settings box
        box = layout.box()
        box.label(text="Output Settings", icon='OUTPUT')

        row = box.row(align=True)
        row.prop(props, "fps")
        row.prop(props, "quality")

        box.prop(props, "codec")

        # Alpha option - only enabled for WebM or ProRes
        row = box.row()
        row.prop(props, "preserve_alpha")
        row.enabled = props.codec in ('WEBM', 'PRORES')

        # Show warning if alpha selected but wrong codec
        if props.preserve_alpha and props.codec not in ('WEBM', 'PRORES'):
            row = box.row()
            row.alert = True
            row.label(text="Will switch to VP9/WebM for transparency", icon='INFO')

        # Color management - only available for Blender encoder
        if props.encoder == 'BLENDER':
            box = layout.box()
            box.prop(props, "override_color_management")

            if props.override_color_management:
                col = box.column(align=True)
                col.prop(props, "view_transform")
                col.prop(props, "look")

                row = col.row(align=True)
                row.prop(props, "exposure")
                row.prop(props, "gamma")

            # Action selection - only for Blender encoder
            layout.separator()
            layout.prop(props, "action")
        else:
            # FFmpeg info
            box = layout.box()
            box.label(text="FFmpeg converts directly - much faster!", icon='INFO')

    
    def _draw_render_status(self, layout, props, show_cancel=False):
        """Draw rendering in progress status."""
        box = layout.box()
        box.label(text="Converting...", icon='RENDER_ANIMATION')
        box.label(text=props.progress_message or "Starting...")

        # Show elapsed time
        if props.start_time > 0:
            elapsed = time.time() - props.start_time
            if elapsed >= 0 and elapsed < 86400 * 7:  # Sanity check
                box.label(text=f"Elapsed: {format_time(elapsed)}")

        if show_cancel:
            box.operator("render.image_sequence_to_video_cancel",
                        text="Cancel", icon='CANCEL')

        box.label(text="Progress shows in Render panel", icon='INFO')
    
    def _draw_finished_status(self, layout, props):
        """Draw completion status."""
        box = layout.box()
        box.label(text="Conversion Complete!", icon='CHECKMARK')
        box.label(text=props.progress_message)
        
        if props.output_file and os.path.exists(props.output_file):
            row = box.row(align=True)
            row.operator("wm.path_open", text="Open Video", 
                        icon='FILE_MOVIE').filepath = props.output_file
            row.operator("wm.path_open", text="Open Folder",
                        icon='FILE_FOLDER').filepath = os.path.dirname(props.output_file)
        
        box.operator("render.image_sequence_to_video_reset", 
                    text="Convert Another", icon='FILE_REFRESH')
    
    def _draw_error_status(self, layout, props):
        """Draw error status."""
        box = layout.box()
        icon = 'CANCEL' if props.render_state == 'CANCELLED' else 'ERROR'
        title = "Cancelled" if props.render_state == 'CANCELLED' else "Error"
        
        box.label(text=title, icon=icon)
        if props.progress_message:
            box.label(text=props.progress_message)
        
        box.operator("render.image_sequence_to_video_reset",
                    text="Try Again", icon='FILE_REFRESH')


# =============================================================================
# Panel
# =============================================================================

class RENDER_PT_image_sequence_to_video_panel(bpy.types.Panel):
    """Main panel in the Render properties."""
    bl_label = "Image Sequence to Video"
    bl_idname = "RENDER_PT_image_sequence_to_video"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.image_sequence_to_video_props
        
        if props.render_state == 'IDLE':
            row = layout.row()
            row.scale_y = 1.5
            row.operator("render.image_sequence_to_video", 
                        text="Convert Image Sequence", 
                        icon='FILE_MOVIE')
        
        elif props.render_state == 'RENDERING':
            box = layout.box()
            box.label(text="Converting...", icon='RENDER_ANIMATION')
            
            # Progress info
            col = box.column(align=True)
            col.label(text=props.progress_message or "Starting...")
            
            # Elapsed time
            if props.start_time > 0:
                elapsed = time.time() - props.start_time
                col.label(text=f"Elapsed: {format_time(elapsed)}")
            
            # Frame count
            if props.frame_count > 0:
                col.label(text=f"Frames: {props.frame_count}")
            
            # Cancel button
            row = box.row()
            row.alert = True
            row.operator("render.image_sequence_to_video_cancel",
                        text="Cancel", icon='CANCEL')
            
            # Output folder link
            if props.output_file:
                folder = os.path.dirname(props.output_file)
                if os.path.isdir(folder):
                    layout.operator("wm.path_open", 
                                   text="Open Output Folder",
                                   icon='FILE_FOLDER').filepath = folder
        
        elif props.render_state == 'FINISHED':
            box = layout.box()
            box.label(text="Conversion Complete!", icon='CHECKMARK')
            box.label(text=props.progress_message)
            
            # File access buttons
            if props.output_file and os.path.exists(props.output_file):
                row = box.row(align=True)
                row.operator("wm.path_open", 
                            text="Open Video",
                            icon='FILE_MOVIE').filepath = props.output_file
                row.operator("wm.path_open",
                            text="Open Folder", 
                            icon='FILE_FOLDER').filepath = os.path.dirname(props.output_file)
            
            # Convert another button
            layout.separator()
            row = layout.row()
            row.scale_y = 1.3
            row.operator("render.image_sequence_to_video",
                        text="Convert Another Sequence",
                        icon='FILE_MOVIE')
        
        elif props.render_state in ('ERROR', 'CANCELLED'):
            box = layout.box()
            icon = 'CANCEL' if props.render_state == 'CANCELLED' else 'ERROR'
            title = "Cancelled" if props.render_state == 'CANCELLED' else "Error"
            
            box.label(text=title, icon=icon)
            if props.progress_message:
                box.label(text=props.progress_message)
            
            layout.separator()
            row = layout.row()
            row.scale_y = 1.3
            row.operator("render.image_sequence_to_video_reset",
                        text="Reset", icon='FILE_REFRESH')


# =============================================================================
# Menu Entry
# =============================================================================

def menu_func(self, context):
    self.layout.operator(RENDER_OT_image_sequence_to_video.bl_idname)


# =============================================================================
# Registration
# =============================================================================

CLASSES = [
    ImageSequenceToVideoPreferences,
    ImageSequenceToVideoProperties,
    RENDER_OT_image_sequence_to_video_check_progress,
    RENDER_OT_image_sequence_to_video_cancel,
    RENDER_OT_image_sequence_to_video_reset,
    RENDER_OT_image_sequence_to_video_execute,
    RENDER_OT_image_sequence_to_video,
    RENDER_PT_image_sequence_to_video_panel,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.image_sequence_to_video_props = PointerProperty(
        type=ImageSequenceToVideoProperties
    )
    bpy.types.TOPBAR_MT_render.append(menu_func)


def unregister():
    # Clean up any running processes
    RenderProcessManager.cleanup_all()
    
    bpy.types.TOPBAR_MT_render.remove(menu_func)
    
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.image_sequence_to_video_props


if __name__ == "__main__":
    register()
