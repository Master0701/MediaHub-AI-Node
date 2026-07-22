from typing import Any

from app.references.fingerprint_compare import (
    FingerprintCompareService,
)


class ReferenceCompareService:
    DEFAULT_ALLOWED_SCORE_DIFFERENCE = 5

    RESOLUTION_RANKS = {
        "low_resolution": 0,
        "sd": 1,
        "hd": 2,
        "full_hd": 3,
        "fhd": 3,
        "qhd": 4,
        "uhd": 5,
        "4k": 5,
        "8k": 6,
    }

    CODEC_RANKS = {
        "mpeg2": 1,
        "mpeg4": 2,
        "xvid": 2,
        "h263": 2,
        "h264": 3,
        "avc": 3,
        "vp8": 3,
        "vp9": 4,
        "h265": 4,
        "hevc": 4,
        "av1": 5,
    }

    AUDIO_QUALITY_RANKS = {
        "unknown": 0,
        "low": 1,
        "standard": 2,
        "good": 3,
        "high": 4,
        "lossless": 5,
    }

    def compare(
        self,
        *,
        reference: dict[str, Any],
        candidate_analysis: dict[str, Any],
        allowed_score_difference: (
            int | float | None
        ) = None,
    ) -> dict[str, Any]:
        reference_quality = self._dict(
            reference.get("quality")
        )

        candidate_media = self._dict(
            candidate_analysis.get("media")
        )

        candidate_quality = self._dict(
            candidate_media.get("quality")
        )

        if not candidate_quality:
            candidate_quality = self._dict(
                candidate_analysis.get("quality")
            )

        reference_analysis = self._dict(
            reference.get("analysis")
        )

        reference_media = self._dict(
            reference_analysis.get("media")
        )

        reference_fingerprint = self._dict(
            reference_media.get(
                "quality_fingerprint"
            )
        )

        candidate_fingerprint = self._dict(
            candidate_media.get(
                "quality_fingerprint"
            )
        )

        if not reference_quality:
            raise ValueError(
                "Die Referenz enthält keine "
                "Qualitätsdaten."
            )

        if not candidate_quality:
            raise ValueError(
                "Die untersuchte Datei enthält "
                "keine Qualitätsdaten."
            )

        reference_score = self._score(
            reference_quality.get("score"),
            reference.get("quality_score"),
        )

        candidate_score = self._score(
            candidate_quality.get("score"),
        )

        if reference_score is None:
            raise ValueError(
                "Die Referenz enthält keinen "
                "gültigen Qualitätsscore."
            )

        if candidate_score is None:
            raise ValueError(
                "Die untersuchte Datei enthält "
                "keinen gültigen Qualitätsscore."
            )

        allowed_difference = (
            self._allowed_difference(
                allowed_score_difference,
                reference,
            )
        )

        score_difference = (
            candidate_score - reference_score
        )

        verdict = self._verdict(
            score_difference,
            allowed_difference,
        )

        categories = {
            "resolution": self._compare_resolution(
                reference_quality=reference_quality,
                candidate_quality=candidate_quality,
            ),
            "video_codec": self._compare_ranked(
                reference_quality.get(
                    "video_codec"
                ),
                candidate_quality.get(
                    "video_codec"
                ),
                self.CODEC_RANKS,
            ),
            "video_bitrate": (
                self._compare_numeric(
                    reference_quality.get(
                        "video_bitrate_bps"
                    ),
                    candidate_quality.get(
                        "video_bitrate_bps"
                    ),
                    tolerance_ratio=0.05,
                )
            ),
            "frame_rate": self._compare_numeric(
                reference_quality.get(
                    "frame_rate"
                ),
                candidate_quality.get(
                    "frame_rate"
                ),
                tolerance_ratio=0.02,
            ),
            "bit_depth": self._compare_numeric(
                reference_quality.get(
                    "bit_depth"
                ),
                candidate_quality.get(
                    "bit_depth"
                ),
            ),
            "hdr": self._compare_boolean_feature(
                reference_quality.get("hdr"),
                candidate_quality.get("hdr"),
            ),
            "audio_channels": (
                self._compare_numeric(
                    reference_quality.get(
                        "audio_channels"
                    ),
                    candidate_quality.get(
                        "audio_channels"
                    ),
                )
            ),
            "audio_quality": self._compare_ranked(
                reference_quality.get(
                    "audio_quality"
                ),
                candidate_quality.get(
                    "audio_quality"
                ),
                self.AUDIO_QUALITY_RANKS,
            ),
            "scan_type": self._compare_scan_type(
                reference_quality.get(
                    "scan_type"
                ),
                candidate_quality.get(
                    "scan_type"
                ),
            ),
        }

        visual_comparison = (
            FingerprintCompareService()
            .compare(
                reference_fingerprint=(
                    reference_fingerprint
                ),
                candidate_fingerprint=(
                    candidate_fingerprint
                ),
            )
        )

        if visual_comparison.get(
            "available",
            False,
        ):
            categories["visual_quality"] = (
                visual_comparison.get(
                    "verdict",
                    "unknown",
                )
            )

        summary = self._category_summary(
            categories
        )

        return {
            "verdict": verdict,
            "reference": {
                "id": reference.get("id"),
                "reference_uuid": (
                    reference.get(
                        "reference_uuid"
                    )
                ),
                "reference_version": (
                    reference.get(
                        "reference_version"
                    )
                ),
                "name": reference.get("name"),
                "quality_profile": (
                    reference.get(
                        "quality_profile"
                    )
                ),
                "score": reference_score,
            },
            "candidate": {
                "file_path": (
                    candidate_analysis.get(
                        "file_path"
                    )
                ),
                "pipeline_version": (
                    candidate_analysis.get(
                        "pipeline_version"
                    )
                ),
                "quality_profile": (
                    self._profile_name(
                        candidate_quality
                    )
                ),
                "score": candidate_score,
            },
            "reference_score": reference_score,
            "candidate_score": candidate_score,
            "score_difference": score_difference,
            "allowed_score_difference": (
                allowed_difference
            ),
            "category_comparison": categories,
            "category_summary": summary,
            "visual_comparison": (
                visual_comparison
            ),
            "recommendation": (
                self._recommendation(
                    verdict=verdict,
                    score_difference=(
                        score_difference
                    ),
                    categories=summary,
                )
            ),
        }

    def _allowed_difference(
        self,
        supplied: int | float | None,
        reference: dict[str, Any],
    ) -> int:
        value = supplied

        if value is None:
            settings = self._dict(
                reference.get(
                    "comparison_settings"
                )
            )

            value = settings.get(
                "allowed_score_difference",
                self.DEFAULT_ALLOWED_SCORE_DIFFERENCE,
            )

        try:
            normalized = int(
                round(float(value))
            )
        except (TypeError, ValueError):
            normalized = (
                self.DEFAULT_ALLOWED_SCORE_DIFFERENCE
            )

        return max(
            0,
            min(
                normalized,
                100,
            ),
        )

    @staticmethod
    def _verdict(
        difference: int,
        allowed_difference: int,
    ) -> str:
        if difference > allowed_difference:
            return "better"

        if difference < -allowed_difference:
            return "worse"

        return "similar"

    @classmethod
    def _compare_resolution(
        cls,
        *,
        reference_quality: dict[str, Any],
        candidate_quality: dict[str, Any],
    ) -> str:
        reference_width = cls._number(
            reference_quality.get("width")
        )

        reference_height = cls._number(
            reference_quality.get("height")
        )

        candidate_width = cls._number(
            candidate_quality.get("width")
        )

        candidate_height = cls._number(
            candidate_quality.get("height")
        )

        if (
            reference_width is not None
            and reference_height is not None
            and candidate_width is not None
            and candidate_height is not None
            and reference_width > 0
            and reference_height > 0
            and candidate_width > 0
            and candidate_height > 0
        ):
            reference_pixels = (
                reference_width
                * reference_height
            )

            candidate_pixels = (
                candidate_width
                * candidate_height
            )

            tolerance = (
                reference_pixels * 0.02
            )

            difference = (
                candidate_pixels
                - reference_pixels
            )

            if abs(difference) <= tolerance:
                return "equal"

            if difference > 0:
                return "better"

            return "worse"

        return cls._compare_ranked(
            reference_quality.get(
                "resolution_class"
            ),
            candidate_quality.get(
                "resolution_class"
            ),
            cls.RESOLUTION_RANKS,
        )

    @staticmethod
    def _compare_numeric(
        reference_value: Any,
        candidate_value: Any,
        *,
        tolerance_ratio: float = 0.0,
    ) -> str:
        reference_number = (
            ReferenceCompareService
            ._number(reference_value)
        )

        candidate_number = (
            ReferenceCompareService
            ._number(candidate_value)
        )

        if (
            reference_number is None
            or candidate_number is None
        ):
            return "unknown"

        tolerance = abs(
            reference_number
        ) * max(
            tolerance_ratio,
            0.0,
        )

        difference = (
            candidate_number
            - reference_number
        )

        if abs(difference) <= tolerance:
            return "equal"

        if difference > 0:
            return "better"

        return "worse"

    @classmethod
    def _compare_ranked(
        cls,
        reference_value: Any,
        candidate_value: Any,
        ranks: dict[str, int],
    ) -> str:
        reference_key = cls._key(
            reference_value
        )

        candidate_key = cls._key(
            candidate_value
        )

        if not reference_key or not candidate_key:
            return "unknown"

        reference_rank = ranks.get(
            reference_key
        )

        candidate_rank = ranks.get(
            candidate_key
        )

        if (
            reference_rank is None
            or candidate_rank is None
        ):
            if reference_key == candidate_key:
                return "equal"

            return "different"

        if candidate_rank == reference_rank:
            return "equal"

        if candidate_rank > reference_rank:
            return "better"

        return "worse"

    @classmethod
    def _compare_boolean_feature(
        cls,
        reference_value: Any,
        candidate_value: Any,
    ) -> str:
        reference_bool = cls._feature_bool(
            reference_value
        )

        candidate_bool = cls._feature_bool(
            candidate_value
        )

        if (
            reference_bool is None
            and candidate_bool is None
        ):
            return "equal"

        if reference_bool == candidate_bool:
            return "equal"

        if candidate_bool and not reference_bool:
            return "better"

        if reference_bool and not candidate_bool:
            return "worse"

        return "unknown"

    @classmethod
    def _compare_scan_type(
        cls,
        reference_value: Any,
        candidate_value: Any,
    ) -> str:
        reference_key = cls._key(
            reference_value
        )

        candidate_key = cls._key(
            candidate_value
        )

        if not reference_key or not candidate_key:
            return "unknown"

        if reference_key == candidate_key:
            return "equal"

        progressive_values = {
            "progressive",
            "progressiv",
        }

        interlaced_values = {
            "interlaced",
            "interlaced_tff",
            "interlaced_bff",
        }

        if (
            candidate_key in progressive_values
            and reference_key in interlaced_values
        ):
            return "better"

        if (
            reference_key in progressive_values
            and candidate_key in interlaced_values
        ):
            return "worse"

        return "different"

    @staticmethod
    def _category_summary(
        categories: dict[str, str],
    ) -> dict[str, Any]:
        better = [
            name
            for name, result
            in categories.items()
            if result == "better"
        ]

        worse = [
            name
            for name, result
            in categories.items()
            if result == "worse"
        ]

        equal = [
            name
            for name, result
            in categories.items()
            if result == "equal"
        ]

        unknown = [
            name
            for name, result
            in categories.items()
            if result in {
                "unknown",
                "different",
            }
        ]

        return {
            "better_count": len(better),
            "worse_count": len(worse),
            "equal_count": len(equal),
            "unknown_count": len(unknown),
            "better": better,
            "worse": worse,
            "equal": equal,
            "unknown": unknown,
        }

    @staticmethod
    def _recommendation(
        *,
        verdict: str,
        score_difference: int,
        categories: dict[str, Any],
    ) -> str:
        worse = categories.get(
            "worse",
            [],
        )

        better = categories.get(
            "better",
            [],
        )

        if verdict == "better":
            text = (
                "Die geprüfte Datei ist besser "
                "als die gespeicherte Referenz."
            )

            if better:
                text += (
                    " Verbesserungen: "
                    + ", ".join(better)
                    + "."
                )

            return text

        if verdict == "worse":
            text = (
                "Die geprüfte Datei ist schlechter "
                "als die gespeicherte Referenz und "
                "sollte nach Möglichkeit ersetzt "
                "oder erneut beschafft werden."
            )

            if worse:
                text += (
                    " Schwächere Bereiche: "
                    + ", ".join(worse)
                    + "."
                )

            return text

        if score_difference == 0:
            text = (
                "Die geprüfte Datei entspricht "
                "beim Gesamtwert der gespeicherten "
                "Referenz."
            )
        else:
            text = (
                "Die geprüfte Datei liegt innerhalb "
                "der erlaubten Abweichung und ist "
                "ungefähr gleichwertig zur Referenz."
            )

        if worse and better:
            text += (
                " Einzelne Qualitätsbereiche "
                "unterscheiden sich jedoch."
            )

        return text

    @staticmethod
    def _profile_name(
        quality: dict[str, Any],
    ) -> str | None:
        profile = quality.get("profile")

        if isinstance(profile, dict):
            value = profile.get("name")
        else:
            value = profile

        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None

    @staticmethod
    def _score(
        *values: Any,
    ) -> int | None:
        for value in values:
            number = (
                ReferenceCompareService
                ._number(value)
            )

            if number is None:
                continue

            return max(
                0,
                min(
                    int(round(number)),
                    100,
                ),
            )

        return None

    @staticmethod
    def _number(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _dict(
        value: Any,
    ) -> dict[str, Any]:
        if isinstance(value, dict):
            return value

        return {}

    @staticmethod
    def _key(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return (
            str(value)
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

    @staticmethod
    def _feature_bool(
        value: Any,
    ) -> bool | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, dict):
            return bool(value)

        text = str(
            value
        ).strip().lower()

        if text in {
            "",
            "none",
            "null",
            "false",
            "no",
            "nein",
            "sdr",
        }:
            return False

        if text in {
            "true",
            "yes",
            "ja",
            "hdr",
            "hdr10",
            "hdr10+",
            "hlg",
            "dolby_vision",
            "dolby vision",
        }:
            return True

        return bool(text)
