# Engine v2

Engine v2 is the default; v1 stays available through the `engine v1 | v2` toggle and is unchanged (README).
v2 maps the data to arrangement, groove, harmony and timbre, so the five days sound clearly different.

**Rules.**
- **Deterministic.** The noise behind hats and reverb uses a seeded generator, and the pad LFO is a plain oscillator, so a render of the same day is always identical.
- **Grounded in music theory.**
- **Thresholds fixed a priori**, in robust SD or percent. None was tuned by listening to the five days.

All constants are in `const V2` and `const TIMBRE` in `index.html`.

## Data used

`embed_v2_features.py` takes `sonification_v2.json` from the thesis extractor and writes `const DATA2` into `index.html` (about 22 KB, aggregates only).

| feature | used for |
|---|---|
| surface (bus + tram + trolleybus) anomaly z per 5-min bin, against the median day of the same day type, in robust SD (MAD × 1.4826, floor 5 s) | density, harmony, timbre |
| lateness-class shares l90 (90–180 s] and l180 (> 180 s) for tram, bus and trolleybus, base64 at 2-point resolution | groove |
| lag-1 persistence r per local hour, pooled over all 173 days (tram, and the surface event-weighted mean) | echo feedback |

Dropped:
- Per-mode z, p50/p90, metro lateness classes and per-day persistence.
- **West/east delay.** Its split is skewed about 70/30 by regional stops, and a Prague-only recompute needs the source database.
- **The ferry** has no baseline; it just rings a bell on A5.

## Running values, evaluated per bar

- **Running z** is the 5-minute surface z smoothed over 3 windows (centred, undefined windows skipped).
- **Running lateness** = Σ n·(l90 + l180) / Σ n over bus, tram and trolleybus and the same 3 windows. `n` is the event count from the v1 data.
- **Every state is decided once per bar** from the values at the bar's downbeat window, with hysteresis.
- **Two scales:**
  - At the default scale (one 5-min window = one beat), one bar covers 20 minutes of data.
  - At the `1 bar` scale, one bar is one window.

## Mapping table

| musical dimension | data | states and thresholds | what changes |
|---|---|---|---|
| **density** | running z | sparse < 0 · full 0–1 · lifted 1–2 · extreme ≥ 2. Enter at 0 / 1 / 2, leave below −0.5 / 0.5 / 1.5 (0.5 SD hysteresis). May jump several states. | **sparse:** kick, bass and pad only, master trim −5 dB. **full:** + hats, clap, stabs, plucks, lead (−2 dB). **lifted:** + arp, shaker, second lead voice a diatonic third below, open hats, 16th ghost hats, cowbell when trolleybus traffic is dense (−1 dB). **extreme:** on entry a 2-bar breakdown (kick, bass and drums drop; pad, lead and a riser; snare roll in the last two beats), then everything, with cowbell always (0 dB). A crash marks every entry into lifted or extreme. |
| **groove** (primary rhythm) | running share > 90 s late | straight < 10 % · swung 10–25 % · half-time > 25 %. Leave below 7.5 % / 22.5 %. | **straight:** 16ths on the grid. **swung:** odd 16ths 0.24 of a 16th late (62 % swing). **half-time:** kick on 1 and the "and" of 2, clap on 3, 8th hats, sparser bass, stabs and plucks; the last two beats of every 4-bar loop are a triplet fill (16th-triplet hats, 8th-triplet snares). |
| **harmony** | running z | rungs at z ≥ 0.5 / 1 / 2 / 3, leave below 0 / 0.5 / 1.5 / 2.5. Climb at most one rung per bar. | **0 tonic:** T · Ts. **1 subdominant:** T · S. **2 dominant:** S · D. **3 dominant + tensions:** (S Dt) · Dt. **4 secondary dominants:** (E7 Dt) · (G♯°7 Dt). The cell alternates every bar, so the chord changes every bar; rungs 3–4 also change on the half bar. A fall from rung ≥ 2 to ≤ 1 plays a | Dt | T | cadence bar. |
| **timbre** | harmonic rung | fixed table, below | music-bus low-pass, pad filter centre, saturation drive |
| **echo** | persistence r by hour | feedback = 0.55·r², capped at 0.55 (0.25–0.51) | dotted-8th echo on plucks, stabs and lead. Repeats filtered 350 Hz – 2.4 kHz. This is a network property, the same on every day. |
| **melody** | smoothed surface delay | 1 scale step per 30 s, from D4 | Notes from the chord-scale. Stepwise, leap ≤ 4 steps and ≤ 7 semitones. Downbeats are chord tones. 4-bar phrases end on root or fifth, 8-bar phrases on root. |
| **volume per instrument** | stop events per mode | sqrt(n / day max), as in v1 | |

Timbre by rung:

| rung | music low-pass | pad filter centre (LFO ± 45 %) | drive k in y = tanh(k·x)/k |
|---|---|---|---|
| 0 tonic | 1.4 kHz | 450 Hz | 1.0 (dark, soft) |
| 1 subdominant | 2.2 kHz | 700 Hz | 1.5 |
| 2 dominant | 3.4 kHz | 1.1 kHz | 2.2 |
| 3 dominant + tensions | 5.2 kHz | 1.7 kHz | 3.2 (bright, edgy) |
| 4 secondary dominants | 8 kHz | 2.6 kHz | 4.5 |

The five drive curves run in parallel and are crossfaded per bar (40 ms), so the switch does not click. y = tanh(k·x)/k has unity gain for small signals, so the drive adds harmonics without raising the level.

**Per-hit displacement is dropped.** v2's first version moved each mode's hits by its own lateness classes. The network lateness share now drives the groove instead, and the per-mode microtiming is gone, to keep the half-time and swung patterns clean.

## Why these cut-offs (a priori)

- **z 0 / 1 / 2 / 3 and hysteresis 0.5 SD.**
  - 0 = the normal day.
  - 1 SD = clearly worse than normal.
  - 2 and 3 SD = the usual "unusual" and "extreme" marks.
  - 0.5 SD = half a standard deviation, the smallest band that keeps 3-window noise from flipping states.
  - Density uses 0 / 1 / 2. Harmony uses 0.5 / 1 / 2 / 3, so the dominant arrives with the lifted arrangement.
- **Lateness 10 % / 25 %.**
  - One stop event in ten more than 90 s late is occasional lateness; one in four is systemic.
  - The values are round shares, fixed before the per-day results were known. They were taken from the brief, not fitted.
  - The hysteresis is 2.5 points, a quarter of the narrowest class.
  - Consequence: the busy days (typical, school, meltdown) are mostly half-time in the morning rush, and the calm days (Easter, summer Sunday) swing.
- **Swing 62 %.** The standard drum-machine shuffle setting; 66.7 % would already be a full triplet.
- **Master trim −5 / −2 / −1 / 0 dB by density.** It sits after the limiter, so the compressors cannot level it away and a sparse day is also quieter. It was set from the measured loudness of the first renders, not by listening.

## Chords, voicing and key

- **Key and mode** follow v1's rule unchanged: D, with the mode by mean surface delay (< 40 s lydian, < 70 s ionian, < 100 s dorian, < 130 s aeolian, else phrygian).
- **T** is the diatonic seventh on degree 1. **Ts** is the relative chord (vi in lydian and ionian, III otherwise). **S** is IV (II in lydian).
- **D** is A7 in every mode: C♯ and G♮ are borrowed as in harmonic minor, and E is left out in phrygian.
- **Dt** adds the mode's 9th (B, or B♭ in aeolian and phrygian). Phrygian also gets ♯11 (E♭).
- **The pad** is 4 voices in G3–E5 that glide between chords:
  - least total motion;
  - no voice crossing;
  - no parallel fifths or octaves (checked: 0 on all days, both scales).
- **Bass** plays the chord root and walks in with the chromatic leading note before a change.

## Palette

The v2 palette is techno, separate from v1's disco.

| instrument | sound |
|---|---|
| kick | deep 130 → 42 Hz sine sweep, 0.48 s decay, short click |
| bass | rolling 16ths (straight or swung) or offbeat 8ths (half-time); two saws ±7 cents through a resonant low-pass (Q 9) with its own envelope, opening further with the rung's drive |
| pad | 4 persistent saw pairs (±4 cents) through a resonant low-pass whose cutoff is swept by a sine LFO, one cycle per 2 bars |
| hats | darker band-passed noise (6.2 kHz, high-pass 3.8 kHz) |
| stabs | dub-techno chord stabs into the echo |
| lead | saw, plus a square-wave second voice in the lifted and extreme states |

## Mix

- **Signal chain:** music bus (bass, pad, stabs, plucks, arp, leads, echoes) → drive → tone low-pass → sidechain duck (to 0.3 on every kick, back within 0.32 s) → mix (0.40) → glue compressor (−20 dB, 2.5:1) → limiter (−4 dB, 20:1, 2 ms) → density trim → soft ceiling → volume.
  - The soft ceiling is linear to −2.5 dBFS and never passes −0.5 dBFS.
- **Drum bus** runs in parallel straight into the mix.
- **Reverb:** subtle and optional, a 1.8 s deterministic impulse, return 0.16.

## Renders and checks

- `renderOffline({engine, day, startBin, seconds, bpm, binBeats})` renders with an OfflineAudioContext in headless Chromium.
- Review set: 07:00–09:30 at 120 BPM, one bar per 5-min window (30 bars = 60 s), default volume 85 %.
- No render has a sample above −0.3 dBFS.
