import re
from typing import Any

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
    BaseAnalyzer,
)


class FilenameAnalyzer(BaseAnalyzer):
    name = "filename"
    priority = 10

    required_tools = []

    capabilities = [
        "filename",
        "cleaned_name",
        "title_candidate",
        "year",
        "season",
        "episode",
        "edition",
        "media_type",
    ]

    EDITION_PATTERNS = {
        "uncut": r"\buncut\b",
        "extended": r"\bextended(?:[ ._-]*cut)?\b",
        "directors_cut": (
            r"\bdirector(?:'s|s)?[ ._-]*cut\b"
        ),
        "theatrical_cut": (
            r"\btheatrical(?:[ ._-]*cut)?\b"
        ),
        "remastered": r"\bremaster(?:ed)?\b",
        "special_edition": (
            r"\bspecial[ ._-]*edition\b"
        ),
        "anniversary_edition": (
            r"\banniversary[ ._-]*edition\b"
        ),
        "ultimate_edition": (
            r"\bultimate[ ._-]*edition\b"
        ),
    }

    TECHNICAL_PATTERNS = [
        r"\b2160p\b",
        r"\b1080p\b",
        r"\b1080i\b",
        r"\b720p\b",
        r"\b576p\b",
        r"\b480p\b",
        r"\b4k\b",
        r"\buhd\b",
        r"\bhdr10\+?\b",
        r"\bdolby[ ._-]*vision\b",
        r"\bbluray\b",
        r"\bblu[ ._-]*ray\b",
        r"\bweb[ ._-]*dl\b",
        r"\bwebrip\b",
        r"\bhdtv\b",
        r"\bdvdrip\b",
        r"\bx264\b",
        r"\bx265\b",
        r"\bh\.?264\b",
        r"\bh\.?265\b",
        r"\bhevc\b",
        r"\bav1\b",
        r"\baac\b",
        r"\bac3\b",
        r"\beac3\b",
        r"\bdts\b",
        r"\btruehd\b",
        r"\batmos\b",
    ]

    def analyze(
        self,
        context: AnalyzerContext,
    ) -> AnalyzerResult:
        file_path = context.file_path

        filename = file_path.name
        stem = file_path.stem
        extension = file_path.suffix.lower()

        cleaned_name = re.sub(
            r"[\._]+",
            " ",
            stem,
        )

        cleaned_name = re.sub(
            r"[\[\]\{\}]",
            " ",
            cleaned_name,
        )

        cleaned_name = re.sub(
            r"\s+",
            " ",
            cleaned_name,
        ).strip()

        year_match = re.search(
            r"\b(18\d{2}|19\d{2}|20\d{2})\b",
            cleaned_name,
        )

        episode_match = re.search(
            r"\bS(\d{1,3})[ ._-]*E(\d{1,3})\b",
            cleaned_name,
            re.IGNORECASE,
        )

        if episode_match is None:
            episode_match = re.search(
                r"\b(\d{1,2})x(\d{1,3})\b",
                cleaned_name,
                re.IGNORECASE,
            )

        editions = self._detect_editions(
            cleaned_name
        )

        title_candidate = self._build_title(
            cleaned_name,
            year_match,
            episode_match,
        )

        likely_media_type = (
            "episode"
            if episode_match
            else "movie"
        )

        data: dict[str, Any] = {
            "filename": filename,
            "stem": stem,
            "extension": extension,
            "cleaned_name": cleaned_name,
            "title_candidate": title_candidate,
            "likely_media_type": likely_media_type,
            "year": (
                int(year_match.group(1))
                if year_match
                else None
            ),
            "season": (
                int(episode_match.group(1))
                if episode_match
                else None
            ),
            "episode": (
                int(episode_match.group(2))
                if episode_match
                else None
            ),
            "editions": editions,
        }

        return AnalyzerResult(
            analyzer=self.name,
            success=True,
            data=data,
        )

    def _detect_editions(
        self,
        cleaned_name: str,
    ) -> list[str]:
        editions: list[str] = []

        for edition, pattern in (
            self.EDITION_PATTERNS.items()
        ):
            if re.search(
                pattern,
                cleaned_name,
                re.IGNORECASE,
            ):
                editions.append(edition)

        return editions

    def _build_title(
        self,
        cleaned_name: str,
        year_match,
        episode_match,
    ) -> str:
        title = cleaned_name

        cut_positions = []

        if episode_match:
            cut_positions.append(
                episode_match.start()
            )

        if year_match:
            cut_positions.append(
                year_match.start()
            )

        if cut_positions:
            title = title[
                :min(cut_positions)
            ]

        for pattern in self.TECHNICAL_PATTERNS:
            title = re.sub(
                pattern,
                " ",
                title,
                flags=re.IGNORECASE,
            )

        for pattern in (
            self.EDITION_PATTERNS.values()
        ):
            title = re.sub(
                pattern,
                " ",
                title,
                flags=re.IGNORECASE,
            )

        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip(" -._")

        return title
