"""Tests for factory functions and public API."""

from soundify import (
    APIConfig,
    MetadataExtractorService,
    create_extractor,
)


class TestCreateExtractor:
    """Tests for create_extractor factory function."""

    def test_creates_extractor_with_defaults(self) -> None:
        """Should create extractor with default config."""
        extractor = create_extractor()

        assert isinstance(extractor, MetadataExtractorService)

    def test_creates_extractor_with_custom_config(self) -> None:
        """Should create extractor with custom config."""
        config = APIConfig(search_limit=5, ignore_spelling=False)
        extractor = create_extractor(config)

        assert isinstance(extractor, MetadataExtractorService)


class TestPublicAPI:
    """Tests for public API exports."""

    def test_all_expected_exports_available(self) -> None:
        """All documented exports should be available."""
        import soundify

        # Factory functions
        assert hasattr(soundify, "create_extractor")
        assert hasattr(soundify, "create_downloader")
        assert hasattr(soundify, "create_playlist_downloader")

        # Services (only high-level)
        assert hasattr(soundify, "MetadataExtractorService")
        assert hasattr(soundify, "PlaylistDownloadService")

        # Models
        assert hasattr(soundify, "TrackMetadata")
        assert hasattr(soundify, "VideoType")
        assert hasattr(soundify, "ContentKind")
        assert hasattr(soundify, "ExtractProgress")
        assert hasattr(soundify, "DownloadProgress")
        assert hasattr(soundify, "DownloadResult")
        assert hasattr(soundify, "DownloadStatus")

        # Config
        assert hasattr(soundify, "APIConfig")
        assert hasattr(soundify, "AudioCodec")
        assert hasattr(soundify, "DownloadConfig")
        assert hasattr(soundify, "PlaylistDownloadConfig")

        # Exceptions
        assert hasattr(soundify, "SoundifyError")
        assert hasattr(soundify, "PlaylistParseError")
        assert hasattr(soundify, "PlaylistNotFoundError")
        assert hasattr(soundify, "UpstreamAPIError")

    def test_internal_not_exported(self) -> None:
        """Internal implementation details should not be exported."""
        import soundify

        # Client is internal (use factory functions instead)
        assert not hasattr(soundify, "YTMusicClient")
        assert not hasattr(soundify, "YTMusicProtocol")

        # Internal services (use PlaylistDownloadService instead)
        assert not hasattr(soundify, "DownloadService")
        assert not hasattr(soundify, "PlaylistArtifactsService")

        # Downloader backend is internal
        assert not hasattr(soundify, "YTDLPDownloader")
        assert not hasattr(soundify, "DownloaderProtocol")
        assert not hasattr(soundify, "tag_track")
