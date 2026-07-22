import json
import subprocess
from pathlib import Path
from typing import Any

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
    BaseAnalyzer,
)


class MediaInfoAnalyzer(BaseAnalyzer):
    name = "mediainfo"
    priority = 35

    required_tools = [
        "mediainfo",
    ]

    capabilities = [
        "container_details",
        "video_profile",
        "scan_type",
        "bit_depth",
        "audio_profiles",
        "audio_channels",
        "subtitle_languages",
        "encoded_metadata",
    ]

    def can_analyze(
        self,
        context: AnalyzerContext,
    ) -> bool:
        return (
            context.file_path.exists()
            and context.file_path.is_file()
        )

    def analyze(
        self,
        context: AnalyzerContext,
    ) -> AnalyzerResult:
        raw_data = self._run_mediainfo(
            context.file_path
        )

        media = raw_data.get(
            "media",
            {},
        )

        tracks = media.get(
            "track",
            [],
        )

        if not isinstance(tracks, list):
            tracks = []

        general_track = None
        video_tracks: list[dict[str, Any]] = []
        audio_tracks: list[dict[str, Any]] = []
        text_tracks: list[dict[str, Any]] = []
        other_tracks: list[dict[str, Any]] = []

        for track in tracks:
            if not isinstance(track, dict):
                continue

            track_type = str(
                track.get("@type")
                or track.get("type")
                or ""
            ).lower()

            normalized = self._normalize_track(
                track
            )

            if track_type == "general":
                general_track = normalized

            elif track_type == "video":
                video_tracks.append(
                    normalized
                )

            elif track_type == "audio":
                audio_tracks.append(
                    normalized
                )

            elif track_type in {
                "text",
                "subtitle",
            }:
                text_tracks.append(
                    normalized
                )

            else:
                other_tracks.append(
                    normalized
                )

        summary = self._build_summary(
            general_track=general_track,
            video_tracks=video_tracks,
            audio_tracks=audio_tracks,
            text_tracks=text_tracks,
        )

        warnings = []

        if not video_tracks:
            warnings.append(
                "MediaInfo hat keine Videospur erkannt."
            )

        data = {
            "mediainfo": {
                "summary": summary,
                "general": general_track,
                "video_tracks": video_tracks,
                "audio_tracks": audio_tracks,
                "text_tracks": text_tracks,
                "other_tracks": other_tracks,
                "track_count": len(tracks),
                "analyzer_version": "2",
            }
        }

        return AnalyzerResult(
            analyzer=self.name,
            success=True,
            data=data,
            warnings=warnings,
        )

    def _run_mediainfo(
        self,
        file_path: Path,
    ) -> dict[str, Any]:
        command = [
            "mediainfo",
            "--Output=JSON",
            str(file_path),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )

        if completed.returncode != 0:
            error_text = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "Unbekannter MediaInfo-Fehler."
            )

            raise RuntimeError(
                "MediaInfo konnte die Datei "
                f"nicht untersuchen: {error_text}"
            )

        output = completed.stdout.strip()

        if not output:
            raise RuntimeError(
                "MediaInfo hat keine Daten geliefert."
            )

        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "MediaInfo lieferte ungültiges JSON: "
                f"{exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise RuntimeError(
                "MediaInfo lieferte kein JSON-Objekt."
            )

        return parsed

    def _normalize_track(
        self,
        track: dict[str, Any],
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        for key, value in track.items():
            clean_key = key.lstrip("@")

            if value in (
                "",
                None,
            ):
                continue

            normalized[clean_key] = (
                self._normalize_value(
                    value
                )
            )

        return normalized

    def _normalize_value(
        self,
        value: Any,
    ) -> Any:
        if isinstance(value, dict):
            return {
                key: self._normalize_value(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self._normalize_value(item)
                for item in value
            ]

        return value

    def _build_summary(
        self,
        general_track: dict[str, Any] | None,
        video_tracks: list[dict[str, Any]],
        audio_tracks: list[dict[str, Any]],
        text_tracks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        primary_video = (
            video_tracks[0]
            if video_tracks
            else {}
        )

        primary_audio = (
            audio_tracks[0]
            if audio_tracks
            else {}
        )

        general = general_track or {}

        width = self._to_int(
            primary_video.get("Width")
        )

        height = self._to_int(
            primary_video.get("Height")
        )

        bit_depth = self._to_int(
            primary_video.get("BitDepth")
        )

        frame_rate = self._to_float(
            primary_video.get("FrameRate")
        )

        duration_value = self._to_float(
            general.get("Duration")
        )

        duration_seconds = (
            round(duration_value, 3)
            if duration_value is not None
            else None
        )

        return {
            "format": (
                general.get("Format")
            ),
            "format_profile": (
                general.get("Format_Profile")
            ),
            "codec_id": (
                general.get("CodecID")
            ),
            "file_size_bytes": self._to_int(
                general.get("FileSize")
            ),
            "duration_seconds": (
                duration_seconds
            ),
            "overall_bitrate_bps": (
                self._to_int(
                    general.get(
                        "OverallBitRate"
                    )
                )
            ),
            "encoded_date": (
                general.get("Encoded_Date")
            ),
            "writing_application": (
                general.get(
                    "Encoded_Application"
                )
                or general.get(
                    "WritingApplication"
                )
            ),
            "writing_library": (
                general.get(
                    "Encoded_Library"
                )
                or general.get(
                    "WritingLibrary"
                )
            ),
            "video_codec": (
                primary_video.get("Format")
            ),
            "video_profile": (
                primary_video.get(
                    "Format_Profile"
                )
            ),
            "video_level": (
                primary_video.get(
                    "Format_Level"
                )
            ),
            "width": width,
            "height": height,
            "frame_rate": frame_rate,
            "frame_rate_mode": (
                primary_video.get(
                    "FrameRate_Mode"
                )
            ),
            "scan_type": (
                primary_video.get("ScanType")
            ),
            "scan_order": (
                primary_video.get("ScanOrder")
            ),
            "bit_depth": bit_depth,
            "chroma_subsampling": (
                primary_video.get(
                    "ChromaSubsampling"
                )
            ),
            "color_space": (
                primary_video.get(
                    "ColorSpace"
                )
            ),
            "color_primaries": (
                primary_video.get(
                    "colour_primaries"
                )
            ),
            "transfer_characteristics": (
                primary_video.get(
                    "transfer_characteristics"
                )
            ),
            "matrix_coefficients": (
                primary_video.get(
                    "matrix_coefficients"
                )
            ),
            "hdr_format": (
                primary_video.get(
                    "HDR_Format"
                )
            ),
            "audio_codec": (
                primary_audio.get("Format")
            ),
            "audio_profile": (
                primary_audio.get(
                    "Format_AdditionalFeatures"
                )
                or primary_audio.get(
                    "Format_Profile"
                )
            ),
            "audio_channels": (
                self._to_int(
                    primary_audio.get(
                        "Channels"
                    )
                )
            ),
            "audio_channel_layout": (
                primary_audio.get(
                    "ChannelLayout"
                )
            ),
            "audio_sample_rate": (
                self._to_int(
                    primary_audio.get(
                        "SamplingRate"
                    )
                )
            ),
            "audio_languages": (
                self._collect_languages(
                    audio_tracks
                )
            ),
            "subtitle_languages": (
                self._collect_languages(
                    text_tracks
                )
            ),
            "video_track_count": len(
                video_tracks
            ),
            "audio_track_count": len(
                audio_tracks
            ),
            "text_track_count": len(
                text_tracks
            ),
        }

    def _collect_languages(
        self,
        tracks: list[dict[str, Any]],
    ) -> list[str]:
        languages: list[str] = []

        for track in tracks:
            language = (
                track.get("Language")
                or track.get("Language_String")
            )

            if not language:
                continue

            language_text = str(language)

            if language_text not in languages:
                languages.append(
                    language_text
                )

        return languages

    def _to_int(
        self,
        value: Any,
    ) -> int | None:
        if value in (
            None,
            "",
            "N/A",
        ):
            return None

        try:
            return int(float(value))
        except (
            TypeError,
            ValueError,
        ):
            return None

    def _to_float(
        self,
        value: Any,
    ) -> float | None:
        if value in (
            None,
            "",
            "N/A",
        ):
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None
