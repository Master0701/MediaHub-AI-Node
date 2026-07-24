# KI-Provider-System

## Zweck

Die Provider-Schicht erlaubt die parallele Einbindung mehrerer KI-Systeme.
MediaHub und die restliche API müssen dadurch nicht wissen, ob eine Aufgabe
lokal, auf dem Raspberry Pi oder durch einen optionalen Cloud-Dienst ausgeführt
wird.

## Bestandteile

- `AIProvider`: gemeinsame abstrakte Schnittstelle
- `ProviderRegistry`: Registrierung und Priorisierung
- `ProviderManager`: Routing, Timeout und Fallback
- `ProviderRequest`: einheitliches Auftragsformat
- `ProviderResponse`: einheitliches Antwortformat
- `ProviderHealth`: einheitlicher Health-Check
- `LocalProvider`: lokale Referenzimplementierung

## Auswahlregeln

1. Nur aktive Provider mit passender Fähigkeit werden berücksichtigt.
2. Provider werden nach ihrer Priorität sortiert.
3. Ein bevorzugter Provider wird zuerst versucht.
4. Bei Fehlern wird – sofern erlaubt – der nächste Provider genutzt.
5. Schlagen alle Provider fehl, erhält der Aufrufer einen klaren Fehler.

## Geplante Provider

- lokaler Regel- und Hilfsprovider
- Ollama
- llama.cpp
- Raspberry-Pi-REST-Provider
- OpenAI-/Cloud-Provider
- spezialisierte OCR-, Audio-, Bild- und Video-Provider

## Beispiel

```python
from app.providers import (
    LocalProvider,
    ProviderCapability,
    ProviderManager,
    ProviderRequest,
)

manager = ProviderManager()
manager.register(LocalProvider())

response = await manager.execute(
    ProviderRequest(
        capability=ProviderCapability.TEXT_GENERATION,
        payload={"prompt": "MediaHub"},
    )
)
```

Der enthaltene `LocalProvider` ist absichtlich nur eine Referenzimplementierung
und noch kein echtes Sprachmodell. Er macht die Provider-Schicht bereits
testbar, ohne neue externe Abhängigkeiten einzuführen.
