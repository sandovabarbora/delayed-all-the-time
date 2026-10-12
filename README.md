# Delayed All the Time. On Time, Occasionally.

**A sonification of Prague public transport delays** — a companion piece to a master's thesis on
delay persistence in the PID network. Five real days from the dataset, played as disco tracks by
the transport system itself.

Open `index.html` in any browser, or visit the [hosted page](https://sandovabarbora.github.io/delayed-all-the-time/).
The player is one self-contained file: no server, no build step, no external resources (the three
fonts, Space Grotesk, JetBrains Mono and Fraunces, are embedded as WOFF2 subsets under the SIL Open
Font License), all audio synthesised live with the Web Audio API.

## Data and attribution

The underlying records are **Prague Integrated Transport (PID) stop-time history, provided by
[Golemio](https://golemio.cz)**, the open-data platform operated by Operator ICT for the City of
Prague. Please credit Golemio when reusing anything here.

- **Source period:** 15 March – 8 September 2025 (~121 million stop events)
- **What this repository contains:** five selected days aggregated into 5-minute windows per
  transport mode — event count, mean arrival delay, 90th-percentile arrival delay, with delays
  clipped to [−600, 3600] s
- **What it does not contain:** no raw stop-time records are redistributed. The aggregates in
  `sonification_days.json` are a derived work and are embedded verbatim in `index.html`.

## How the data drives the music

This section describes engine v1, the original disco version. Every data-to-music decision is
deterministic and comes from the data. The only randomness is in two textures: the noise behind the
hats and the reverb impulse are filled with `Math.random`, so two v1 plays differ very slightly in
those sounds and nowhere else.

| element | data source |
|---|---|
| tempo grid | 288 five-minute windows of one day = 288 beats at 116 BPM (24 h ≈ 2.5 min) |
| kick drum + bass | metro stop events (avg delay 7 s on a typical weekday — the most reliable pulse in the city; when the metro closes at night the beat literally stops, and the first morning train is the drop) |
| hi-hats + guitar plucks | tram stop events |
| chord stabs | bus stop events (557k/day on a weekday — the backbone); chord detune in cents grows with the current bus delay |
| claps + cowbell | trolleybus stop events |
| bell | ferry stop events (3 rings on a typical Tuesday; dozens in summer) |
| lead melody ("Voice of the City") | city-wide average surface delay, quantised to the day's scale — the later Prague runs, the higher it sings |
| trains | kicked out of the band: averaging 111 s late on a typical weekday, they played too far out of tune (still shown in the chart) |

**Song structure is data-driven.** The chorus is not triggered by the clock: whenever the smoothed,
event-weighted average delay of surface transport (bus + tram + trolleybus) exceeds **68 % of that
day's own maximum**, the city stops keeping up and the track lifts into the chorus. On a typical
weekday this yields exactly the two rush hours (≈ 07:25–10:00 and 14:45–17:40, delay peaking at
145 s around 07:55).

**Each day sings in its own key**, chosen by its mean surface delay — bright modes to dark:

| day | mean surface delay | key |
|---|---|---|
| Easter Monday, 21 Apr 2025 | 36 s | D lydian — floating, nothing hurts |
| Summer Sunday, 13 Jul 2025 | 43 s | D major — sunny with a chance of buses |
| Back to School, 1 Sep 2025 | 82 s | D dorian — the first school day sounds like any other workday |
| Typical Tuesday, 17 Jun 2025 | 85 s | D dorian — the everyday funk |
| The Meltdown, 30 Apr 2025 | 164 s | D phrygian — the city in distress |

Thresholds: < 40 s lydian, < 70 s ionian, < 100 s dorian, < 130 s aeolian, otherwise phrygian.

**Production notes.** The groove swings (~58 % shuffle), everything melodic is side-chained to the
metro's kick, the two beats before each chorus break down into a snare roll + riser before the drop,
the bassline walks chromatically into every chord change, and the arrangement varies in 8-beat
blocks so long off-peak stretches stay alive. The mix is stereo (plucks left, arpeggio right, pads
wide) with a −4.5 dB high-shelf at 6 kHz.

## Engine v2

The player has two engines, switched with the `engine v1 | v2` toggle. v2 is the default; v1 is
unchanged and stays selectable. v2 is a techno engine and is fully deterministic: its noise and
reverb come from a seeded generator, so a render of the same day is always identical.

v2 reads features the thesis extractor computes against a normal day, not only the raw delay:

- **Density.** The surface network's (bus, tram, trolleybus) delay as a robust z against the median
  day of the same type sets the arrangement: sparse below 0, full from 0, lifted from 1, extreme
  from 2 with a two-bar breakdown on entry.
- **Groove.** The share of stop events more than 90 s late: straight below 10 %, swung from 10 %,
  half-time above 25 %.
- **Harmony and timbre.** z climbs a functional ladder (tonic, subdominant, dominant, dominant
  with tensions, secondary dominants) with one chord per bar and voice-led pads; each rung opens
  the filters and adds drive.
- **Echo.** Lag-1 delay persistence between consecutive stops, by hour of day over the whole
  period, sets the feedback of a dotted-eighth echo. It is the same on every day.
- **Melody.** The smoothed surface delay, one scale step per 30 s, stepwise in the chord-scale.

States change once per bar, with hysteresis. All thresholds were fixed a priori in robust SD or
round percentages; none was tuned by listening. Every mapping and number is in
[docs/ENGINE_V2.md](docs/ENGINE_V2.md).

## Reproducing the aggregates

`extract_sonification_data.py` regenerates `sonification_days.json` from the project's local
DuckDB build of the Golemio stop-time history. It requires that database, which is not distributed
here; the script is included to document how the published aggregates were produced.

```bash
python extract_sonification_data.py
```

It selects the five days (criteria documented inline), aggregates stop events into 5-minute bins
per transport mode, and writes `sonification_days.json`, which `index.html` embeds verbatim.

The v2 features come from `extract_v2.py`, documented in [docs/FEATURES_V2.md](docs/FEATURES_V2.md).
Its inputs are the thesis DuckDB build of the stop-time history and the PID GTFS `stops.txt`;
neither is redistributed here. Paths are set with `SONIF_DB`, `SONIF_STOPS` and `SONIF_OUT`
(defaults: next to the script). `embed_v2_features.py` then writes the part the engine uses
(about 22 KB, aggregates only) into `index.html` as `const DATA2`, so the intermediate
`sonification_v2.json` is not committed.

```bash
SONIF_DB=/path/to/prague_transit.duckdb SONIF_STOPS=/path/to/stops.txt python extract_v2.py
python embed_v2_features.py sonification_v2.json
```

## Homage disclaimer

Title and structure are a loving homage to the disco-revival tradition, and the phrasing of the
title riffs on contemporary pop-album naming. No affiliation with, or endorsement by, any artist
or label. No audio was sampled — every sound is synthesised in the browser from public-transport
data. Any resemblance to an actual banger is purely statistical.
