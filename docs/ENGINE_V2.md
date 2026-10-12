# Engine v2

Engine v2 is the default; v1 stays available through the `engine v1 | v2` toggle and is unchanged.
v2 maps the data to arrangement, groove, harmony and timbre, so the five days sound clearly different.
It has two layers: **FORM** (verse, pre-chorus, drop, chorus) from the day's own delay curve, and **MOOD** (density, groove, harmony, timbre) from the anomaly against a normal day. Form says *when* the track lifts; mood says how dark, dense and tense it is when it does.

**Rules.**
- **Deterministic.** The noise behind hats and reverb uses a seeded generator, and the pad LFO is a plain oscillator, so a render of the same day is always identical.
- **Grounded in music theory.**
- **Thresholds fixed a priori**, in robust SD or percent. None was tuned by listening to the five days. The one exception in timing is the night-window rule, added after review (see Changes).

All constants are in `const V2`, `const TIMBRE`, `const HOOK_C` and `chorusPair` in `index.html`.

## Data used

`embed_v2_features.py` takes `sonification_v2.json` from the thesis extractor `extract_v2.py` ([FEATURES_V2.md](FEATURES_V2.md)) and writes `const DATA2` into `index.html` (about 22 KB, aggregates only).

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

- **Reliable windows only.** A window's surface z counts only if the window has at least 1 000 bus, tram and trolleybus stop events (`V2.MIN_SURF_N`). A window below that is treated as z = 0, the normal day, for density, harmony and timbre. Groove is unaffected, since it uses shares. See Changes below.
- **Running z** is the 5-minute surface z (after the rule above) smoothed over 3 windows (centred, undefined windows skipped).
- **Running lateness** = Σ n·(l90 + l180) / Σ n over bus, tram and trolleybus and the same 3 windows. `n` is the event count from the v1 data.
- **Every state is decided once per bar** from the values at the bar's downbeat window, with hysteresis.
- **Two scales:**
  - At the default scale (one 5-min window = one beat), one bar covers 20 minutes of data.
  - At the `1 bar` scale, one bar is one window.

## Form (song structure)

Added 12 October 2026 (see Changes). Computed per bar, from the values at the bar's downbeat window, at both scales.

- **Chorus.** A bar is a chorus bar when its downbeat window's smoothed surface delay (the v1 curve: event-weighted bus, tram and trolleybus mean delay, centred over 5 windows) is at or above the **day's 75th percentile** of that curve (`V2.CHORUS_Q`). The percentile is taken over reliable windows only, those with ≥ 1 000 surface stop events, the same rule as for z; a window below that can never be chorus. Linear interpolation between order statistics.
- **Length.** Verse gaps shorter than 2 bars between chorus bars are merged into the chorus first; then chorus runs shorter than 2 bars are dropped (`CHORUS_GAP`, `CHORUS_MIN`).
- **Pre-chorus** = the 2 bars before each chorus (`PRE`): a riser over both bars, an 8th-note snare roll in bar 1 and a 16th-note roll in bar 2, both in crescendo; the last beat before the drop is empty except for the snare, pad and lead. The extreme-state breakdown and the half-time triplet fill do not play in form bars; the pre-chorus is the build. The second half of the last pre-chorus bar plays the chorus's V-slot chord, a half cadence into the tonic.
- **Drop** = the first chorus bar: crash and a sub impact (sine 70 → 32 Hz), with kick, bass, pad and the hook only. The upper groove (hats, clap, stabs, plucks, arp, shaker, cowbell) enters on the next bar.
- **Verse** = everything else.
- **Arrangement.** Chorus bars (including the drop) play one density state above the mood state: sparse → full, full → lifted, lifted → extreme, extreme stays extreme. The density trim follows. The mood layer still sets groove, harmonic rung and timbre, so a calm Easter chorus is light and on the tonic, and a Meltdown chorus is dense and dark.
- **Grid.** The acid strip above the grid shows the chorus (form) again; the pre-chorus is the same strip at 35 %. The groove · density row still shows the mood state.

**Why the 75th percentile.** A round share fixed before any render: the chorus is the worst quarter of the day's own reliable windows. It replaces v1's hand-set 68 % of the day's peak, which depends on a single maximum. By construction every day gets about a quarter of its service day as chorus; *where* it falls is the data. It was not tuned by listening.

**The hook.** One fixed 4-bar motif, the same every day, transposed to the day's mode (scale degrees, 1 = D):

| bar | degrees | 16th positions (lengths) |
|---|---|---|
| 1 | 1 – 3 – 5 | 0 (3) · 3 (3) · 6 (6) |
| 2 | 4 – 3 – 2 | 0 (3) · 3 (3) · 6 (6) |
| 3 | 3 – 4 – 5 | 0 (3) · 3 (3) · 6 (6) |
| 4 | 4 – 3 – 2 – 1 | 0 (3) · 3 (3) · 6 (2) · 8 (8) |

- A tresillo (3 + 3 + 2) rhythm in every bar; the melody outlines 1-3-5 and walks 4-3-2-1 home.
- It sings from D5 (`HOOK_BASE` 74) on the main lead voice, and repeats every 4 bars from the drop for as long as the chorus lasts. Each degree takes the chord-scale (the day's scale with the current chord's tones replacing degrees of the same letter, as for the data melody), so it never clashes with the harmony.
- In the verse the lead keeps the data melody. In the chorus the data melody moves an octave down to the second (square) voice as a counter-line; the diatonic third below is not played there.

**Chorus progression.** One chord per bar, restarting at the drop, aligned with the hook: **T – V – Ts – S**. In the major modes this is I–V–vi–IV (lydian: I–V–vi–II, since S is II there); in the minor modes i–V–III–iv. T, Ts and S are the existing chords and voicings. The harmonic rung changes only the V slot (and, from rung 3, the S slot's second half):

| rung | V slot | S slot |
|---|---|---|
| 0–1 | V5: the diatonic seventh on degree 5 (Amaj7 lydian, A7 ionian, Am7 dorian and aeolian; A7 in phrygian, whose diatonic v is diminished) | S |
| 2 | D (A7) | S |
| 3 | Dt | S, then Dt on the half bar |
| 4 | E7 (V/V), then Dt on the half bar | S, then Dt on the half bar |

Voice leading is unchanged (least motion, no crossing, no parallel fifths or octaves: checked 0 on all days, both scales). The verse keeps the ladder cells and the cadence rule.

**Chorus time per day** (chorus incl. drop; pre-chorus not counted):

| day | 75th pct of smoothed delay | 5 min = 1 beat (20-min bars) | 5 min = 1 bar |
|---|---|---|---|
| Typical Tuesday | 103 s | 300 min: 07:40–10:00, 15:00–17:40 | 295 min |
| The Meltdown | 193 s | 260 min: 14:40–19:00 | 295 min (incl. 07:55–08:20) |
| Easter Monday | 45 s | 280 min: 14:20–19:00 | 295 min |
| Back to School | 98 s | 300 min: 07:20–12:20 | 295 min |
| Summer Sunday | 56 s | 320 min: 12:20–13:00, 14:20–19:00 | 290 min |

## Mapping table

| musical dimension | data | states and thresholds | what changes |
|---|---|---|---|
| **density** (mood) | running z | sparse < 0 · full 0–1 · lifted 1–2 · extreme ≥ 2. Enter at 0 / 1 / 2, leave below −0.5 / 0.5 / 1.5 (0.5 SD hysteresis). May jump several states. | **sparse:** kick, bass and pad only, master trim −5 dB. **full:** + hats, clap, stabs, plucks, lead (−2 dB). **lifted:** + arp, shaker, second lead voice a diatonic third below, open hats, 16th ghost hats, cowbell when trolleybus traffic is dense (−1 dB). **extreme:** on entry a 2-bar breakdown (kick, bass and drums drop; pad, lead and a riser; snare roll in the last two beats), then everything, with cowbell always (0 dB). A crash marks every entry into lifted or extreme. In the chorus the arrangement is one state higher (Form). |
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
- **Master trim −5 / −2 / −1 / 0 dB by density.** It sits after the limiter, so the compressors cannot level it away and a sparse day is also quieter. This is a mix decision, not a data-mapping threshold: the values were set from the measured loudness of the first renders. No mapping threshold (z, lateness share, persistence, melody step) was tuned by listening.

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

## Changes

**12 October 2026: a real chorus again (FORM layer).**
- **Why.** Bára's listening feedback on the v2 renders: "it feels like we're missing a chorus". v2 had replaced v1's chorus with anomaly states, so a typical day barely lifted and a calm day never did.
- **Rule.** Chorus = bars whose smoothed surface delay is in the day's top quartile (≥ 75th percentile of reliable windows, ≥ 1 000 surface events), at least 2 bars, gaps under 2 bars merged; a 2-bar pre-chorus, a 1-bar drop on entry, verse elsewhere. The chorus plays one density state above the mood, sings a fixed 4-bar hook, and runs a fixed T–V–Ts–S progression whose V slot follows the harmonic rung. Details under Form.
- **Fixed before rendering.** The quartile, the 2-bar lengths, the hook and the progression were fixed before any v2c render was made and were not adjusted after listening.

**12 October 2026: night windows count as normal.**
- **What was found.** An independent review of the first v2 states found that night windows with few events, about 250–450 surface stop events per 5 minutes, produced noise-sized z values. The holidays turned lifted at 03:40–04:40, the Meltdown at 00:00–01:00, and the typical Tuesday at 04:00 and around 23:10. The extractor's guard (n ≥ 5 per cell) does not exclude these windows.
- **Rule.** A window's z counts only with at least 1 000 surface stop events; otherwise z = 0 for density, harmony and timbre.
- **Why a count and not a standard-error rule.** The preferred rule, SE of the window mean ≤ 0.5 × spread, needs the per-event dispersion of each window. That dispersion is not in the published aggregates, so the rule could not be checked from this repository. The event count is published (`sonification_days.json`), so the count rule can be checked from the repository.
- **Where 1 000 falls.** On all five days every window between 06:00 and 22:00 has at least 1 201 surface stop events. Windows below 1 000 are the night, about 00:00–05:00, plus 23:05 on the typical Tuesday.
- **Not tuned to the music.** The rule was chosen after the review found the noise, so it is post hoc. Its value was fixed as a round count from the event counts alone, and it was not adjusted to change how any of the five days sounds.

