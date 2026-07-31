"""The cities, chosen to span climates rather than to rank importance.

The point of a fixed set is comparison, so the selection matters more than its
size. It covers both hemispheres, the Arctic and the equator, maritime and
continental, desert and monsoon. Southern-hemisphere cities are here deliberately:
their seasons run upside down against the month rows, which is a useful reminder
that the grid is showing a calendar and not a trend line.

Coordinates are city centres. ERA5 resolves to roughly 25km, so a few hundred
metres either way changes nothing; what it does mean is that these are the
climates of the grid cell a city sits in, not a reading from a station in it.
"""

CITIES = [
    # name,          latitude,  longitude,  a one-line reason for being here
    ("Reykjavik",     64.1466,  -21.9426, "sub-Arctic, and its 1940s were unusually warm"),
    ("Anchorage",     61.2181, -149.9003, "sub-Arctic on the other side of the world"),
    ("Moscow",        55.7558,   37.6173, "deep continental, the widest seasonal swing"),
    ("London",        51.5072,   -0.1276, "maritime temperate, and the one on the profile"),
    ("Paris",         48.8566,    2.3522, "temperate, a little more continental than London"),
    ("New York",      40.7128,  -74.0060, "humid continental, east-coast maritime"),
    ("Beijing",       39.9042,  116.4074, "continental monsoon, cold winters and hot summers"),
    ("Madrid",        40.4168,   -3.7038, "inland Mediterranean, hot and dry"),
    ("Tokyo",         35.6762,  139.6503, "humid subtropical, typhoon season"),
    ("Los Angeles",   34.0522, -118.2437, "Mediterranean, and drought-prone"),
    ("Cairo",         30.0444,   31.2357, "hot desert, almost no rain"),
    ("Delhi",         28.6139,   77.2090, "monsoon, and among the hottest big cities"),
    ("Mexico City",   19.4326,  -99.1332, "tropical highland, 2,200m up"),
    ("Lagos",          6.5244,    3.3792, "tropical monsoon, near the equator"),
    ("Singapore",      1.3521,  103.8198, "equatorial, barely a season to speak of"),
    ("Nairobi",       -1.2921,   36.8219, "tropical highland, just south of the equator"),
    ("Jakarta",       -6.2088,  106.8456, "equatorial monsoon, southern side"),
    ("Lima",         -12.0464,  -77.0428, "coastal desert, cooled by the Humboldt current"),
    ("Sao Paulo",    -23.5505,  -46.6333, "subtropical highland, southern hemisphere"),
    ("Cape Town",    -33.9249,   18.4241, "Mediterranean, seasons inverted"),
    ("Sydney",       -33.8688,  151.2093, "humid subtropical, seasons inverted"),
]

NAMES = [c[0] for c in CITIES]
LATS = ",".join(f"{c[1]}" for c in CITIES)
LONS = ",".join(f"{c[2]}" for c in CITIES)
REASONS = {c[0]: c[3] for c in CITIES}


def slug(name):
    return name.lower().replace(" ", "-")
