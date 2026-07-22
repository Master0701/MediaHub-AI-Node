from datetime import datetime, timezone

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
    BaseAnalyzer,
)


def timestamp_to_iso(
    value: float,
) -> str:
    return datetime.fromtimestamp(
        value,
        tz=timezone.utc,
    ).isoformat()


class FilesystemAnalyzer(BaseAnalyzer):
    name = "filesystem"
    priority = 20

    required_tools = []

    capabilities = [
        "file_exists",
        "file_size",
        "file_times",
        "file_permissions",
    ]

    def analyze(
        self,
        context: AnalyzerContext,
    ) -> AnalyzerResult:
        file_path = context.file_path

        if not file_path.exists():
            return AnalyzerResult(
                analyzer=self.name,
                success=True,
                data={
                    "exists": False,
                    "is_file": False,
                    "is_directory": False,
                    "absolute_path": str(
                        file_path.absolute()
                    ),
                },
                warnings=[
                    "Die Mediendatei existiert "
                    "auf diesem KI-Knoten nicht."
                ],
            )

        stat = file_path.stat()

        data = {
            "exists": True,
            "is_file": file_path.is_file(),
            "is_directory": (
                file_path.is_dir()
            ),
            "absolute_path": str(
                file_path.resolve()
            ),
            "parent_directory": str(
                file_path.parent.resolve()
            ),
            "file_size_bytes": (
                stat.st_size
            ),
            "created_utc": timestamp_to_iso(
                stat.st_ctime
            ),
            "modified_utc": timestamp_to_iso(
                stat.st_mtime
            ),
            "accessed_utc": timestamp_to_iso(
                stat.st_atime
            ),
            "permissions_octal": oct(
                stat.st_mode & 0o777
            ),
        }

        return AnalyzerResult(
            analyzer=self.name,
            success=True,
            data=data,
        )
