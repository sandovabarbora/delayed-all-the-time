# Delayed All the Time. On Time, Occasionally.

**A sonification of Prague public transport delays** — a companion piece to a master's thesis on
delay persistence in the PID network. Five real days from the dataset, played as disco tracks by
the transport system itself.

Open `index.html` in any browser, or visit the hosted page. The player is fully self-contained:
no server, no build step, no external resources, all audio synthesised live with the Web Audio API.

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

Every musical decision comes from the data — nothing is random:

| element | data source |
|---|---|
| tempo grid | 288 five-minute windows of one day = 288 beats at 116 BPM (24 h ≈ 2.5 min) |
| kick drum + bass | metro stop events (avg delay 9 s — the most reliable pulse in the city; when the metro closes at night the beat literally stops, and the first morning train is the drop) |
| hi-hats + guitar plucks | tram stop events |
| chord stabs | bus stop events (557k/day on a weekday — the backbone); chord detune in cents grows with the current bus delay |
| claps + cowbell | trolleybus stop events |
| bell | ferry stop events (3 rings on a typical Tuesday; dozens in summer) |
| lead melody ("Voice of the City") | city-wide average surface delay, quantised to the day's scale — the later Prague runs, the higher it sings |
| trains | kicked out of the band: averaging 123 s late, they played too far out of tune (still shown in the chart) |

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

## Reproducing the aggregates

`extract_sonification_data.py` regenerates `sonification_days.json` from the project's local
DuckDB build of the Golemio stop-time history. It requires that database, which is not distributed
here; the script is included to document how the published aggregates were produced.

```bash
python extract_sonification_data.py
```

It selects the five days (criteria documented inline), aggregates stop events into 5-minute bins
per transport mode, and writes `sonification_days.json`, which `index.html` embeds verbatim.

## Homage disclaimer

Title and structure are a loving homage to the disco-revival tradition, and the phrasing of the
title riffs on contemporary pop-album naming. No affiliation with, or endorsement by, any artist
or label. No audio was sampled — every sound is synthesised in the browser from public-transport
data. Any resemblance to an actual banger is purely statistical.
