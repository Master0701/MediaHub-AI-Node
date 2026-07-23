from app.jobs.base import BaseJobHandler
from app.jobs.cache_purge import CachePurgeHandler
from app.jobs.knowledge_search import (
    KnowledgeSearchHandler,
)
from app.jobs.media_analyze import MediaAnalyzeHandler
from app.jobs.provider_execute import (
    ProviderExecuteHandler,
)
from app.jobs.reference_create import (
    ReferenceCreateHandler,
)
from app.jobs.reference_compare import (
    ReferenceCompareHandler,
)
from app.jobs.system_test import SystemTestHandler


class JobHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[
            str,
            BaseJobHandler,
        ] = {}

    def register(
        self,
        handler: BaseJobHandler,
    ) -> None:
        self._handlers[
            handler.job_type
        ] = handler

    def get(
        self,
        job_type: str,
    ) -> BaseJobHandler | None:
        return self._handlers.get(
            job_type
        )

    def require(
        self,
        job_type: str,
    ) -> BaseJobHandler:
        handler = self.get(job_type)

        if handler is None:
            raise ValueError(
                f"Unbekannter Job-Typ: "
                f"{job_type}"
            )

        return handler

    def list_types(self) -> list[str]:
        return sorted(
            self._handlers.keys()
        )


job_handler_registry = JobHandlerRegistry()

job_handler_registry.register(
    SystemTestHandler()
)
job_handler_registry.register(
    ProviderExecuteHandler()
)
job_handler_registry.register(
    CachePurgeHandler()
)
job_handler_registry.register(
    KnowledgeSearchHandler()
)
job_handler_registry.register(
    MediaAnalyzeHandler()
)
job_handler_registry.register(
    ReferenceCreateHandler()
)
job_handler_registry.register(
    ReferenceCompareHandler()
)
