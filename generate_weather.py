from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

LAT = 53.47693
LON = 9.70141
LOCATION = "Buxtehude"
FORECAST_DAYS = 10
OUTPUT = Path("public/weather.ics")

WEATHER = {
    0: ("☀️", "Klar"),
    1: ("🌤️", "Überwiegend klar"),
    2: ("⛅", "Teilweise bewölkt"),
    3: ("☁️", "Bewölkt"),
    45: ("🌫️", "Nebel"),
    48: ("🌫️", "Reifnebel"),
    51: ("🌦️", "Leichter Nieselregen"),
    53: ("🌦️", "Nieselregen"),
    55: ("🌧️", "Starker Nieselregen"),
    56: ("🌧️", "Gefrierender Nieselregen"),
    57: ("🌧️", "Starker gefrierender Nieselregen"),
    61: ("🌦️", "Leichter Regen"),
    63: ("🌧️", "Regen"),
    65: ("🌧️", "Starker Regen"),
    66: ("🌧️", "Gefrierender Regen"),
    67: ("🌧️", "Starker gefrierender Regen"),
    71: ("🌨️", "Leichter Schneefall"),
    73: ("🌨️", "Schneefall"),
    75: ("❄️", "Starker Schneefall"),
    77: ("❄️", "Schneegriesel"),
    80: ("🌦️", "Leichte Regenschauer"),
    81: ("🌧️", "Regenschauer"),
    82: ("⛈️", "Starke Regenschauer"),
    85: ("🌨️", "Leichte Schneeschauer"),
    86: ("❄️", "Starke Schneeschauer"),
    95: ("⛈️", "Gewitter"),
    96: ("⛈️", "Gewitter mit leichtem Hagel"),
    99: ("⛈️", "Gewitter mit starkem Hagel"),
}

def ics_escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )

params = {
    "latitude": LAT,
    "longitude": LON,
    "daily": ",".join([
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
        "precipitation_sum",
        "wind_speed_10m_max",
    ]),
    "timezone": "Europe/Berlin",
    "forecast_days": FORECAST_DAYS,
}

url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)

with urlopen(url, timeout=30) as response:
    data = json.load(response)

daily = data["daily"]
now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Buxtehude Wetterkalender//DE",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Wetter Buxtehude",
    "X-PUBLISHED-TTL:PT3H",
]

for i, day in enumerate(daily["time"]):
    date = datetime.strptime(day, "%Y-%m-%d").date()
    next_date = date + timedelta(days=1)

    code = daily["weather_code"][i]
    icon, description = WEATHER.get(code, ("🌡️", "Wetter"))

    tmax = round(daily["temperature_2m_max"][i])
    tmin = round(daily["temperature_2m_min"][i])
    rain_prob = daily["precipitation_probability_max"][i]
    rain_mm = daily["precipitation_sum"][i]
    wind = round(daily["wind_speed_10m_max"][i])

    summary = f"{icon} {tmax}° / {tmin}° · 💧 {rain_prob}%"

    details = (
        f"{description}\n"
        f"Höchsttemperatur: {tmax} °C\n"
        f"Tiefsttemperatur: {tmin} °C\n"
        f"Regenwahrscheinlichkeit: {rain_prob} %\n"
        f"Niederschlag: {rain_mm} mm\n"
        f"Max. Wind: {wind} km/h\n"
        f"Ort: {LOCATION}\n"
        f"Daten: Open-Meteo"
    )

    uid = f"weather-buxtehude-{day}@weather-calendar"

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"LAST-MODIFIED:{now}",
        f"DTSTART;VALUE=DATE:{date.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{next_date.strftime('%Y%m%d')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(details)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")

# Kleine Startseite für GitHub Pages
Path("public/index.html").write_text("""<!doctype html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wetterkalender Buxtehude</title></head>
<body>
<h1>Wetterkalender Buxtehude</h1>
<p><a href="weather.ics">weather.ics öffnen</a></p>
<p>Datenquelle: Open-Meteo</p>
</body></html>""", encoding="utf-8")

print(f"{OUTPUT} mit {len(daily['time'])} Tagen erstellt.")
