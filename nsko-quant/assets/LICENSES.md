
## Voice-over (video ad)
- Piper TTS (MIT) with voice `en_GB-northern_english_male-medium`: dataset OpenSLR 83 (CC BY-SA 4.0), base model rdh (CC0). Credit: "Voice: Piper, OpenSLR 83 (CC BY-SA 4.0)". The en_GB "alan" voice was NOT used, because it is fine-tuned from lessac, whose dataset licence is unclear for commercial use.

## Music and sound (video ad)
- All music and sound effects in `marketing/video/out/*.mp4` were synthesised in code by NSKO Solutions (`marketing/video/audio.py`, numpy/scipy): a 64 BPM low pulse, sub drone, low-passed saw pad, tick-tock clock, typing clicks, noise risers and a sine bell. No samples, loops or downloaded music were used, so no third-party licence applies. numpy and scipy are BSD-3.

## Marketing assets (video ad and posters)
- Fonts: Inter (SIL OFL 1.1) and JetBrains Mono (SIL OFL 1.1), from `@fontsource`.
- Every screen is the NSKO QUANT app in demo mode, recorded locally.
- The God's Eye shot shows Esri World Imagery (credit "Esri, Maxar, Earthstar Geographics, and the GIS User Community", visible in the app's credit line). Esri's terms for using basemap imagery in advertising were not checked from the sandbox: re-check before paid media, or swap that shot for the brain sphere. The posters do not use it.
- The Live Desk chart is TradingView Lightweight Charts (Apache-2.0); its attribution logo stays visible in the shot.

## Stage 3 data sources (engine: nsq/data, nsq/research, nsq/lab, nsq/godseye)
Endpoints are from each provider's own public documentation. The docs sites could not be opened from the build sandbox, so terms marked "re-check" should be read again before NSKO QUANT is sold.

### Market data and news
- **Kraken public REST (OHLC, Trades) and WebSocket v2 `trade`**: free, no key. Kraken's terms allow use of public market data; redistribution of raw data is not allowed, so it stays on the user's machine. Fair use: about 1 request per second.
- **GDELT DOC 2.0 API**: free and open, including commercial use, with a citation ("Source: The GDELT Project"). The limit is 1 request per 5 seconds. Only headlines and links are kept.
- **RSS feeds** (default: Federal Reserve press releases, US public domain): only headlines and links are stored, and robots.txt is checked first. Each publisher keeps its copyright.
- **SEC EDGAR** (sec.gov, data.sec.gov): US public domain. SEC fair-access rules apply: at most 10 requests per second, and a User-Agent that names you (setting `sec.user_agent`).
- **US House Clerk periodic transaction reports**: public records, used for context only and weeks late. The Ethics in Government Act (5 U.S.C. §13107) bars commercial use of these reports, so this source is **off by default** (`news.congress_enabled`). Get legal advice before turning it on in a product that is sold.
- **US Senate eFD**: the site requires you to accept its terms first, so the engine only gives you a link to it and scrapes nothing.
- **13F filings** (SEC EDGAR): US public domain, context only.
- **Economic calendar**: `nsq/data/econ_calendar.json` was written by NSKO. It holds FOMC 2026 dates from federalreserve.gov and recurring rules for NFP, jobless claims and the EIA report. Check it against the official calendars.

### Research
- **GitHub REST API (search, readme)**: allowed under the GitHub Terms of Service. Each repository keeps its own licence, which is recorded per source. Only a short excerpt and the link are stored.
- **arXiv API**: metadata, including abstracts, is CC0. Each paper keeps its own licence. The limit is 1 request per 3 seconds.
- **YouTube Data API v3**: bring your own key, under the YouTube API Services Terms. Only the title, description and link are used. Transcripts are off by default; the optional `youtube-transcript-api` (MIT) reads YouTube's caption endpoint, which the YouTube Terms may not allow.
- **Ollama** (MIT) runs a local model on the user's machine. Each model has its own licence (for example the Llama 3.1 Community Licence), and the user chooses the model.
- **Offline research notes** in `nsq/research/scout.py` were written by NSKO Solutions.

### God's Eye
- **adsb.lol API v2**: data is ODbL 1.0. Attribution: "Flight data: adsb.lol contributors, ODbL 1.0". No key is needed today; adsb.lol says it may add keys later. If a product shares derived databases, the ODbL share-alike clause applies (re-check).
- **AISStream.io**: bring your own free key, and the layer is off by default. Its terms could not be read from the sandbox, so commercial use is not confirmed. Re-check, and treat it as personal use only until then.
- **CelesTrak GP data**: free. Credit CelesTrak. Fetch at most once every 2 hours per group, as CelesTrak asks.
- **USGS earthquake GeoJSON feeds**: US public domain. Credit the U.S. Geological Survey.
- **NASA FIRMS area API**: bring your own free MAP_KEY, and the layer is off by default. NASA data is free and open; credit "NASA FIRMS (LANCE/EOSDIS)".
- **Open-Meteo forecast API** (models include NOAA GFS): data is CC BY 4.0, with the credit "Weather data by Open-Meteo.com". **The free API is for non-commercial use only.** A paid product needs an Open-Meteo API plan; set `open_meteo_api_key` and the engine switches to customer-api.open-meteo.com. The NOAA GFS model data itself is US public domain.
- **Launch Library 2** (The Space Devs): the free tier allows 15 requests per hour. Credit "Launch Library 2 by The Space Devs".
- **Microsoft Planetary Computer STAC API** (Sentinel-2 L2A): STAC search is free and needs no key, under the Planetary Computer terms of use (re-check for commercial use). Sentinel-2 data is Copernicus free and open; credit "Contains modified Copernicus Sentinel data [year]".
- **EIA API v2** (weekly crude stocks WCESTUS1): bring your own free key. US public domain; credit "Source: U.S. Energy Information Administration".
- **Not used, by rule**: OpenSky, Cesium ion, Google 3D Tiles, CCTV feeds, TeleGeography cables.

### Python libraries added for Stage 3
- `websockets` (BSD-3, via uvicorn[standard]), `defusedxml` (PSF), `sgp4` (MIT, optional), `youtube-transcript-api` (MIT, optional), pandas and numpy (BSD-3).
