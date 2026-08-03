# Original-Lizenztexte

Dieser Ordner enthält die Standard-Lizenztexte für die direkten Python-Abhängigkeiten des MediaHub-AI-Node.

`dependency_licenses.json` ordnet jede direkte Abhängigkeit aus `requirements.txt` den passenden Lizenztexten zu. Vor jedem Release prüft `scripts/check_third_party_licenses.py`, ob alle Abhängigkeiten erfasst und alle referenzierten Dateien vorhanden sind.

Maßgeblich bleiben die Lizenz- und Copyright-Dateien der konkret installierten Paketversion. Debian-/apt-Pakete werden nicht im Repository gebündelt; deren Hinweise stammen aus der verwendeten Distribution.
