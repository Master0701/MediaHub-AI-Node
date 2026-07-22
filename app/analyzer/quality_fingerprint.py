from pathlib import Path
from typing import Any

import cv2
import imagehash
import numpy as np
from PIL import Image

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
    BaseAnalyzer,
)


class QualityFingerprintAnalyzer(BaseAnalyzer):
    name = "quality_fingerprint"
    priority = 38

    required_tools: list[str] = []

    capabilities = [
        "visual_quality_fingerprint",
        "brightness_analysis",
        "contrast_analysis",
        "sharpness_analysis",
        "noise_analysis",
        "saturation_analysis",
        "black_frame_detection",
        "blockiness_estimation",
        "perceptual_hash",
    ]

    DEFAULT_SAMPLE_COUNT = 8
    MIN_SAMPLE_COUNT = 3
    MAX_SAMPLE_COUNT = 24

    def can_analyze(
        self,
        context: AnalyzerContext,
    ) -> bool:
        return (
            context.file_path.exists()
            and context.file_path.is_file()
            and bool(
                context.shared_data.get(
                    "video_streams"
                )
            )
        )

    def analyze(
        self,
        context: AnalyzerContext,
    ) -> AnalyzerResult:
        sample_count = self._sample_count(
            context.options.get(
                "fingerprint_sample_count",
                self.DEFAULT_SAMPLE_COUNT,
            )
        )

        maximum_width = self._positive_int(
            context.options.get(
                "fingerprint_max_width",
                640,
            ),
            fallback=640,
        )

        capture = cv2.VideoCapture(
            str(context.file_path)
        )

        if not capture.isOpened():
            return AnalyzerResult(
                analyzer=self.name,
                success=False,
                errors=[
                    "OpenCV konnte die Videodatei "
                    "nicht öffnen."
                ],
            )

        try:
            duration_seconds = (
                self._duration_seconds(
                    context,
                    capture,
                )
            )

            timestamps = self._timestamps(
                duration_seconds,
                sample_count,
            )

            samples: list[dict[str, Any]] = []
            warnings: list[str] = []

            for index, timestamp in enumerate(
                timestamps,
                start=1,
            ):
                frame = self._read_frame(
                    capture,
                    timestamp,
                )

                if frame is None:
                    warnings.append(
                        "Stichprobenbild "
                        f"{index} bei "
                        f"{timestamp:.3f} Sekunden "
                        "konnte nicht gelesen werden."
                    )
                    continue

                frame = self._resize_frame(
                    frame,
                    maximum_width,
                )

                metrics = self._analyze_frame(
                    frame
                )

                metrics["sample_index"] = index
                metrics["timestamp_seconds"] = (
                    round(timestamp, 3)
                )

                samples.append(metrics)

            if not samples:
                return AnalyzerResult(
                    analyzer=self.name,
                    success=False,
                    errors=[
                        "Es konnte kein geeignetes "
                        "Stichprobenbild aus dem Video "
                        "gelesen werden."
                    ],
                    warnings=warnings,
                )

            fingerprint = self._aggregate(
                samples=samples,
                requested_sample_count=(
                    sample_count
                ),
                duration_seconds=duration_seconds,
            )

            return AnalyzerResult(
                analyzer=self.name,
                success=True,
                data={
                    "quality_fingerprint": (
                        fingerprint
                    )
                },
                warnings=warnings,
            )

        finally:
            capture.release()

    def _analyze_frame(
        self,
        frame: np.ndarray,
    ) -> dict[str, Any]:
        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        hsv = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2HSV,
        )

        brightness = float(
            np.mean(gray)
        )

        contrast = float(
            np.std(gray)
        )

        sharpness = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F,
            ).var()
        )

        saturation = float(
            np.mean(hsv[:, :, 1])
        )

        black_ratio = float(
            np.mean(gray <= 16)
        )

        clipped_white_ratio = float(
            np.mean(gray >= 245)
        )

        noise = self._estimate_noise(
            gray
        )

        blockiness = self._estimate_blockiness(
            gray
        )

        perceptual_hash = (
            self._perceptual_hash(frame)
        )

        return {
            "brightness": round(
                brightness,
                4,
            ),
            "contrast": round(
                contrast,
                4,
            ),
            "sharpness": round(
                sharpness,
                4,
            ),
            "noise": round(
                noise,
                4,
            ),
            "saturation": round(
                saturation,
                4,
            ),
            "black_ratio": round(
                black_ratio,
                6,
            ),
            "clipped_white_ratio": round(
                clipped_white_ratio,
                6,
            ),
            "blockiness": round(
                blockiness,
                4,
            ),
            "perceptual_hash": (
                perceptual_hash
            ),
            "width": int(
                frame.shape[1]
            ),
            "height": int(
                frame.shape[0]
            ),
        }

    def _aggregate(
        self,
        *,
        samples: list[dict[str, Any]],
        requested_sample_count: int,
        duration_seconds: float,
    ) -> dict[str, Any]:
        brightness = self._values(
            samples,
            "brightness",
        )

        contrast = self._values(
            samples,
            "contrast",
        )

        sharpness = self._values(
            samples,
            "sharpness",
        )

        noise = self._values(
            samples,
            "noise",
        )

        saturation = self._values(
            samples,
            "saturation",
        )

        black_ratio = self._values(
            samples,
            "black_ratio",
        )

        clipped_white = self._values(
            samples,
            "clipped_white_ratio",
        )

        blockiness = self._values(
            samples,
            "blockiness",
        )

        hashes = [
            str(sample["perceptual_hash"])
            for sample in samples
            if sample.get(
                "perceptual_hash"
            )
        ]

        average_sharpness = self._average(
            sharpness
        )

        average_noise = self._average(
            noise
        )

        average_blockiness = self._average(
            blockiness
        )

        black_frame_count = sum(
            1
            for value in black_ratio
            if value >= 0.90
        )

        dark_frame_count = sum(
            1
            for value in brightness
            if value <= 25.0
        )

        return {
            "version": "1",
            "analyzer": self.name,
            "requested_sample_count": (
                requested_sample_count
            ),
            "sample_count": len(samples),
            "duration_seconds": round(
                duration_seconds,
                3,
            ),
            "brightness": self._statistics(
                brightness
            ),
            "contrast": self._statistics(
                contrast
            ),
            "sharpness": {
                **self._statistics(
                    sharpness
                ),
                "level": self._sharpness_level(
                    average_sharpness
                ),
            },
            "noise": {
                **self._statistics(noise),
                "level": self._noise_level(
                    average_noise
                ),
            },
            "saturation": self._statistics(
                saturation
            ),
            "black_ratio": self._statistics(
                black_ratio
            ),
            "clipped_white_ratio": (
                self._statistics(
                    clipped_white
                )
            ),
            "blockiness": {
                **self._statistics(
                    blockiness
                ),
                "level": (
                    self._blockiness_level(
                        average_blockiness
                    )
                ),
            },
            "black_frame_count": (
                black_frame_count
            ),
            "dark_frame_count": (
                dark_frame_count
            ),
            "black_frame_ratio": round(
                black_frame_count
                / max(len(samples), 1),
                6,
            ),
            "perceptual_hashes": hashes,
            "representative_hash": (
                self._representative_hash(
                    hashes
                )
            ),
            "samples": samples,
        }

    @staticmethod
    def _read_frame(
        capture: cv2.VideoCapture,
        timestamp: float,
    ) -> np.ndarray | None:
        capture.set(
            cv2.CAP_PROP_POS_MSEC,
            max(timestamp, 0.0) * 1000.0,
        )

        success, frame = capture.read()

        if not success or frame is None:
            return None

        if frame.size == 0:
            return None

        return frame

    @staticmethod
    def _resize_frame(
        frame: np.ndarray,
        maximum_width: int,
    ) -> np.ndarray:
        height, width = frame.shape[:2]

        if width <= maximum_width:
            return frame

        scale = maximum_width / width

        target_width = maximum_width
        target_height = max(
            1,
            int(round(height * scale)),
        )

        return cv2.resize(
            frame,
            (
                target_width,
                target_height,
            ),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def _estimate_noise(
        gray: np.ndarray,
    ) -> float:
        blurred = cv2.GaussianBlur(
            gray,
            (3, 3),
            0,
        )

        difference = cv2.absdiff(
            gray,
            blurred,
        )

        return float(
            np.mean(difference)
        )

    @staticmethod
    def _estimate_blockiness(
        gray: np.ndarray,
    ) -> float:
        image = gray.astype(
            np.float32
        )

        vertical_values = []

        for column in range(
            8,
            image.shape[1],
            8,
        ):
            difference = np.abs(
                image[:, column]
                - image[:, column - 1]
            )

            vertical_values.append(
                float(np.mean(difference))
            )

        horizontal_values = []

        for row in range(
            8,
            image.shape[0],
            8,
        ):
            difference = np.abs(
                image[row, :]
                - image[row - 1, :]
            )

            horizontal_values.append(
                float(np.mean(difference))
            )

        values = (
            vertical_values
            + horizontal_values
        )

        if not values:
            return 0.0

        return float(
            np.mean(values)
        )

    @staticmethod
    def _perceptual_hash(
        frame: np.ndarray,
    ) -> str | None:
        try:
            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            image = Image.fromarray(rgb)

            return str(
                imagehash.phash(image)
            )

        except Exception:
            return None

    @staticmethod
    def _duration_seconds(
        context: AnalyzerContext,
        capture: cv2.VideoCapture,
    ) -> float:
        duration = context.shared_data.get(
            "duration_seconds"
        )

        try:
            parsed = float(duration)

            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            pass

        frame_count = capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )

        frame_rate = capture.get(
            cv2.CAP_PROP_FPS
        )

        if frame_count > 0 and frame_rate > 0:
            return float(
                frame_count / frame_rate
            )

        return 1.0

    @staticmethod
    def _timestamps(
        duration_seconds: float,
        sample_count: int,
    ) -> list[float]:
        duration = max(
            float(duration_seconds),
            1.0,
        )

        if sample_count <= 1:
            return [
                duration * 0.5
            ]

        start_ratio = 0.05
        end_ratio = 0.95

        return [
            duration
            * (
                start_ratio
                + (
                    end_ratio
                    - start_ratio
                )
                * index
                / (sample_count - 1)
            )
            for index in range(
                sample_count
            )
        ]

    @classmethod
    def _sample_count(
        cls,
        value: Any,
    ) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = (
                cls.DEFAULT_SAMPLE_COUNT
            )

        return max(
            cls.MIN_SAMPLE_COUNT,
            min(
                parsed,
                cls.MAX_SAMPLE_COUNT,
            ),
        )

    @staticmethod
    def _positive_int(
        value: Any,
        *,
        fallback: int,
    ) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback

        if parsed < 1:
            return fallback

        return parsed

    @staticmethod
    def _values(
        samples: list[dict[str, Any]],
        key: str,
    ) -> list[float]:
        values = []

        for sample in samples:
            value = sample.get(key)

            try:
                values.append(
                    float(value)
                )
            except (TypeError, ValueError):
                continue

        return values

    @staticmethod
    def _average(
        values: list[float],
    ) -> float:
        if not values:
            return 0.0

        return float(
            np.mean(values)
        )

    @staticmethod
    def _statistics(
        values: list[float],
    ) -> dict[str, float | None]:
        if not values:
            return {
                "average": None,
                "minimum": None,
                "maximum": None,
                "median": None,
            }

        array = np.asarray(
            values,
            dtype=np.float64,
        )

        return {
            "average": round(
                float(np.mean(array)),
                4,
            ),
            "minimum": round(
                float(np.min(array)),
                4,
            ),
            "maximum": round(
                float(np.max(array)),
                4,
            ),
            "median": round(
                float(np.median(array)),
                4,
            ),
        }

    @staticmethod
    def _sharpness_level(
        value: float,
    ) -> str:
        if value < 40:
            return "very_low"

        if value < 100:
            return "low"

        if value < 250:
            return "medium"

        if value < 600:
            return "good"

        return "very_high"

    @staticmethod
    def _noise_level(
        value: float,
    ) -> str:
        if value < 2.5:
            return "very_low"

        if value < 5.0:
            return "low"

        if value < 9.0:
            return "medium"

        if value < 15.0:
            return "high"

        return "very_high"

    @staticmethod
    def _blockiness_level(
        value: float,
    ) -> str:
        if value < 4.0:
            return "very_low"

        if value < 8.0:
            return "low"

        if value < 14.0:
            return "medium"

        if value < 22.0:
            return "high"

        return "very_high"

    @staticmethod
    def _representative_hash(
        hashes: list[str],
    ) -> str | None:
        if not hashes:
            return None

        return hashes[
            len(hashes) // 2
        ]
