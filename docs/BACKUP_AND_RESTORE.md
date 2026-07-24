# Backup und Wiederherstellung

## Zu sichernde Daten

- Datenbankdateien
- Konfiguration und `.env`
- lokale Wissensdaten
- Cache, sofern nicht problemlos neu erzeugbar
- benutzerdefinierte Regeln
- Schlüssel und Tokens nur verschlüsselt oder geschützt sichern

## Beispiel-Backup

```bash
sudo systemctl stop mediahub-ai-node
tar -czf mediahub-ai-node-backup-$(date +%Y-%m-%d).tar.gz   /opt/mediahub/ai-node
sudo systemctl start mediahub-ai-node
```

## Wiederherstellung

1. Dienst stoppen.
2. Bestehenden Stand sichern.
3. Backup entpacken.
4. Eigentümer und Rechte kontrollieren.
5. Abhängigkeiten installieren.
6. Dienst starten und Health-Check durchführen.

```bash
sudo chown -R mediahub:mediahub /opt/mediahub/ai-node
sudo systemctl restart mediahub-ai-node
```
