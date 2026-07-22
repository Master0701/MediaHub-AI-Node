from collections import deque
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.knowledge.constants import (
    normalize_relation_type,
)
from app.knowledge.models import (
    KnowledgeItem,
    KnowledgeRelation,
)
from app.knowledge.service import (
    decode_json,
    item_to_dict,
    relation_to_dict,
)


class KnowledgeGraphService:
    """
    Liest und analysiert Beziehungen innerhalb der
    MediaHub-Wissensdatenbank.

    Der Service verändert keine Datenbankeinträge.
    """

    DIRECTED_RELATION_TYPES = {
        "prequel",
        "sequel",
        "spin_off",
        "remake",
        "reboot",
        "takes_place_before",
        "takes_place_after",
        "continues",
        "adaptation_of",
        "based_on",
        "parent_series",
        "child_series",
    }

    SYMMETRIC_RELATION_TYPES = {
        "crossover",
        "shared_universe",
        "same_franchise",
        "same_collection",
        "related",
    }

    ORDER_RELATION_TYPES = {
        "chronological_order",
        "release_order",
        "watch_order",
    }

    INVERSE_RELATION_TYPES = {
        "prequel": "sequel",
        "sequel": "prequel",
        "takes_place_before": "takes_place_after",
        "takes_place_after": "takes_place_before",
        "parent_series": "child_series",
        "child_series": "parent_series",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_direct_relations(
        self,
        item_id: int,
        *,
        relation_type: str | None = None,
        include_incoming: bool = True,
        include_outgoing: bool = True,
    ) -> list[dict[str, Any]]:
        self._require_item(item_id)

        statement = select(KnowledgeRelation)

        direction_filters = []

        if include_outgoing:
            direction_filters.append(
                KnowledgeRelation.source_id == item_id
            )

        if include_incoming:
            direction_filters.append(
                KnowledgeRelation.target_id == item_id
            )

        if not direction_filters:
            return []

        statement = statement.where(
            or_(*direction_filters)
        )

        normalized_type = self._normalize(
            relation_type
        )

        if normalized_type:
            statement = statement.where(
                KnowledgeRelation.relation_type
                == normalized_type
            )

        statement = statement.order_by(
            KnowledgeRelation.relation_type.asc(),
            KnowledgeRelation.order_type.asc(),
            KnowledgeRelation.position.asc(),
            KnowledgeRelation.id.asc(),
        )

        relations = list(
            self.db.scalars(statement).all()
        )

        return [
            self._relation_with_direction(
                relation=relation,
                item_id=item_id,
            )
            for relation in relations
        ]

    def get_connected_items(
        self,
        item_id: int,
        *,
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        relations = self.get_direct_relations(
            item_id=item_id,
            relation_type=relation_type,
        )

        connected_ids: list[int] = []
        seen_ids: set[int] = set()

        for relation in relations:
            connected_id = relation[
                "connected_item_id"
            ]

            if connected_id in seen_ids:
                continue

            seen_ids.add(connected_id)
            connected_ids.append(connected_id)

        items = self._load_items(connected_ids)

        result = []

        for connected_id in connected_ids:
            item = items.get(connected_id)

            if item is None:
                continue

            item_result = item_to_dict(item)
            item_result["relations"] = [
                relation
                for relation in relations
                if relation[
                    "connected_item_id"
                ] == connected_id
            ]

            result.append(item_result)

        return result

    def traverse(
        self,
        item_id: int,
        *,
        max_depth: int = 3,
        relation_types: (
            list[str] | set[str] | None
        ) = None,
    ) -> dict[str, Any]:
        start_item = self._require_item(item_id)

        normalized_relation_types = {
            self._normalize(value)
            for value in (
                relation_types or []
            )
            if self._normalize(value)
        }

        safe_depth = max(
            0,
            min(int(max_depth), 20),
        )

        visited: set[int] = {item_id}
        queue: deque[tuple[int, int]] = deque(
            [(item_id, 0)]
        )

        nodes: dict[int, dict[str, Any]] = {
            item_id: item_to_dict(start_item)
        }

        edges: list[dict[str, Any]] = []
        edge_ids: set[int] = set()

        while queue:
            current_id, depth = queue.popleft()

            if depth >= safe_depth:
                continue

            relations = self._relations_for_item(
                current_id
            )

            for relation in relations:
                if (
                    normalized_relation_types
                    and relation.relation_type
                    not in normalized_relation_types
                ):
                    continue

                if relation.id not in edge_ids:
                    edge_ids.add(relation.id)
                    edges.append(
                        relation_to_dict(
                            relation
                        )
                    )

                connected_id = (
                    relation.target_id
                    if relation.source_id
                    == current_id
                    else relation.source_id
                )

                if connected_id not in nodes:
                    connected_item = self.db.get(
                        KnowledgeItem,
                        connected_id,
                    )

                    if connected_item is not None:
                        nodes[connected_id] = (
                            item_to_dict(
                                connected_item
                            )
                        )

                if connected_id in visited:
                    continue

                visited.add(connected_id)
                queue.append(
                    (
                        connected_id,
                        depth + 1,
                    )
                )

        return {
            "start_item": item_to_dict(
                start_item
            ),
            "max_depth": safe_depth,
            "relation_types": sorted(
                normalized_relation_types
            ),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def get_relation_path(
        self,
        source_id: int,
        target_id: int,
        *,
        max_depth: int = 6,
        relation_types: (
            list[str] | set[str] | None
        ) = None,
    ) -> dict[str, Any]:
        source_item = self._require_item(
            source_id
        )

        target_item = self._require_item(
            target_id
        )

        if source_id == target_id:
            return {
                "found": True,
                "source": item_to_dict(
                    source_item
                ),
                "target": item_to_dict(
                    target_item
                ),
                "depth": 0,
                "items": [
                    item_to_dict(
                        source_item
                    )
                ],
                "relations": [],
            }

        normalized_relation_types = {
            self._normalize(value)
            for value in (
                relation_types or []
            )
            if self._normalize(value)
        }

        safe_depth = max(
            1,
            min(int(max_depth), 20),
        )

        queue: deque[int] = deque(
            [source_id]
        )

        visited: set[int] = {source_id}

        depth_by_item: dict[int, int] = {
            source_id: 0
        }

        previous_item: dict[int, int] = {}
        previous_relation: dict[
            int,
            KnowledgeRelation,
        ] = {}

        found = False

        while queue:
            current_id = queue.popleft()
            current_depth = depth_by_item[
                current_id
            ]

            if current_depth >= safe_depth:
                continue

            relations = self._relations_for_item(
                current_id
            )

            for relation in relations:
                if (
                    normalized_relation_types
                    and relation.relation_type
                    not in normalized_relation_types
                ):
                    continue

                connected_id = (
                    relation.target_id
                    if relation.source_id
                    == current_id
                    else relation.source_id
                )

                if connected_id in visited:
                    continue

                visited.add(connected_id)
                depth_by_item[connected_id] = (
                    current_depth + 1
                )
                previous_item[connected_id] = (
                    current_id
                )
                previous_relation[
                    connected_id
                ] = relation

                if connected_id == target_id:
                    found = True
                    queue.clear()
                    break

                queue.append(connected_id)

        if not found:
            return {
                "found": False,
                "source": item_to_dict(
                    source_item
                ),
                "target": item_to_dict(
                    target_item
                ),
                "max_depth": safe_depth,
                "items": [],
                "relations": [],
            }

        item_ids = [target_id]
        relations = []

        current_id = target_id

        while current_id != source_id:
            relation = previous_relation[
                current_id
            ]
            relations.append(relation)

            current_id = previous_item[
                current_id
            ]
            item_ids.append(current_id)

        item_ids.reverse()
        relations.reverse()

        loaded_items = self._load_items(
            item_ids
        )

        return {
            "found": True,
            "source": item_to_dict(
                source_item
            ),
            "target": item_to_dict(
                target_item
            ),
            "depth": len(relations),
            "items": [
                item_to_dict(
                    loaded_items[current_id]
                )
                for current_id in item_ids
                if current_id in loaded_items
            ],
            "relations": [
                relation_to_dict(
                    relation
                )
                for relation in relations
            ],
        }

    def get_ordered_items(
        self,
        item_id: int,
        *,
        order_type: str,
        relation_type: str | None = None,
    ) -> dict[str, Any]:
        start_item = self._require_item(item_id)

        normalized_order_type = self._normalize(
            order_type
        )

        normalized_relation_type = (
            self._normalize(
                relation_type
            )
        )

        statement = select(
            KnowledgeRelation
        ).where(
            or_(
                KnowledgeRelation.source_id
                == item_id,
                KnowledgeRelation.target_id
                == item_id,
            ),
            KnowledgeRelation.order_type
            == normalized_order_type,
        )

        if normalized_relation_type:
            statement = statement.where(
                KnowledgeRelation.relation_type
                == normalized_relation_type
            )

        statement = statement.order_by(
            KnowledgeRelation.position.asc(),
            KnowledgeRelation.id.asc(),
        )

        relations = list(
            self.db.scalars(statement).all()
        )

        entries: dict[int, dict[str, Any]] = {
            item_id: {
                "item_id": item_id,
                "position": 0,
                "relation_id": None,
            }
        }

        for relation in relations:
            connected_id = (
                relation.target_id
                if relation.source_id
                == item_id
                else relation.source_id
            )

            position = relation.position

            if position is None:
                position = len(entries)

            existing = entries.get(
                connected_id
            )

            if (
                existing is None
                or position
                < existing["position"]
            ):
                entries[connected_id] = {
                    "item_id": connected_id,
                    "position": position,
                    "relation_id": relation.id,
                }

        ordered_entries = sorted(
            entries.values(),
            key=lambda entry: (
                entry["position"],
                entry["item_id"],
            ),
        )

        item_ids = [
            entry["item_id"]
            for entry in ordered_entries
        ]

        items = self._load_items(
            item_ids
        )

        result_items = []

        for entry in ordered_entries:
            item = items.get(
                entry["item_id"]
            )

            if item is None:
                continue

            result_items.append(
                {
                    "position": (
                        entry["position"]
                    ),
                    "relation_id": (
                        entry["relation_id"]
                    ),
                    "item": item_to_dict(
                        item
                    ),
                }
            )

        return {
            "start_item": item_to_dict(
                start_item
            ),
            "order_type": normalized_order_type,
            "relation_type": (
                normalized_relation_type
            ),
            "count": len(result_items),
            "items": result_items,
        }

    def get_franchise_members(
        self,
        item_id: int,
        *,
        max_depth: int = 10,
    ) -> dict[str, Any]:
        return self.traverse(
            item_id=item_id,
            max_depth=max_depth,
            relation_types={
                "same_franchise",
                "same_collection",
                "shared_universe",
                "spin_off",
                "prequel",
                "sequel",
                "crossover",
                "parent_series",
                "child_series",
            },
        )

    def find_invalid_relations(
        self,
    ) -> dict[str, Any]:
        relations = list(
            self.db.scalars(
                select(
                    KnowledgeRelation
                ).order_by(
                    KnowledgeRelation.id.asc()
                )
            ).all()
        )

        invalid = []
        duplicates = []
        seen_keys: set[
            tuple[
                int,
                int,
                str,
                str | None,
            ]
        ] = set()

        for relation in relations:
            problems = []

            if (
                relation.source_id
                == relation.target_id
            ):
                problems.append(
                    "source_equals_target"
                )

            source_exists = (
                self.db.get(
                    KnowledgeItem,
                    relation.source_id,
                )
                is not None
            )

            target_exists = (
                self.db.get(
                    KnowledgeItem,
                    relation.target_id,
                )
                is not None
            )

            if not source_exists:
                problems.append(
                    "source_missing"
                )

            if not target_exists:
                problems.append(
                    "target_missing"
                )

            if not relation.relation_type:
                problems.append(
                    "relation_type_missing"
                )

            relation_key = (
                relation.source_id,
                relation.target_id,
                relation.relation_type,
                relation.order_type,
            )

            if relation_key in seen_keys:
                duplicates.append(
                    relation_to_dict(
                        relation
                    )
                )
            else:
                seen_keys.add(
                    relation_key
                )

            if problems:
                invalid.append(
                    {
                        "relation": (
                            relation_to_dict(
                                relation
                            )
                        ),
                        "problems": problems,
                    }
                )

        return {
            "checked_relations": len(
                relations
            ),
            "invalid_count": len(
                invalid
            ),
            "duplicate_count": len(
                duplicates
            ),
            "invalid": invalid,
            "duplicates": duplicates,
        }

    def describe_item(
        self,
        item_id: int,
    ) -> dict[str, Any]:
        item = self._require_item(item_id)

        direct_relations = (
            self.get_direct_relations(
                item_id
            )
        )

        relation_counts: dict[str, int] = {}

        for relation in direct_relations:
            relation_type = relation[
                "effective_relation_type"
            ]

            relation_counts[relation_type] = (
                relation_counts.get(
                    relation_type,
                    0,
                )
                + 1
            )

        return {
            "item": item_to_dict(item),
            "external_ids": decode_json(
                item.external_ids
            ),
            "metadata": decode_json(
                item.metadata_json
            ),
            "relation_count": len(
                direct_relations
            ),
            "relation_types": dict(
                sorted(
                    relation_counts.items()
                )
            ),
            "relations": direct_relations,
        }

    def _relations_for_item(
        self,
        item_id: int,
    ) -> list[KnowledgeRelation]:
        statement = (
            select(KnowledgeRelation)
            .where(
                or_(
                    KnowledgeRelation.source_id
                    == item_id,
                    KnowledgeRelation.target_id
                    == item_id,
                )
            )
            .order_by(
                KnowledgeRelation.id.asc()
            )
        )

        return list(
            self.db.scalars(
                statement
            ).all()
        )

    def _relation_with_direction(
        self,
        *,
        relation: KnowledgeRelation,
        item_id: int,
    ) -> dict[str, Any]:
        outgoing = (
            relation.source_id == item_id
        )

        connected_item_id = (
            relation.target_id
            if outgoing
            else relation.source_id
        )

        effective_relation_type = (
            relation.relation_type
        )

        if not outgoing:
            effective_relation_type = (
                self.INVERSE_RELATION_TYPES.get(
                    relation.relation_type,
                    relation.relation_type,
                )
            )

        connected_item = self.db.get(
            KnowledgeItem,
            connected_item_id,
        )

        result = relation_to_dict(
            relation
        )

        result.update(
            {
                "direction": (
                    "outgoing"
                    if outgoing
                    else "incoming"
                ),
                "connected_item_id": (
                    connected_item_id
                ),
                "effective_relation_type": (
                    effective_relation_type
                ),
                "connected_item": (
                    item_to_dict(
                        connected_item
                    )
                    if connected_item
                    is not None
                    else None
                ),
            }
        )

        return result

    def _require_item(
        self,
        item_id: int,
    ) -> KnowledgeItem:
        item = self.db.get(
            KnowledgeItem,
            item_id,
        )

        if item is None:
            raise ValueError(
                "Wissenseintrag wurde nicht "
                f"gefunden: {item_id}"
            )

        return item

    def _load_items(
        self,
        item_ids: list[int],
    ) -> dict[int, KnowledgeItem]:
        if not item_ids:
            return {}

        statement = select(
            KnowledgeItem
        ).where(
            KnowledgeItem.id.in_(
                item_ids
            )
        )

        items = list(
            self.db.scalars(
                statement
            ).all()
        )

        return {
            item.id: item
            for item in items
        }

    @staticmethod
    def _normalize(
        value: str | None,
    ) -> str:
        return normalize_relation_type(
            value
        )
