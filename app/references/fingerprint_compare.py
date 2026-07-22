from __future__ import annotations

from typing import Any


class FingerprintCompareService:
    """
    Vergleicht zwei visuelle Qualitäts-Fingerprints.

    Version 2 berücksichtigt Zusammenhänge zwischen
    einzelnen Messwerten. Dadurch werden starke
    Weichzeichnung und Detailverlust nicht mehr
    fälschlich als Entrauschungs- oder
    Blockbildungsverbesserung gewertet.
    """

    VERSION = "2"

    METRICS = {
        "sharpness": {
            "direction": "higher",
            "tolerance": 0.10,
            "weight": 2.50,
        },
        "noise": {
            "direction": "lower",
            "tolerance": 0.15,
            "weight": 1.00,
        },
        "blockiness": {
            "direction": "lower",
            "tolerance": 0.12,
            "weight": 1.25,
        },
        "clipped_white_ratio": {
            "direction": "lower",
            "tolerance": 0.20,
            "weight": 0.60,
        },
        "black_ratio": {
            "direction": "neutral",
            "tolerance": 0.20,
            "weight": 0.35,
        },
        "brightness": {
            "direction": "neutral",
            "tolerance": 0.10,
            "weight": 0.35,
        },
        "contrast": {
            "direction": "neutral",
            "tolerance": 0.10,
            "weight": 0.85,
        },
        "saturation": {
            "direction": "neutral",
            "tolerance": 0.12,
            "weight": 0.40,
        },
    }

    def compare(
        self,
        *,
        reference_fingerprint: dict[str, Any],
        candidate_fingerprint: dict[str, Any],
    ) -> dict[str, Any]:
        if not reference_fingerprint:
            return self._unavailable("Die Referenz enthält keinen Quality-Fingerprint.")

        if not candidate_fingerprint:
            return self._unavailable("Die geprüfte Datei enthält keinen Quality-Fingerprint.")

        metrics: dict[str, dict[str, Any]] = {}

        for metric_name, config in self.METRICS.items():
            reference_value = self._metric_average(
                reference_fingerprint,
                metric_name,
            )

            candidate_value = self._metric_average(
                candidate_fingerprint,
                metric_name,
            )

            metrics[metric_name] = self._compare_metric(
                reference_value=reference_value,
                candidate_value=candidate_value,
                direction=str(config["direction"]),
                tolerance=float(config["tolerance"]),
            )

        quality_events = self._apply_context_rules(metrics)

        (
            metric_similarity,
            visual_difference,
        ) = self._aggregate_metrics(metrics)

        hash_comparison = self._compare_hashes(
            reference_fingerprint,
            candidate_fingerprint,
        )

        hash_similarity = hash_comparison.get("similarity_percent")

        overall_similarity = self._overall_similarity(
            metric_similarity=metric_similarity,
            hash_similarity=hash_similarity,
        )

        verdict = self._verdict(
            visual_difference=visual_difference,
            metrics=metrics,
            quality_events=quality_events,
        )

        compared_count = sum(1 for value in metrics.values() if value["status"] != "unknown")

        return {
            "available": compared_count > 0,
            "version": self.VERSION,
            "verdict": verdict,
            "visual_difference_percent": round(
                visual_difference,
                2,
            ),
            "similarity_percent": (
                round(overall_similarity, 2) if overall_similarity is not None else None
            ),
            "metric_similarity_percent": (
                round(metric_similarity, 2) if metric_similarity is not None else None
            ),
            "compared_metric_count": compared_count,
            "quality_events": quality_events,
            "metrics": metrics,
            "perceptual_hash": hash_comparison,
            "reference": {
                "sample_count": self._integer(reference_fingerprint.get("sample_count")),
                "representative_hash": (reference_fingerprint.get("representative_hash")),
            },
            "candidate": {
                "sample_count": self._integer(candidate_fingerprint.get("sample_count")),
                "representative_hash": (candidate_fingerprint.get("representative_hash")),
            },
        }

    def _apply_context_rules(
        self,
        metrics: dict[str, dict[str, Any]],
    ) -> list[str]:
        events: list[str] = []

        sharpness = metrics.get("sharpness", {})
        noise = metrics.get("noise", {})
        blockiness = metrics.get("blockiness", {})
        contrast = metrics.get("contrast", {})

        sharpness_difference = self._number(sharpness.get("difference_percent"))

        contrast_difference = self._number(contrast.get("difference_percent"))

        strong_detail_loss = sharpness_difference is not None and sharpness_difference <= -25.0

        severe_detail_loss = sharpness_difference is not None and sharpness_difference <= -60.0

        apparent_denoising = noise.get("status") == "better"

        apparent_deblocking = blockiness.get("status") == "better"

        contrast_loss = contrast_difference is not None and contrast_difference <= -12.0

        blur_detected = strong_detail_loss and (
            apparent_denoising or apparent_deblocking or contrast_loss
        )

        if strong_detail_loss:
            events.append("detail_loss")

        if severe_detail_loss:
            events.append("severe_detail_loss")

        if blur_detected:
            events.append("blur_detected")

        if strong_detail_loss and apparent_denoising:
            self._invalidate_false_improvement(
                noise,
                reason=(
                    "Der niedrigere Noise-Wert wird "
                    "wegen gleichzeitigem starkem "
                    "Detailverlust nicht als "
                    "Verbesserung gewertet."
                ),
            )

        if strong_detail_loss and apparent_deblocking:
            self._invalidate_false_improvement(
                blockiness,
                reason=(
                    "Der niedrigere Blockiness-Wert "
                    "wird wegen gleichzeitigem "
                    "starkem Detailverlust nicht als "
                    "Verbesserung gewertet."
                ),
            )

        clipped_white = metrics.get(
            "clipped_white_ratio",
            {},
        )

        if strong_detail_loss and clipped_white.get("status") == "better":
            self._invalidate_false_improvement(
                clipped_white,
                reason=(
                    "Weniger helle Spitzlichter "
                    "werden bei starkem Detailverlust "
                    "nicht als Qualitätsverbesserung "
                    "gewertet."
                ),
            )

        return events

    @staticmethod
    def _invalidate_false_improvement(
        metric: dict[str, Any],
        *,
        reason: str,
    ) -> None:
        metric["original_status"] = metric.get("status")
        metric["status"] = "context_neutral"
        metric["directional_score"] = 0.0
        metric["context_adjusted"] = True
        metric["context_reason"] = reason

    def _aggregate_metrics(
        self,
        metrics: dict[str, dict[str, Any]],
    ) -> tuple[float | None, float]:
        weighted_direction = 0.0
        directional_weight = 0.0

        weighted_similarity = 0.0
        similarity_weight = 0.0

        for metric_name, result in metrics.items():
            if result.get("status") == "unknown":
                continue

            config = self.METRICS.get(
                metric_name,
                {},
            )

            weight = float(config.get("weight", 1.0))

            similarity = self._number(result.get("similarity_percent"))

            if similarity is not None:
                weighted_similarity += similarity * weight
                similarity_weight += weight

            directional_value = self._number(result.get("directional_score"))

            if directional_value is not None:
                weighted_direction += directional_value * weight
                directional_weight += weight

        if similarity_weight > 0:
            metric_similarity = weighted_similarity / similarity_weight
        else:
            metric_similarity = None

        if directional_weight > 0:
            visual_difference = weighted_direction / directional_weight
        else:
            visual_difference = 0.0

        return (
            metric_similarity,
            visual_difference,
        )

    @staticmethod
    def _verdict(
        *,
        visual_difference: float,
        metrics: dict[str, dict[str, Any]],
        quality_events: list[str],
    ) -> str:
        sharpness_difference = FingerprintCompareService._number(
            metrics.get(
                "sharpness",
                {},
            ).get("difference_percent")
        )

        if "severe_detail_loss" in quality_events:
            return "worse"

        if "blur_detected" in quality_events:
            return "worse"

        if sharpness_difference is not None and sharpness_difference <= -25.0:
            return "worse"

        if visual_difference > 7.5:
            return "better"

        if visual_difference < -7.5:
            return "worse"

        return "similar"

    @staticmethod
    def _compare_metric(
        *,
        reference_value: float | None,
        candidate_value: float | None,
        direction: str,
        tolerance: float,
    ) -> dict[str, Any]:
        if reference_value is None or candidate_value is None:
            return {
                "status": "unknown",
                "reference": reference_value,
                "candidate": candidate_value,
                "difference": None,
                "difference_percent": None,
                "similarity_percent": None,
                "directional_score": None,
            }

        difference = candidate_value - reference_value

        denominator = max(
            abs(reference_value),
            0.000001,
        )

        difference_ratio = difference / denominator

        absolute_ratio = abs(difference_ratio)

        similarity = max(
            0.0,
            100.0
            - min(
                absolute_ratio * 100.0,
                100.0,
            ),
        )

        if absolute_ratio <= tolerance:
            status = "equal"
            directional_score = 0.0
        elif direction == "higher":
            if difference > 0:
                status = "better"
                directional_score = min(
                    difference_ratio * 100.0,
                    100.0,
                )
            else:
                status = "worse"
                directional_score = max(
                    difference_ratio * 100.0,
                    -100.0,
                )
        elif direction == "lower":
            if difference < 0:
                status = "better"
                directional_score = min(
                    abs(difference_ratio) * 100.0,
                    100.0,
                )
            else:
                status = "worse"
                directional_score = max(
                    -abs(difference_ratio) * 100.0,
                    -100.0,
                )
        else:
            status = "different"
            directional_score = None

        return {
            "status": status,
            "reference": round(
                reference_value,
                6,
            ),
            "candidate": round(
                candidate_value,
                6,
            ),
            "difference": round(
                difference,
                6,
            ),
            "difference_percent": round(
                difference_ratio * 100.0,
                2,
            ),
            "similarity_percent": round(
                similarity,
                2,
            ),
            "directional_score": (
                round(
                    directional_score,
                    2,
                )
                if directional_score is not None
                else None
            ),
        }

    @classmethod
    def _compare_hashes(
        cls,
        reference_fingerprint: dict[str, Any],
        candidate_fingerprint: dict[str, Any],
    ) -> dict[str, Any]:
        reference_hash = cls._hash_text(reference_fingerprint.get("representative_hash"))

        candidate_hash = cls._hash_text(candidate_fingerprint.get("representative_hash"))

        if not reference_hash or not candidate_hash:
            return {
                "available": False,
                "reference_hash": reference_hash,
                "candidate_hash": candidate_hash,
                "hamming_distance": None,
                "bit_count": None,
                "similarity_percent": None,
            }

        if len(reference_hash) != len(candidate_hash):
            return {
                "available": False,
                "reference_hash": reference_hash,
                "candidate_hash": candidate_hash,
                "hamming_distance": None,
                "bit_count": None,
                "similarity_percent": None,
                "warning": ("Die Hash-Längen stimmen nicht überein."),
            }

        try:
            reference_number = int(
                reference_hash,
                16,
            )
            candidate_number = int(
                candidate_hash,
                16,
            )
        except ValueError:
            return {
                "available": False,
                "reference_hash": reference_hash,
                "candidate_hash": candidate_hash,
                "hamming_distance": None,
                "bit_count": None,
                "similarity_percent": None,
                "warning": ("Mindestens ein Hash ist ungültig."),
            }

        bit_count = len(reference_hash) * 4

        hamming_distance = (reference_number ^ candidate_number).bit_count()

        similarity = 100.0 * (bit_count - hamming_distance) / bit_count

        return {
            "available": True,
            "reference_hash": reference_hash,
            "candidate_hash": candidate_hash,
            "hamming_distance": hamming_distance,
            "bit_count": bit_count,
            "similarity_percent": round(
                similarity,
                2,
            ),
        }

    @staticmethod
    def _overall_similarity(
        *,
        metric_similarity: float | None,
        hash_similarity: Any,
    ) -> float | None:
        hash_value = FingerprintCompareService._number(hash_similarity)

        if metric_similarity is None and hash_value is None:
            return None

        if metric_similarity is None:
            return hash_value

        if hash_value is None:
            return metric_similarity

        return metric_similarity * 0.90 + hash_value * 0.10

    @staticmethod
    def _metric_average(
        fingerprint: dict[str, Any],
        metric_name: str,
    ) -> float | None:
        value = fingerprint.get(metric_name)

        if isinstance(value, dict):
            value = value.get("average")

        return FingerprintCompareService._number(value)

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
    def _integer(
        value: Any,
    ) -> int | None:
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _hash_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()

        return normalized or None

    @classmethod
    def _unavailable(
        cls,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "available": False,
            "version": cls.VERSION,
            "verdict": "unknown",
            "visual_difference_percent": None,
            "similarity_percent": None,
            "metric_similarity_percent": None,
            "compared_metric_count": 0,
            "quality_events": [],
            "metrics": {},
            "perceptual_hash": {
                "available": False,
                "similarity_percent": None,
            },
            "reason": reason,
        }
