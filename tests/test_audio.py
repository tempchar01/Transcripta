import pytest

from app.audio import media
from app.audio.media import MediaError, assert_supported, chunk_count, format_duration


def test_duration_formatting():
    assert format_duration(10_651.4) == "02:57:31"
    assert format_duration(-1) == "00:00:00"


def test_chunk_segmentation_is_bounded():
    assert chunk_count(3 * 3600, 900) == 12
    assert chunk_count(901, 900) == 2
    with pytest.raises(ValueError):
        chunk_count(0, 900)


def test_unsupported_format_is_rejected(tmp_path):
    source = tmp_path / "audio.exe"
    source.write_bytes(b"not media")
    with pytest.raises(MediaError, match="Неподдерживаемый"):
        assert_supported(source)


def test_ffmpeg_resolution_prefers_bundled_then_configured_then_path(monkeypatch, tmp_path):
    bundled = tmp_path / "bundled" / "ffmpeg" / "bin"; bundled.mkdir(parents=True)
    configured = tmp_path / "configured"; configured.mkdir()
    inherited = tmp_path / "path"; inherited.mkdir()
    for directory in (bundled, configured, inherited):
        (directory / "ffmpeg.exe").touch(); (directory / "ffprobe.exe").touch()
    monkeypatch.setattr(media, "_bundled_ffmpeg_directories", lambda: (bundled,))
    monkeypatch.setenv(media.FFMPEG_DIRECTORY_ENV, str(configured))
    monkeypatch.setattr(media.shutil, "which", lambda _name: str(inherited / "ffmpeg.exe"))
    assert media.resolve_ffmpeg_binary("ffmpeg") == bundled / "ffmpeg.exe"
    for binary in bundled.iterdir(): binary.unlink()
    assert media.resolve_ffmpeg_binary("ffmpeg") == configured / "ffmpeg.exe"
    for binary in configured.iterdir(): binary.unlink()
    assert media.resolve_ffmpeg_binary("ffmpeg") == inherited / "ffmpeg.exe"


def test_pyav_duration_works_without_external_ffmpeg(monkeypatch, synthetic_wav):
    monkeypatch.setattr(media, "resolve_ffmpeg_binary", lambda _name: None)
    assert media.get_duration(synthetic_wav) > 0


def test_pyav_streams_bounded_wav_without_external_ffmpeg(monkeypatch, synthetic_wav, tmp_path):
    monkeypatch.setattr(media, "resolve_ffmpeg_binary", lambda _name: None)
    chunk = next(media.stream_chunks(synthetic_wav, tmp_path, 1.0, 30))
    assert chunk.path.is_file()
    assert chunk.path.stat().st_size > 44


def test_corrupted_media_has_safe_user_error(monkeypatch, tmp_path):
    source = tmp_path / "broken.ogg"; source.write_bytes(b"not media")
    monkeypatch.setattr(media, "resolve_ffmpeg_binary", lambda _name: None)
    with pytest.raises(MediaError, match="Не удалось открыть медиафайл"):
        media.get_duration(source)
