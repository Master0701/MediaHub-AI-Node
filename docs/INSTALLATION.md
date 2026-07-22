# Installation

## 1. Repository herunterladen

```bash
sudo -u mediahub git clone \
  https://github.com/Master0701/MediaHub-AI-Node.git \
  /opt/mediahub/ai-node
```

Solange das öffentliche Repository noch nicht angelegt ist, werden die vorbereiteten Dateien manuell nach `/opt/mediahub/ai-node` kopiert.

## 2. Virtuelle Umgebung

```bash
sudo -u mediahub python3 -m venv /opt/mediahub/venv
sudo -u mediahub /opt/mediahub/venv/bin/python -m pip install --upgrade pip
sudo -u mediahub /opt/mediahub/venv/bin/pip install \
  -r /opt/mediahub/ai-node/requirements.txt
```

## 3. Konfiguration

```bash
cd /opt/mediahub/ai-node
sudo -u mediahub cp .env.example .env
```

Tokens und Geheimnisse nur in `.env` oder einer geschützten systemd-Konfiguration speichern. `.env` wird nicht eingecheckt.

## 4. Manueller Start

```bash
cd /opt/mediahub/ai-node
source /opt/mediahub/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

## 5. Health-Check

```bash
curl -sS http://127.0.0.1:8765/health \
  | python -m json.tool
```

Erwartet wird `"status": "healthy"`.

## 6. Dienst installieren

Siehe [SYSTEMD_SERVICE.md](SYSTEMD_SERVICE.md).

## 7. Tests

```bash
cd /opt/mediahub/ai-node
source /opt/mediahub/venv/bin/activate
python -m pytest
python tests/test_ai_node_smoke.py
```

Der geprüfte Raspberry-Pi-Stand endete mit 5 von 5 bestandenen Smoke-Tests.
