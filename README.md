# Delayed All the Time. On Time, Occasionally.

A sonification of Prague public transport delays: five real days played by the transport system
itself, with two engines (v1 disco, v2 techno). How it works, and why:
[bsandova.com/texts/delayed](https://bsandova.com/texts/delayed).

## Setup

Open `index.html` in a browser, or visit the [hosted page](https://sandovabarbora.github.io/delayed-all-the-time/).
It is one self-contained file with no server, no build step and no external resources. The fonts
(Space Grotesk, JetBrains Mono, Fraunces) are embedded as WOFF2 subsets under the SIL Open Font
License, and all audio is synthesised live with the Web Audio API.

Engine v2's mappings, thresholds and change log are in [docs/ENGINE_V2.md](docs/ENGINE_V2.md); its
input features in [docs/FEATURES_V2.md](docs/FEATURES_V2.md).

## Data provenance

The records are **Prague Integrated Transport (PID) stop-time history, provided by
[Golemio](https://golemio.cz)**, the open-data platform operated by Operátor ICT for the City of
Prague. Please credit Golemio when reusing anything here.

- **Source period:** 15 March – 8 September 2025 (about 121 million stop events).
- **In this repository:** five days aggregated into 5-minute windows per transport mode (event
  count, mean and 90th-percentile arrival delay, delays clipped to [−600, 3600] s), plus the v2
  features (about 22 KB). Both are embedded in `index.html`.
- **Not in this repository:** no raw stop-time records are redistributed.

## Reproducing the aggregates

Both extractors need the thesis's local DuckDB build of the stop-time history, which is not
distributed; they are included to document how the published aggregates were made.

```bash
python extract_sonification_data.py            # writes sonification_days.json (embedded verbatim)
SONIF_DB=/path/to/prague_transit.duckdb SONIF_STOPS=/path/to/stops.txt python extract_v2.py
python embed_v2_features.py sonification_v2.json   # writes const DATA2 into index.html
```

`extract_v2.py` also needs the PID GTFS `stops.txt`. Paths are set with `SONIF_DB`, `SONIF_STOPS`
and `SONIF_OUT` (defaults: next to the script).

## Licence

Code: MIT ([LICENSE](LICENSE)). Data credit as above.
