"""Probe every Stage 3 host once and print reachable / blocked: `python -m nsq.data.probe`.
One light request per host (a documented endpoint), so it is safe to run any time."""
from __future__ import annotations

import json
import urllib.error

from .util import Blocked, http_get

PROBES = {
    "api.kraken.com": "https://api.kraken.com/0/public/Time",
    "api.gdeltproject.org": "https://api.gdeltproject.org/api/v2/doc/doc?query=gold&mode=ArtList&format=json&maxrecords=1",
    "www.sec.gov": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=1&output=atom",
    "disclosures-clerk.house.gov": "https://disclosures-clerk.house.gov/",
    "api.github.com": "https://api.github.com/rate_limit",
    "export.arxiv.org": "https://export.arxiv.org/api/query?search_query=all:momentum&max_results=1",
    "rss.arxiv.org": "https://rss.arxiv.org/rss/q-fin.TR",
    "www.federalreserve.gov": "https://www.federalreserve.gov/feeds/press_all.xml",
    "www.googleapis.com": "https://www.googleapis.com/youtube/v3/search",
    "api.adsb.lol": "https://api.adsb.lol/v2/mil",
    "stream.aisstream.io": "https://stream.aisstream.io/",
    "celestrak.org": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
    "earthquake.usgs.gov": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson",
    "firms.modaps.eosdis.nasa.gov": "https://firms.modaps.eosdis.nasa.gov/api/",
    "api.open-meteo.com": "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&daily=temperature_2m_min&forecast_days=1",
    "ll.thespacedevs.com": "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=1",
    "planetarycomputer.microsoft.com": "https://planetarycomputer.microsoft.com/api/stac/v1/",
    "api.eia.gov": "https://api.eia.gov/v2/",
}


def probe() -> dict:
    out = {}
    for host, url in PROBES.items():
        try:
            http_get(url, timeout=15, min_interval=0)
            out[host] = "reachable"
        except urllib.error.HTTPError as e:
            out[host] = f"reachable (HTTP {e.code})"
        except Blocked as e:
            out[host] = f"blocked ({str(e)[:80]})"
        except Exception as e:
            out[host] = f"error ({type(e).__name__})"
    return out


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))
