"""
Tests for get_ffmpeg_codec_args function.

This function generates FFmpeg command-line arguments for different codecs and quality levels.
"""
import pytest


class TestH264Codec:
    """Tests for H.264/MP4 codec arguments."""

    def test_h264_returns_mp4_extension(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('H264', 'MEDIUM')

        assert ext == 'mp4'

    def test_h264_uses_libx264(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('H264', 'MEDIUM')

        assert '-c:v' in args
        assert 'libx264' in args

    def test_h264_has_crf(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('H264', 'MEDIUM')

        assert '-crf' in args

    def test_h264_uses_yuv420p(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('H264', 'MEDIUM')

        assert '-pix_fmt' in args
        assert 'yuv420p' in args

    def test_h264_has_faststart(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('H264', 'MEDIUM')

        assert '-movflags' in args
        assert '+faststart' in args


class TestWebMCodec:
    """Tests for VP9/WebM codec arguments."""

    def test_webm_returns_webm_extension(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('WEBM', 'MEDIUM')

        assert ext == 'webm'

    def test_webm_uses_libvpx_vp9(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('WEBM', 'MEDIUM')

        assert '-c:v' in args
        assert 'libvpx-vp9' in args

    def test_webm_no_alpha_uses_yuv420p(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('WEBM', 'MEDIUM', preserve_alpha=False)

        assert 'yuv420p' in args

    def test_webm_with_alpha_uses_yuva420p(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('WEBM', 'MEDIUM', preserve_alpha=True)

        assert 'yuva420p' in args

    def test_webm_has_row_mt(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('WEBM', 'MEDIUM')

        assert '-row-mt' in args
        assert '1' in args


class TestAV1Codec:
    """Tests for AV1/WebM codec arguments."""

    def test_av1_returns_webm_extension(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('AV1', 'MEDIUM')

        assert ext == 'webm'

    def test_av1_uses_libaom_av1(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('AV1', 'MEDIUM')

        assert '-c:v' in args
        assert 'libaom-av1' in args

    def test_av1_has_cpu_used(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('AV1', 'MEDIUM')

        assert '-cpu-used' in args


class TestProResCodec:
    """Tests for ProRes/MOV codec arguments."""

    def test_prores_returns_mov_extension(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('PRORES', 'MEDIUM')

        assert ext == 'mov'

    def test_prores_uses_prores_ks(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('PRORES', 'MEDIUM')

        assert '-c:v' in args
        assert 'prores_ks' in args

    def test_prores_has_profile(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('PRORES', 'MEDIUM')

        assert '-profile:v' in args

    def test_prores_no_alpha_uses_yuv422p10le(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('PRORES', 'MEDIUM', preserve_alpha=False)

        assert 'yuv422p10le' in args

    def test_prores_with_alpha_uses_yuva444p10le(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('PRORES', 'MEDIUM', preserve_alpha=True)

        assert 'yuva444p10le' in args


class TestQualityLevels:
    """Tests for different quality levels affecting CRF values."""

    def test_quality_affects_crf_h264(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        _, low_args = get_ffmpeg_codec_args('H264', 'LOWEST')
        _, high_args = get_ffmpeg_codec_args('H264', 'HIGHEST')

        # Get CRF values
        low_crf_idx = low_args.index('-crf') + 1
        high_crf_idx = high_args.index('-crf') + 1

        # Lower quality = higher CRF value (bigger number = worse quality)
        assert int(low_args[low_crf_idx]) > int(high_args[high_crf_idx])

    def test_all_quality_levels_valid_h264(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        qualities = ['LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST']

        for quality in qualities:
            ext, args = get_ffmpeg_codec_args('H264', quality)
            assert ext == 'mp4'
            assert len(args) > 0
            assert '-crf' in args

    def test_all_quality_levels_valid_webm(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        qualities = ['LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST']

        for quality in qualities:
            ext, args = get_ffmpeg_codec_args('WEBM', quality)
            assert ext == 'webm'
            assert len(args) > 0

    def test_prores_quality_affects_profile(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        _, low_args = get_ffmpeg_codec_args('PRORES', 'LOWEST')
        _, high_args = get_ffmpeg_codec_args('PRORES', 'HIGHEST')

        # Get profile values
        low_profile_idx = low_args.index('-profile:v') + 1
        high_profile_idx = high_args.index('-profile:v') + 1

        # Different profiles for different quality
        assert low_args[low_profile_idx] != high_args[high_profile_idx]


class TestUnknownCodec:
    """Tests for handling unknown codec values."""

    def test_unknown_codec_defaults_to_h264(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('UNKNOWN_CODEC', 'MEDIUM')

        assert ext == 'mp4'
        assert 'libx264' in args

    def test_empty_codec_defaults_to_h264(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('', 'MEDIUM')

        assert ext == 'mp4'

    def test_unknown_quality_uses_default_crf(self):
        from image_sequence_to_video import get_ffmpeg_codec_args

        ext, args = get_ffmpeg_codec_args('H264', 'INVALID_QUALITY')

        # Should still work with default CRF (20)
        assert ext == 'mp4'
        assert '-crf' in args
        crf_idx = args.index('-crf') + 1
        assert args[crf_idx] == '20'  # Default CRF
