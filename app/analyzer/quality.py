from typing import Any

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
    BaseAnalyzer,
)
from app.analyzer.quality_profiles import (
    get_quality_profile,
)


class QualityAnalyzer(BaseAnalyzer):
    name = "quality"
    priority = 40

    required_tools: list[str] = []

    capabilities = [
        "quality_score",
        "quality_level",
        "resolution_class",
        "video_codec_class",
        "audio_quality",
        "hdr_quality",
        "quality_recommendation",
    ]

    def can_analyze(
        self,
        context: AnalyzerContext,
    ) -> bool:
        return bool(context.shared_data.get("video_streams"))

    def analyze(
        self,
        context: AnalyzerContext,
    ) -> AnalyzerResult:
        media = context.shared_data

        requested_profile = context.options.get(
            "quality_profile",
            "balanced",
        )

        quality_profile = get_quality_profile(str(requested_profile))

        video_streams = media.get(
            "video_streams",
            [],
        )

        audio_streams = media.get(
            "audio_streams",
            [],
        )

        mediainfo = media.get(
            "mediainfo",
            {},
        )

        if not isinstance(mediainfo, dict):
            mediainfo = {}

        mediainfo_summary = mediainfo.get(
            "summary",
            {},
        )

        if not isinstance(
            mediainfo_summary,
            dict,
        ):
            mediainfo_summary = {}

        if not video_streams:
            return AnalyzerResult(
                analyzer=self.name,
                success=False,
                skipped=True,
                skip_reason=("Keine Video-Daten für die Qualitätsbewertung vorhanden."),
            )

        primary_video = video_streams[0]

        width = self._to_int(primary_video.get("width"))

        height = self._to_int(primary_video.get("height"))

        video_codec = str(primary_video.get("codec_name") or "").lower()

        pixel_format = str(primary_video.get("pixel_format") or "").lower()

        frame_rate = self._to_float(primary_video.get("frame_rate"))

        bitrate = self._to_int(primary_video.get("bitrate_bps"))

        if bitrate is None:
            bitrate = self._to_int(media.get("bitrate_bps"))

        hdr = primary_video.get("hdr") or media.get("hdr")

        resolution_class = self._resolution_class(
            width,
            height,
        )

        codec_class = self._video_codec_class(video_codec)

        bit_depth = self._detect_bit_depth(pixel_format)

        mediainfo_bit_depth = self._to_int(mediainfo_summary.get("bit_depth"))

        if mediainfo_bit_depth is not None:
            bit_depth = mediainfo_bit_depth

        mediainfo_hdr = mediainfo_summary.get("hdr_format")

        if not hdr and mediainfo_hdr:
            hdr = mediainfo_hdr

        scan_type = mediainfo_summary.get("scan_type")

        frame_rate_mode = mediainfo_summary.get("frame_rate_mode")

        chroma_subsampling = mediainfo_summary.get("chroma_subsampling")

        video_profile = mediainfo_summary.get("video_profile")

        audio_channels = self._to_int(mediainfo_summary.get("audio_channels"))

        audio_quality = self._audio_quality(audio_streams)

        score_details: list[dict[str, Any]] = []

        score = 0

        resolution_score = self._resolution_score(height)

        score += resolution_score

        score_details.append(
            {
                "category": "resolution",
                "score": resolution_score,
                "maximum": 40,
                "value": resolution_class,
            }
        )

        codec_score = self._codec_score(video_codec)

        score += codec_score

        score_details.append(
            {
                "category": "video_codec",
                "score": codec_score,
                "maximum": 20,
                "value": video_codec or None,
            }
        )

        bitrate_score = self._bitrate_score(
            bitrate,
            height,
        )

        score += bitrate_score

        score_details.append(
            {
                "category": "bitrate",
                "score": bitrate_score,
                "maximum": 20,
                "value_bps": bitrate,
            }
        )

        audio_score = self._audio_score(audio_streams)

        score += audio_score

        score_details.append(
            {
                "category": "audio",
                "score": audio_score,
                "maximum": 10,
                "value": audio_quality,
            }
        )

        feature_score = self._feature_score(
            hdr=hdr,
            bit_depth=bit_depth,
            frame_rate=frame_rate,
            scan_type=scan_type,
        )

        score += feature_score

        score_details.append(
            {
                "category": "features",
                "score": feature_score,
                "maximum": 10,
                "hdr": hdr,
                "bit_depth": bit_depth,
                "frame_rate": frame_rate,
                "scan_type": scan_type,
            }
        )

        score = max(
            0,
            min(100, score),
        )

        quality_level = self._quality_level(
            score,
            quality_profile,
        )

        recommendation = self._recommendation(
            score=score,
            height=height,
            video_codec=video_codec,
            audio_quality=audio_quality,
            bitrate=bitrate,
            audio_channels=audio_channels,
            quality_profile=quality_profile,
        )

        warnings = []

        if bitrate is None:
            warnings.append(
                "Keine zuverlässige Video-Bitrate "
                "verfügbar; es wurde ersatzweise "
                "die Container-Bitrate verwendet "
                "oder die Bewertung reduziert."
            )

        data = {
            "quality": {
                "score": score,
                "level": quality_level,
                "profile": {
                    "name": quality_profile.get("name"),
                    "label": quality_profile.get("label"),
                    "description": (quality_profile.get("description")),
                },
                "resolution_class": (resolution_class),
                "width": width,
                "height": height,
                "video_codec": (video_codec or None),
                "video_codec_class": (codec_class),
                "video_bitrate_bps": (bitrate),
                "frame_rate": (frame_rate),
                "frame_rate_mode": (frame_rate_mode),
                "scan_type": (scan_type),
                "pixel_format": (pixel_format or None),
                "chroma_subsampling": (chroma_subsampling),
                "bit_depth": (bit_depth),
                "hdr": hdr,
                "video_profile": (video_profile),
                "audio_quality": (audio_quality),
                "audio_channels": (audio_channels),
                "recommendation": (recommendation),
                "score_details": (score_details),
                "data_sources": [
                    "ffprobe",
                    "mediainfo",
                ],
                "evaluation_version": "3",
            }
        }

        return AnalyzerResult(
            analyzer=self.name,
            success=True,
            data=data,
            warnings=warnings,
        )

    def _resolution_class(
        self,
        width: int | None,
        height: int | None,
    ) -> str:
        if height is None:
            return "unknown"

        if height >= 4320:
            return "8K"

        if height >= 2160:
            return "4K UHD"

        if height >= 1440:
            return "QHD"

        if height >= 1080:
            return "Full HD"

        if height >= 720:
            return "HD"

        if height >= 576:
            return "SD"

        if height >= 480:
            return "SD Low"

        return "Low Resolution"

    def _video_codec_class(
        self,
        codec: str,
    ) -> str:
        if codec in {
            "av1",
            "hevc",
            "h265",
            "vp9",
        }:
            return "modern"

        if codec in {
            "h264",
            "avc",
        }:
            return "compatible"

        if codec in {
            "mpeg4",
            "mpeg2video",
            "mpeg1video",
            "vp8",
        }:
            return "legacy"

        if not codec:
            return "unknown"

        return "other"

    def _audio_quality(
        self,
        streams: list[dict[str, Any]],
    ) -> str:
        if not streams:
            return "none"

        best_rank = 0
        best_label = "basic"

        for stream in streams:
            codec = str(stream.get("codec_name") or "").lower()

            channels = self._to_int(stream.get("channels")) or 0

            if codec in {
                "truehd",
                "dts",
                "dts_hd",
                "flac",
                "alac",
                "pcm_s16le",
                "pcm_s24le",
            }:
                rank = 4
                label = "lossless"

            elif codec in {
                "eac3",
                "ac3",
                "opus",
            }:
                rank = 3
                label = "high"

            elif codec in {
                "aac",
                "vorbis",
            }:
                rank = 2
                label = "standard"

            else:
                rank = 1
                label = "basic"

            if channels >= 6:
                rank += 1
                label = label + "_surround"

            if rank > best_rank:
                best_rank = rank
                best_label = label

        return best_label

    def _resolution_score(
        self,
        height: int | None,
    ) -> int:
        if height is None:
            return 0

        if height >= 4320:
            return 40

        if height >= 2160:
            return 38

        if height >= 1440:
            return 34

        if height >= 1080:
            return 30

        if height >= 720:
            return 24

        if height >= 576:
            return 17

        if height >= 480:
            return 12

        return 6

    def _codec_score(
        self,
        codec: str,
    ) -> int:
        if codec == "av1":
            return 20

        if codec in {
            "hevc",
            "h265",
            "vp9",
        }:
            return 18

        if codec in {
            "h264",
            "avc",
        }:
            return 15

        if codec in {
            "mpeg4",
            "vp8",
        }:
            return 10

        if codec in {
            "mpeg2video",
            "mpeg1video",
        }:
            return 6

        return 4

    def _bitrate_score(
        self,
        bitrate: int | None,
        height: int | None,
    ) -> int:
        if bitrate is None:
            return 5

        mbps = bitrate / 1_000_000

        if height is None:
            if mbps >= 10:
                return 18

            if mbps >= 5:
                return 14

            if mbps >= 2:
                return 10

            return 6

        if height >= 2160:
            if mbps >= 35:
                return 20

            if mbps >= 20:
                return 16

            if mbps >= 10:
                return 11

            return 5

        if height >= 1080:
            if mbps >= 12:
                return 20

            if mbps >= 7:
                return 16

            if mbps >= 4:
                return 12

            if mbps >= 2:
                return 8

            return 4

        if height >= 720:
            if mbps >= 6:
                return 20

            if mbps >= 3:
                return 16

            if mbps >= 1.5:
                return 12

            if mbps >= 0.8:
                return 8

            return 4

        if mbps >= 2:
            return 18

        if mbps >= 1:
            return 14

        if mbps >= 0.5:
            return 10

        return 5

    def _audio_score(
        self,
        streams: list[dict[str, Any]],
    ) -> int:
        if not streams:
            return 0

        best_score = 2

        for stream in streams:
            codec = str(stream.get("codec_name") or "").lower()

            channels = self._to_int(stream.get("channels")) or 0

            if codec in {
                "truehd",
                "dts",
                "dts_hd",
                "flac",
                "alac",
            }:
                score = 9

            elif codec in {
                "eac3",
                "ac3",
                "opus",
            }:
                score = 7

            elif codec == "aac":
                score = 6

            else:
                score = 4

            if channels >= 6:
                score += 1

            best_score = max(
                best_score,
                min(score, 10),
            )

        return best_score

    def _feature_score(
        self,
        hdr: Any,
        bit_depth: int | None,
        frame_rate: float | None,
        scan_type: Any = None,
    ) -> int:
        score = 0

        if hdr:
            score += 5

        if bit_depth is not None:
            if bit_depth >= 12:
                score += 3
            elif bit_depth >= 10:
                score += 2
            elif bit_depth >= 8:
                score += 1

        if frame_rate is not None:
            if frame_rate >= 50:
                score += 2
            elif frame_rate >= 23:
                score += 1

        scan_text = str(scan_type or "").lower()

        if scan_text == "progressive":
            score += 1

        return min(
            score,
            10,
        )

    def _detect_bit_depth(
        self,
        pixel_format: str,
    ) -> int | None:
        if not pixel_format:
            return None

        if "p16" in pixel_format:
            return 16

        if "p12" in pixel_format:
            return 12

        if "p10" in pixel_format:
            return 10

        if "p9" in pixel_format:
            return 9

        if "yuv" in pixel_format or "rgb" in pixel_format or "gbr" in pixel_format:
            return 8

        return None

    def _quality_level(
        self,
        score: int,
        quality_profile: dict[str, Any],
    ) -> str:
        thresholds = quality_profile.get(
            "thresholds",
            {},
        )

        if score >= int(thresholds.get("excellent", 90)):
            return "excellent"

        if score >= int(thresholds.get("very_good", 75)):
            return "very_good"

        if score >= int(thresholds.get("good", 60)):
            return "good"

        if score >= int(thresholds.get("acceptable", 45)):
            return "acceptable"

        if score >= int(thresholds.get("improvable", 30)):
            return "improvable"

        return "poor"

    def _recommendation(
        self,
        score: int,
        height: int | None,
        video_codec: str,
        audio_quality: str,
        bitrate: int | None,
        audio_channels: int | None,
        quality_profile: dict[str, Any],
    ) -> str:
        level = self._quality_level(
            score,
            quality_profile,
        )

        minimums = quality_profile.get(
            "minimums",
            {},
        )

        minimum_height = int(minimums.get("height", 720))

        minimum_bitrate = int(
            minimums.get(
                "bitrate_bps",
                1_500_000,
            )
        )

        minimum_channels = int(
            minimums.get(
                "audio_channels",
                2,
            )
        )

        problems: list[str] = []

        if height is not None and height < minimum_height:
            problems.append("Auflösung unter dem Profil-Mindestwert")

        if bitrate is not None and bitrate < minimum_bitrate:
            problems.append("Bitrate unter dem Profil-Mindestwert")

        if audio_channels is not None and audio_channels < minimum_channels:
            problems.append("zu wenige Audiokanäle")

        if video_codec in {
            "mpeg1video",
            "mpeg2video",
            "mpeg4",
        }:
            problems.append("veralteter Video-Codec")

        if audio_quality in {
            "none",
            "basic",
        }:
            problems.append("schwache Audioqualität")

        if (
            level
            in {
                "excellent",
                "very_good",
            }
            and not problems
        ):
            return "Qualität erfüllt das gewählte Profil vollständig."

        if level == "good" and not problems:
            return "Qualität ist gut. Eine bessere Fassung ist nicht erforderlich."

        if level == "acceptable":
            prefix = "Noch akzeptabel, aber eine höherwertige Fassung wäre sinnvoll."

        elif level == "improvable":
            prefix = "Qualität ist verbesserungswürdig."

        else:
            prefix = "Bessere Fassung suchen."

        if not problems:
            return prefix

        return prefix + " Gründe: " + ", ".join(problems) + "."

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
