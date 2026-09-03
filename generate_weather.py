from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

# ===== KONFIGURATION =====
LAT = 53.47693
LON = 9.70141
LOCATION = "Buxtehude"
FORECAST_DAYS = 10
OUTPUT = Path("public/weather.ics")

# Ab dieser Regenwahrscheinlichkeit wird ein Zeitraum als "Regen möglich" markiert.
RAIN_THRESHOLD = 30

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

def rain_windows(date, time_index, hourly):
    """
    Prüft 08:00 bis 14:00 Uhr.
    Stunden mit >= RAIN_THRESHOLD % Regenwahrscheinlichkeit
    oder messbarem Niederschlag werden zu Zeitfenstern zusammengefasst.
    """
    wet_hours = []

    for hour in range(8, 15):
        ts = f"{date.isoformat()}T{hour:02d}:00"
        if ts not in time_index:
            continue

        i = time_index[ts]
        prob = hourly["precipitation_probability"][i]
        mm = hourly["precipitation"][i]

        if prob is None:
            prob = 0
        if mm is None:
            mm = 0

        if prob >= RAIN_THRESHOLD or mm > 0:
            wet_hours.append(hour)

    if not wet_hours:
        return [], 0

    # Zusammenhängende Stunden zu Zeitfenstern bündeln.
    groups = []
    start = prev = wet_hours[0]

    for hour in wet_hours[1:]:
        if hour == prev + 1:
            prev = hour
        else:
            groups.append((start, prev))
            start = prev = hour
        prev = hour

    groups.append((start, prev))

    # Maximale Regenwahrscheinlichkeit im gesamten Zeitraum 08–14 Uhr.
    probs = []
    for hour in range(8, 15):
        ts = f"{date.isoformat()}T{hour:02d}:00"
        if ts in time_index:
            p = hourly["precipitation_probability"][time_index[ts]]
            probs.append(p or 0)

    return groups, max(probs) if probs else 0

def format_windows(groups):
    if not groups:
        return "kein Regen erwartet"

    parts = []
    for start, end in groups:
        # Eine einzelne Stunde: "ca. 11 Uhr"
        if start == end:
            parts.append(f"ca. {start:02d} Uhr")
        else:
            # Stündliche Prognose: bei 10,11,12 wird "ca. 10–13 Uhr" angezeigt.
            parts.append(f"ca. {start:02d}–{end + 1:02d} Uhr")

    return " / ".join(parts)

params = {
    "latitude": LAT,
    "longitude": LON,
    "current": ",".join(["temperature_2m", "apparent_temperature", "weather_code"]),
    "hourly": ",".join([
        "temperature_2m",
        "weather_code",
        "precipitation_probability",
        "precipitation",
        "wind_speed_10m",
    ]),
    "timezone": "Europe/Berlin",
    "forecast_days": FORECAST_DAYS,
}

url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)

with urlopen(url, timeout=30) as response:
    data = json.load(response)

hourly = data["hourly"]
current = data.get("current", {})
current_temp = current.get("temperature_2m")
current_feels = current.get("apparent_temperature")
current_code = current.get("weather_code")
current_icon, current_desc = WEATHER.get(current_code, ("🌡️", "Wetter"))

time_index = {
    timestamp: i
    for i, timestamp in enumerate(hourly["time"])
}

now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
start_date = datetime.fromisoformat(hourly["time"][0]).date()

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Buxtehude Wetterkalender//DE",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Wetter Buxtehude",
    "X-WR-TIMEZONE:Europe/Berlin",
    "X-PUBLISHED-TTL:PT3H",
]

for day_offset in range(FORECAST_DAYS):
    date = start_date + timedelta(days=day_offset)

    ts_08 = f"{date.isoformat()}T08:00"
    ts_14 = f"{date.isoformat()}T14:00"

    if ts_08 not in time_index or ts_14 not in time_index:
        continue

    i08 = time_index[ts_08]
    i14 = time_index[ts_14]

    temp08 = round(hourly["temperature_2m"][i08])
    temp14 = round(hourly["temperature_2m"][i14])

    code08 = hourly["weather_code"][i08]
    icon08, desc08 = WEATHER.get(code08, ("🌡️", "Wetter"))

    code14 = hourly["weather_code"][i14]
    icon14, desc14 = WEATHER.get(code14, ("🌡️", "Wetter"))

    groups, max_prob = rain_windows(date, time_index, hourly)
    rain_text = format_windows(groups)

    # Kurzer Kalendertitel
    if groups:
        summary = (
            f"{icon08} 08h {temp08}° · {icon14} 14h {temp14}° "
            f"· 🌧️ {rain_text}"
        )
    else:
        summary = (
            f"{icon08} 08h {temp08}° · {icon14} 14h {temp14}° "
            f"· ☂️ trocken"
        )

    # Details für 08–14 Uhr
    hourly_details = []
    for hour in range(8, 15):
        ts = f"{date.isoformat()}T{hour:02d}:00"
        if ts not in time_index:
            continue

        i = time_index[ts]
        temp = round(hourly["temperature_2m"][i])
        prob = hourly["precipitation_probability"][i] or 0
        mm = hourly["precipitation"][i] or 0
        hourly_details.append(
            f"{hour:02d}:00 – {temp} °C · Regen {prob}% · {mm} mm"
        )

    current_line = ""
    if current_temp is not None:
        current_line = f"Aktuell: {current_icon} {round(current_temp)} °C · {current_desc}"
        if current_feels is not None:
            current_line += f" · gefühlt {round(current_feels)} °C"
        current_line += "\n\n"

    details = (
        f"Wetter in {LOCATION}\n\n"
        + current_line
        f"08:00 Uhr: {temp08} °C · {desc08}\n"
        f"14:00 Uhr: {temp14} °C · {desc14}\n\n"
        f"Regen zwischen 08:00 und 14:00 Uhr:\n"
        f"{rain_text}\n"
        f"Max. Regenwahrscheinlichkeit: {max_prob} %\n\n"
        + "\n".join(hourly_details)
        + "\n\nDaten: Open-Meteo"
    )

    # Termin jeden Tag um 08:00 Uhr, 30 Minuten lang.
    start_dt = datetime(date.year, date.month, date.day, 8, 0)
    end_dt = start_dt + timedelta(minutes=30)

    uid = f"weather-buxtehude-{date.isoformat()}@weather-calendar"

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"LAST-MODIFIED:{now}",
        f"DTSTART;TZID=Europe/Berlin:{start_dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/Berlin:{end_dt.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(details)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")

Path("public/index.html").write_text("""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wetterkalender Buxtehude</title>
</head>
<body>
<h1>Wetterkalender Buxtehude</h1>
<p>Täglich um 08:00 Uhr: Temperatur 08:00/14:00 Uhr und Regenfenster 08:00–14:00 Uhr.</p>
<p><a href="weather.ics">weather.ics öffnen</a></p>
<p>Datenquelle: Open-Meteo</p>
</body>
</html>""", encoding="utf-8")

print("weather.ics erstellt: Temperatur 08/14 Uhr + Regenfenster 08–14 Uhr.")
