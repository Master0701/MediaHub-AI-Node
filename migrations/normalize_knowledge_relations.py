from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.knowledge.constants import normalize_relation_type
from app.knowledge.models import KnowledgeRelation


def migrate_relation_types() -> None:
    db = SessionLocal()

    changed = 0
    unchanged = 0
    conflicts = 0

    try:
        relations = list(
            db.scalars(select(KnowledgeRelation).order_by(KnowledgeRelation.id.asc())).all()
        )

        for relation in relations:
            old_relation_type = relation.relation_type

            new_relation_type = normalize_relation_type(old_relation_type)

            old_order_type = relation.order_type

            new_order_type = normalize_relation_type(old_order_type) if old_order_type else None

            if old_relation_type == new_relation_type and old_order_type == new_order_type:
                unchanged += 1
                continue

            relation.relation_type = new_relation_type
            relation.order_type = new_order_type

            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                conflicts += 1

                print(
                    "Konflikt bei Beziehung",
                    relation.id,
                    "- nicht geändert.",
                )
                continue

            changed += 1

            print(f"Beziehung {relation.id}: {old_relation_type!r} -> {new_relation_type!r}")

        db.commit()

        print()
        print("Migration abgeschlossen.")
        print("Geändert:", changed)
        print("Unverändert:", unchanged)
        print("Konflikte:", conflicts)

    finally:
        db.close()


if __name__ == "__main__":
    migrate_relation_types()
