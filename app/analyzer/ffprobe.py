import json
import subprocess
from fractions import Fraction
from typing import Any

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
    BaseAnalyzer,
)


class FFProbeAnalyzer(BaseAnalyzer):
    name = "ffprobe"
    priority = 30

    required_tools = [
        "ffprobe",
    ]

    capabilities = [
        "container",
        "duration",
        "bitrate",
        "video_streams",
        "audio_streams",
        "subtitle_streams",
        "chapters",
        "resolution",
        "frame_rate",
        "hdr",
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
        command = [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            str(context.file_path),
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                analyzer=self.name,
                success=False,
                errors=[
                    "FFprobe wurde nach 60 Sekunden "
                    "abgebrochen."
                ],
            )

        if process.returncode != 0:
            error_message = (
                process.stderr.strip()
                or "FFprobe konnte die Datei nicht analysieren."
            )

            return AnalyzerResult(
                analyzer=self.name,
                success=False,
                errors=[
                    error_message,
                ],
            )

        try:
            probe_data = json.loads(
                process.stdout
            )
        except json.JSONDecodeError as exc:
            return AnalyzerResult(
                analyzer=self.name,
                success=False,
                errors=[
                    f"Ungültige FFprobe-Ausgabe: {exc}"
                ],
            )

        data = self._build_result(
            probe_data
        )

        return AnalyzerResult(
            analyzer=self.name,
            success=True,
            data=data,
        )

    def _build_result(
        self,
        probe_data: dict[str, Any],
    ) -> dict[str, Any]:
        format_data = probe_data.get(
            "format",
            {},
        )

        streams = probe_data.get(
            "streams",
            [],
        )

        chapters = probe_data.get(
            "chapters",
            [],
        )

        video_streams = []
        audio_streams = []
        subtitle_streams = []
        other_streams = []

        for stream in streams:
            codec_type = stream.get(
                "codec_type"
            )

            if codec_type == "video":
                video_streams.append(
                    self._parse_video_stream(
                        stream
                    )
                )
            elif codec_type == "audio":
                audio_streams.append(
                    self._parse_audio_stream(
                        stream
                    )
                )
            elif codec_type == "subtitle":
                subtitle_streams.append(
                    self._parse_subtitle_stream(
                        stream
                    )
                )
            else:
                other_streams.append(
                    self._parse_generic_stream(
                        stream
                    )
                )

        primary_video = (
            video_streams[0]
            if video_streams
            else None
        )

        return {
            "container": {
                "format_name": format_data.get(
                    "format_name"
                ),
                "format_long_name": format_data.get(
                    "format_long_name"
                ),
                "duration_seconds": (
                    self._to_float(
                        format_data.get(
                            "duration"
                        )
                    )
                ),
                "size_bytes": (
                    self._to_int(
                        format_data.get(
                            "size"
                        )
                    )
                ),
                "bitrate_bps": (
                    self._to_int(
                        format_data.get(
                            "bit_rate"
                        )
                    )
                ),
                "probe_score": (
                    self._to_int(
                        format_data.get(
                            "probe_score"
                        )
                    )
                ),
                "tags": format_data.get(
                    "tags",
                    {},
                ),
            },
            "duration_seconds": (
                self._to_float(
                    format_data.get(
                        "duration"
                    )
                )
            ),
            "bitrate_bps": (
                self._to_int(
                    format_data.get(
                        "bit_rate"
                    )
                )
            ),
            "resolution": (
                {
                    "width": primary_video.get(
                        "width"
                    ),
                    "height": primary_video.get(
                        "height"
                    ),
                }
                if primary_video
                else None
            ),
            "video_codec": (
                primary_video.get(
                    "codec_name"
                )
                if primary_video
                else None
            ),
            "frame_rate": (
                primary_video.get(
                    "frame_rate"
                )
                if primary_video
                else None
            ),
            "hdr": (
                primary_video.get(
                    "hdr"
                )
                if primary_video
                else None
            ),
            "video_streams": video_streams,
            "audio_streams": audio_streams,
            "subtitle_streams": (
                subtitle_streams
            ),
            "other_streams": other_streams,
            "stream_count": len(streams),
            "video_stream_count": len(
                video_streams
            ),
            "audio_stream_count": len(
                audio_streams
            ),
            "subtitle_stream_count": len(
                subtitle_streams
            ),
            "chapter_count": len(chapters),
            "chapters": [
                self._parse_chapter(
                    chapter
                )
                for chapter in chapters
            ],
        }

    def _parse_video_stream(
        self,
        stream: dict[str, Any],
    ) -> dict[str, Any]:
        frame_rate = self._parse_fraction(
            stream.get(
                "avg_frame_rate"
            )
            or stream.get(
                "r_frame_rate"
            )
        )

        color_transfer = stream.get(
            "color_transfer"
        )

        color_primaries = stream.get(
            "color_primaries"
        )

        color_space = stream.get(
            "color_space"
        )

        hdr_type = self._detect_hdr(
            stream
        )

        return {
            "index": stream.get(
                "index"
            ),
            "codec_name": stream.get(
                "codec_name"
            ),
            "codec_long_name": stream.get(
                "codec_long_name"
            ),
            "profile": stream.get(
                "profile"
            ),
            "width": stream.get(
                "width"
            ),
            "height": stream.get(
                "height"
            ),
            "coded_width": stream.get(
                "coded_width"
            ),
            "coded_height": stream.get(
                "coded_height"
            ),
            "pixel_format": stream.get(
                "pix_fmt"
            ),
            "level": stream.get(
                "level"
            ),
            "frame_rate": frame_rate,
            "bitrate_bps": self._to_int(
                stream.get(
                    "bit_rate"
                )
            ),
            "duration_seconds": self._to_float(
                stream.get(
                    "duration"
                )
            ),
            "color_range": stream.get(
                "color_range"
            ),
            "color_space": color_space,
            "color_transfer": (
                color_transfer
            ),
            "color_primaries": (
                color_primaries
            ),
            "hdr": hdr_type,
            "language": self._get_language(
                stream
            ),
            "title": self._get_title(
                stream
            ),
            "default": self._is_default(
                stream
            ),
            "forced": self._is_forced(
                stream
            ),
            "tags": stream.get(
                "tags",
                {},
            ),
        }

    def _parse_audio_stream(
        self,
        stream: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "index": stream.get(
                "index"
            ),
            "codec_name": stream.get(
                "codec_name"
            ),
            "codec_long_name": stream.get(
                "codec_long_name"
            ),
            "profile": stream.get(
                "profile"
            ),
            "sample_rate": self._to_int(
                stream.get(
                    "sample_rate"
                )
            ),
            "channels": stream.get(
                "channels"
            ),
            "channel_layout": stream.get(
                "channel_layout"
            ),
            "bitrate_bps": self._to_int(
                stream.get(
                    "bit_rate"
                )
            ),
            "duration_seconds": self._to_float(
                stream.get(
                    "duration"
                )
            ),
            "language": self._get_language(
                stream
            ),
            "title": self._get_title(
                stream
            ),
            "default": self._is_default(
                stream
            ),
            "forced": self._is_forced(
                stream
            ),
            "tags": stream.get(
                "tags",
                {},
            ),
        }

    def _parse_subtitle_stream(
        self,
        stream: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "index": stream.get(
                "index"
            ),
            "codec_name": stream.get(
                "codec_name"
            ),
            "codec_long_name": stream.get(
                "codec_long_name"
            ),
            "language": self._get_language(
                stream
            ),
            "title": self._get_title(
                stream
            ),
            "default": self._is_default(
                stream
            ),
            "forced": self._is_forced(
                stream
            ),
            "hearing_impaired": (
                self._is_hearing_impaired(
                    stream
                )
            ),
            "tags": stream.get(
                "tags",
                {},
            ),
        }

    def _parse_generic_stream(
        self,
        stream: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "index": stream.get(
                "index"
            ),
            "codec_type": stream.get(
                "codec_type"
            ),
            "codec_name": stream.get(
                "codec_name"
            ),
            "language": self._get_language(
                stream
            ),
            "title": self._get_title(
                stream
            ),
            "tags": stream.get(
                "tags",
                {},
            ),
        }

    def _parse_chapter(
        self,
        chapter: dict[str, Any],
    ) -> dict[str, Any]:
        tags = chapter.get(
            "tags",
            {},
        )

        return {
            "id": chapter.get(
                "id"
            ),
            "start_seconds": self._to_float(
                chapter.get(
                    "start_time"
                )
            ),
            "end_seconds": self._to_float(
                chapter.get(
                    "end_time"
                )
            ),
            "title": tags.get(
                "title"
            ),
            "tags": tags,
        }

    def _detect_hdr(
        self,
        stream: dict[str, Any],
    ) -> str | None:
        transfer = str(
            stream.get(
                "color_transfer",
                ""
            )
        ).lower()

        side_data = stream.get(
            "side_data_list",
            [],
        )

        side_data_text = json.dumps(
            side_data,
            ensure_ascii=False,
        ).lower()

        if (
            "dovi" in side_data_text
            or "dolby vision" in side_data_text
        ):
            return "dolby_vision"

        if transfer == "smpte2084":
            if (
                "content light level"
                in side_data_text
                or "mastering display metadata"
                in side_data_text
            ):
                return "hdr10"

            return "pq"

        if transfer == "arib-std-b67":
            return "hlg"

        return None

    def _get_language(
        self,
        stream: dict[str, Any],
    ) -> str | None:
        return stream.get(
            "tags",
            {},
        ).get(
            "language"
        )

    def _get_title(
        self,
        stream: dict[str, Any],
    ) -> str | None:
        return stream.get(
            "tags",
            {},
        ).get(
            "title"
        )

    def _is_default(
        self,
        stream: dict[str, Any],
    ) -> bool:
        return bool(
            stream.get(
                "disposition",
                {},
            ).get(
                "default",
                0,
            )
        )

    def _is_forced(
        self,
        stream: dict[str, Any],
    ) -> bool:
        return bool(
            stream.get(
                "disposition",
                {},
            ).get(
                "forced",
                0,
            )
        )

    def _is_hearing_impaired(
        self,
        stream: dict[str, Any],
    ) -> bool:
        disposition = stream.get(
            "disposition",
            {},
        )

        return bool(
            disposition.get(
                "hearing_impaired",
                0,
            )
        )

    def _parse_fraction(
        self,
        value: Any,
    ) -> float | None:
        if not value:
            return None

        try:
            fraction = Fraction(
                str(value)
            )

            if fraction.denominator == 0:
                return None

            return round(
                float(fraction),
                6,
            )
        except (
            ValueError,
            ZeroDivisionError,
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
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None
