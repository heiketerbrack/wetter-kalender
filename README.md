# Wetterkalender Buxtehude

Erzeugt automatisch einen iCalendar-Wetterfeed für Buxtehude mit Open-Meteo
und veröffentlicht ihn über GitHub Pages.

## Einrichtung

1. Neues öffentliches GitHub-Repository erstellen, z. B. `wetter-buxtehude`.
2. Den Inhalt dieses Pakets ins Repository hochladen.
3. GitHub: Settings → Pages → Source → GitHub Actions.
4. Unter Actions den Workflow `Wetterkalender aktualisieren` einmal manuell starten.
5. Danach ist der Feed typischerweise erreichbar unter:
   `https://DEIN-BENUTZERNAME.github.io/wetter-buxtehude/weather.ics`

Der Workflow erzeugt den Feed automatisch alle drei Stunden neu.
