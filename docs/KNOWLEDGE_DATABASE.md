# Wissensdatenbank

## Zweck

Die Wissensdatenbank speichert nicht nur einzelne Medien, sondern auch Beziehungen zwischen ihnen.

Beispiele:

- Franchise
- Universum
- Fortsetzung
- Prequel
- Spin-off
- Crossover
- Veröffentlichungsreihenfolge
- chronologische Reihenfolge

## Kernmodelle

- `KnowledgeItem`
- `KnowledgeAlias`
- `KnowledgeRelation`

## Erkennung

Der aktuelle Stand unterstützt:

- normalisierte Titel
- Originaltitel
- Aliasnamen
- Jahr
- Medientyp
- externe IDs
- Kandidatenbewertung
- eindeutige Treffer
- Konflikterkennung

## Import

Der Importer unterstützt:

- `create`
- `update`
- `unchanged`
- `dry_run`
- Aliasimport
- externe IDs
- Metadaten-Merge
- Quellenverfolgung

## Beziehungen

Beziehungen werden normalisiert, beispielsweise:

```text
sequel-of -> sequel_of
release-order -> release_order
```

Vorhandene identische Beziehungen werden nicht doppelt angelegt.

## Graphprüfung

Die Integritätsprüfung kontrolliert mindestens:

- ungültige Beziehungen
- doppelte Beziehungen
- fehlende Quell- oder Zieleinträge

Der bestätigte Teststand meldete:

```text
Ungültig: 0
Dubletten: 0
```
