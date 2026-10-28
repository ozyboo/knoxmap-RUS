"""Buildings from Microsoft's Global ML Building Footprints, where OSM has none.

Overture's gap filling (generator/overture.py) draws on these same footprints
but reaches them through DuckDB and two to three minutes of sifting metadata.
Microsoft publishes them itself as plain files, one per quadkey tile, so this
needs nothing installed: read the index, download only the tiles that cover the
box, keep the footprints that touch it. Same ODbL licence as OSM.

Everything after the fetch is shared with the Overture path: the rows become
OSMFeatures through overture.to_features and are dropped where a mapped
building already stands through overture.only_missing.

A tile is about 30 MB gzipped (all of eastern Tennessee's Knox County sits in
one), so the answer is cached beside the map like the Overpass one.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import os
import tempfile
import time
import urllib.request

from . import overture
from .osm import OSMFeature

INDEX_URL = ("https://minedbuildings.z5.web.core.windows.net"
             "/global-buildings/dataset-links.csv")
ZOOM = 9                      # the index's tiles are level-9 quadkeys
INDEX_MAX_AGE_S = 7 * 86400   # Microsoft re-publishes every few months
TIMEOUT_S = 120
USER_AGENT = "KnoxMap (Project Zomboid map generator)"


def cache_path(output_dir: str, map_name: str) -> str:
    return os.path.join(output_dir, f"{map_name}_microsoft.json.gz")


def save_cache(path: str, bbox, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump({"source": "microsoft", "bbox": list(bbox),
                   "buildings": rows}, fh)


def load_cache(path: str, bbox) -> list[dict] | None:
    if not os.path.exists(path):
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError):
        return None
    kept = payload.get("bbox")
    if not (isinstance(kept, list) and len(kept) == 4
            and all(abs(a - b) < 1e-9 for a, b in zip(kept, bbox))):
        return None
    found = payload.get("buildings")
    return found if isinstance(found, list) else None


def quadkeys(south: float, west: float, north: float, east: float,
             zoom: int = ZOOM) -> list[str]:
    """Every level-`zoom` Bing quadkey the box touches."""
    def tile(lat: float, lon: float) -> tuple[int, int]:
        n = 2 ** zoom
        lat = max(-85.05112878, min(85.05112878, lat))
        s = math.sin(math.radians(lat))
        x = (lon + 180.0) / 360.0 * n
        y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
        return min(n - 1, max(0, int(x))), min(n - 1, max(0, int(y)))

    x0, y0 = tile(north, west)
    x1, y1 = tile(south, east)
    keys = []
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            key = ""
            for i in range(zoom, 0, -1):
                m = 1 << (i - 1)
                key += str((1 if x & m else 0) + (2 if y & m else 0))
            keys.append(key)
    return keys


def _open(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=TIMEOUT_S)


def _index() -> dict[str, list[str]]:
    """quadkey -> tile urls, from the index, kept in the temp folder a week."""
    path = os.path.join(tempfile.gettempdir(), "knoxmap_ms_buildings_index.csv")
    fresh = (os.path.exists(path)
             and time.time() - os.path.getmtime(path) < INDEX_MAX_AGE_S)
    if not fresh:
        with _open(INDEX_URL) as resp, open(path + ".part", "wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
        os.replace(path + ".part", path)
    table: dict[str, list[str]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table.setdefault(row["QuadKey"], []).append(row["Url"])
    return table


def _touches(shape: dict, south, west, north, east) -> bool:
    kind = shape.get("type")
    parts = ([shape.get("coordinates") or []] if kind == "Polygon"
             else shape.get("coordinates") or [] if kind == "MultiPolygon"
             else [])
    for part in parts:
        for lon, lat in (part[0] if part else []):
            # a corner inside is enough; a footprint spanning the whole box
            # without a corner in it is not a thing a town has
            if west <= lon <= east and south <= lat <= north:
                return True
    return False


def fetch(south: float, west: float, north: float, east: float,
          should_stop=None) -> list[dict]:
    """Every Microsoft footprint with a corner inside this box."""
    table = _index()
    urls = [u for k in quadkeys(south, west, north, east)
            for u in table.get(k, [])]
    rows: list[dict] = []
    for url in urls:
        with _open(url) as resp, gzip.GzipFile(fileobj=resp) as gz:
            for n, line in enumerate(io.TextIOWrapper(gz, encoding="utf-8")):
                if n % 20000 == 0 and should_stop is not None and should_stop():
                    import knoxstop
                    raise knoxstop.Stopped("the Microsoft buildings download")
                try:
                    feat = json.loads(line)
                    shape = feat["geometry"]
                except (ValueError, KeyError, TypeError):
                    continue
                if not _touches(shape, south, west, north, east):
                    continue
                height = (feat.get("properties") or {}).get("height")
                rows.append({"id": None, "height": height, "levels": None,
                             "class": None, "geometry": shape})
    return rows


def add_missing(features: list[OSMFeature],
                bbox: tuple[float, float, float, float],
                output_dir: str, map_name: str,
                should_stop=None) -> tuple[list[OSMFeature], dict]:
    """`features`, plus a building wherever Microsoft has one and OSM does not.

    Raises on a network failure; the caller decides what to fall back to.
    """
    south, west, north, east = bbox
    stats = {"available": True, "fetched": 0, "added": 0, "cached": False}
    path = cache_path(output_dir, map_name)
    rows = load_cache(path, bbox)
    if rows is not None:
        stats["cached"] = True
    else:
        rows = fetch(south, west, north, east, should_stop=should_stop)
        try:
            save_cache(path, bbox, rows)
        except OSError:
            pass
    stats["fetched"] = len(rows)
    extra = overture.only_missing(overture.to_features(rows), features)
    stats["added"] = len(extra)
    return (features + extra) if extra else features, stats
