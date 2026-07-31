"""Build the city plates and the README.

    python3 tools/build.py history   # refetch 1940-now and rebuild data/monthly.json
    python3 tools/build.py           # daily: update the recent tail and re-render

The history mode moves about 12MB and takes a couple of minutes, so it is not what
runs every morning. It reduces 86 years of daily maximum temperature for every city
to one monthly mean each, which is 21 cities x 87 years x 12 months of numbers, and
commits that as data/monthly.json.

The daily mode fetches only the last ninety days. Nothing before that can change:
ERA5 is a reanalysis, so the past is settled, and the only cell that moves is the
month currently in progress. Ninety days is enough to close out the previous month
once the reanalysis catches up, which it does on a lag of about five days.
"""
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

import cities
import render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PLATES = os.path.join(ROOT, "plates")
TABLE = os.path.join(DATA, "monthly.json")

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FIRST_YEAR = 1940                    # ERA5 starts on 1940-01-01
BASE_FROM, BASE_TO = 1961, 1990      # WMO historical reference period
BATCH = 2                            # cities per request in history mode
TAIL = 90                            # days refetched by the daily run
LAG = 6                              # ERA5 publishes about five days behind

# Open-Meteo weights a request by locations multiplied by days, so an 86-year call
# for two cities is heavy enough to trip the per-minute limit on its own. The daily
# run is nowhere near it, at ninety days rather than thirty-one thousand.
RETRIES = 8
PAUSE = 45


def fetch(url):
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=300) as fh:
                return json.load(fh)
        except urllib.error.HTTPError as err:
            if err.code != 429 or attempt == RETRIES - 1:
                raise
            wait = 90 * (attempt + 1)
            print(f"    rate limited, waiting {wait}s")
            time.sleep(wait)


def series(start, stop, group):
    """Daily maxima per city for a date range, as {city: {date: value}}."""
    lats = ",".join(str(c[1]) for c in group)
    lons = ",".join(str(c[2]) for c in group)
    payload = fetch(f"{ARCHIVE}?latitude={lats}&longitude={lons}"
                    f"&start_date={start}&end_date={stop}"
                    "&daily=temperature_2m_max&timezone=auto")
    # A single-city request returns an object, several return an array. Normalising
    # here means the rest of the file never has to know which case it is in.
    if isinstance(payload, dict):
        payload = [payload]
    out = {}
    for city, block in zip(group, payload):
        daily = block["daily"]
        out[city[0]] = {
            date.fromisoformat(t): v
            for t, v in zip(daily["time"], daily["temperature_2m_max"])
            if v is not None
        }
    return out


def monthly(values):
    """Mean of each calendar month, keyed "YYYY-MM"."""
    buckets = {}
    for when, value in values.items():
        buckets.setdefault(f"{when:%Y-%m}", []).append(value)
    # A month is only counted once it is complete enough to mean anything. Twenty
    # days is generous, but it stops a month in progress being drawn as if it were
    # finished, which would make the newest cell the least trustworthy one.
    return {k: round(statistics.mean(v), 3) for k, v in buckets.items() if len(v) >= 20}


def rebuild_history():
    os.makedirs(DATA, exist_ok=True)
    stop = date.today() - timedelta(days=LAG)
    # Resume rather than restart. This moves about 12MB against a rate limit, so a
    # failure two thirds of the way through should not cost the first two thirds.
    payload = load() if os.path.exists(TABLE) else {
        "note": "Monthly mean of daily maximum temperature, degrees Celsius.",
        "source": "Open-Meteo ERA5 reanalysis",
        "baseline": f"{BASE_FROM}-{BASE_TO}",
        "cities": {},
    }
    for i in range(0, len(cities.CITIES), BATCH):
        group = [c for c in cities.CITIES[i:i + BATCH]
                 if c[0] not in payload["cities"]]
        if not group:
            continue
        for name, values in series(f"{FIRST_YEAR}-01-01", stop, group).items():
            payload["cities"][name] = monthly(values)
        json.dump(payload, open(TABLE, "w"), separators=(",", ":"))
        print(f"  {', '.join(c[0] for c in group)} "
              f"({len(payload['cities'])}/{len(cities.CITIES)})")
        time.sleep(PAUSE)
    print(f"wrote {TABLE} ({os.path.getsize(TABLE) / 1024:.0f}KB), "
          f"{len(payload['cities'])} cities")


def load():
    return json.load(open(TABLE))


def update_tail(payload):
    """Refresh the last ninety days in place, adding or correcting recent months."""
    stop = date.today() - timedelta(days=LAG)
    start = stop - timedelta(days=TAIL)
    changed = 0
    for i in range(0, len(cities.CITIES), BATCH):
        group = cities.CITIES[i:i + BATCH]
        for name, values in series(start, stop, group).items():
            for key, value in monthly(values).items():
                if payload["cities"][name].get(key) != value:
                    payload["cities"][name][key] = value
                    changed += 1
    return changed


def normals(months):
    """The 1961-1990 mean for each calendar month, or None where unavailable."""
    buckets = {m: [] for m in range(1, 13)}
    for key, value in months.items():
        year, month = int(key[:4]), int(key[5:])
        if BASE_FROM <= year <= BASE_TO:
            buckets[month].append(value)
    return {m: (statistics.mean(v) if v else None) for m, v in buckets.items()}


def decade_mean(months, first, last, base):
    """Mean anomaly across a span of years, or None if nothing falls in it."""
    got = [months[k] - base[int(k[5:])]
           for k in months
           if first <= int(k[:4]) <= last and base[int(k[5:])] is not None]
    return statistics.mean(got) if got else None


def main():
    payload = load()
    changed = update_tail(payload)
    json.dump(payload, open(TABLE, "w"), separators=(",", ":"))
    last_year = date.today().year

    rows = []
    for name, lat, lon, reason in cities.CITIES:
        months = payload["cities"][name]
        base = normals(months)
        anomalies = {(int(k[:4]), int(k[5:])): v - base[int(k[5:])]
                     for k, v in months.items() if base[int(k[5:])] is not None}
        # Both figures are against the same 1961-1990 baseline, so the reader can
        # do the subtraction themselves. An earlier attempt ranked cities by the
        # difference between the last decade and 1940-69, which quietly handed the
        # ranking to the least reliable thirty years in the record: ERA5's
        # back-extension before 1979 assimilates far fewer observations, and in
        # the Arctic the 1940s were genuinely warm, so Reykjavik came 18th.
        recent = decade_mean(months, last_year - 9, last_year, base)
        earliest = decade_mean(months, FIRST_YEAR, FIRST_YEAR + 9, base)

        head = (f"{abs(recent):.1f}°C {'warmer' if recent >= 0 else 'cooler'} "
                f"in the last decade than the {BASE_FROM}-{BASE_TO} average")
        note = (f"Monthly mean of the daily maximum, against this city's own "
                f"{BASE_FROM}-{BASE_TO} average")
        path = os.path.join(PLATES, f"{cities.slug(name)}.svg")
        render.render(name, anomalies, FIRST_YEAR, last_year, head, note, path)
        rows.append((recent, name, reason, earliest))

    rows.sort(reverse=True)
    write_readme(rows, changed)
    print(f"{changed} monthly values updated, {len(rows)} plates rendered")
    for recent, name, _, earliest in rows[:5]:
        print(f"  {name:<14} last decade {recent:+.2f}°C, 1940s {earliest:+.2f}°C")


def write_readme(rows, changed):
    stamp = date.today() - timedelta(days=LAG)
    lines = [
        "<!-- Generated by tools/build.py. Edits above the marker are kept. -->",
        "",
        "## The cities",
        "",
        "Ranked by the last ten years. Both figures are the same city measured "
        f"against its own {BASE_FROM}-{BASE_TO} average for the same months, never "
        "against another city, so the subtraction between the two columns is "
        "yours to make. The 1940s column is the least reliable number on this "
        "page: see the limitations above.",
        "",
        "| | City | Last decade | 1940s | Why it is here |",
        "|---:|---|---:|---:|---|",
    ]
    for i, (recent, name, reason, earliest) in enumerate(rows, 1):
        anchor = cities.slug(name)
        lines.append(f"| {i} | [{name}](#{anchor}) | **{recent:+.1f}°C** | "
                     f"{earliest:+.1f}°C | {reason} |")
    lines += ["", f"Last updated with data to {stamp:%-d %B %Y}. "
                  f"{changed} monthly values changed in this run.", ""]
    for recent, name, reason, earliest in rows:
        anchor = cities.slug(name)
        lines += [
            f"### {name}",
            "",
            f'<img src="plates/{anchor}.svg" alt="{name} monthly temperature '
            f'anomalies from {FIRST_YEAR} to {date.today().year}, one column per '
            f'year and one row per month" width="900">',
            "",
        ]
    body = "\n".join(lines)

    path = os.path.join(ROOT, "README.md")
    marker = "<!-- PLATES:START -->"
    text = open(path).read() if os.path.exists(path) else marker + "\n"
    open(path, "w").write(text.split(marker)[0] + marker + "\n" + body)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        rebuild_history()
    else:
        main()
