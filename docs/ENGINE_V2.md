# Engine v2

Engine v2 is the default engine. v1 is still available through the `engine v1 | v2` toggle and works exactly as the README describes.
In v2 the data drives tension and release and never adds noise. Every musical decision follows from the data, deterministically:
the noise behind the hats and the reverb impulse comes from a seeded generator, so two renders of the same day are identical.

## Data used

`embed_v2_features.py` takes `sonification_v2.json`, written by the thesis extractor `extract_v2.py`, and writes `const DATA2` into `index.html` (about 26 KB, aggregates only).
`FEATURES.md`, which ships next to the extractor, has the definitions.

| feature | used for | kept in DATA2 |
|---|---|---|
| surface (bus + tram + trolleybus) anomaly z per 5-min bin, against the median day of the same day type, in robust SD (MAD × 1.4826, floor 5 s) | chorus and harmony | `z`, rounded to 0.01 |
| lateness-class shares per mode × bin: l30 (30–90 s], l90 (90–180 s], l180 > 180 s | rhythmic displacement | `cls`, 3 chars per bin, base64, value = round(% / 2), so the resolution is 2 points |
| persistence: lag-1 r per mode × local hour, pooled over all 173 days | echo feedback | `pers.tram`, `pers.surface` (the event-weighted mean of bus, tram and trolleybus) |

Not used:
- **Per-mode z** and **p50/p90.**
- **Per-day persistence.** Persistence r is 0.89–0.98 on every day. It sits near its ceiling and barely separates the days, so v2 treats it as a property of the network that changes only with the time of day.
- **West/east delay.** The split longitude 14.50 is the median over all PID stops, regional ones included, so about 70 % of events fall "west". A Prague-only recompute needs the source database, which is not part of this repository. The feature is dropped instead of being used skewed.
- **The ferry** has no baseline. It only rings its bell, now on A5, the fifth of the key, which is diatonic in all five modes.

All the constants below are in `const V2` in `index.html`.

## Time

- One five-minute bin is one beat at the default scale, as in v1 (288 beats, 116 BPM, 2:29 per day). The `5 min = 1 bar` scale stretches a bin to a bar, so a day lasts about 10 min.
- **Structure is decided in data time,** in blocks of 4 bins (20 min), aligned to midnight. At the default scale one block is one bar.
- **Surface rhythm is in musical time.** Hits sit on a 16th grid in 4-bar loops.
- **v2 plays straight, with no global swing.** Any looseness you hear comes from lateness in the data.

## A. Lateness → rhythm, inside the metre

Every displaceable instrument has a 4-bar pattern, given in 16th positions per bar:

| instrument | mode | bars 1–3 | bar 4 |
|---|---|---|---|
| bass | metro | 0 2 4 6 7 8 10 12 14 15 | same |
| hats | tram | 2 3 6 10 11 14 | 2 3 6 7 10 11 14 15 |
| plucks | tram | 2 5 7 10 13 15 | 1 3 6 9 11 14 |
| stabs | bus | 2 6 10 14 15 (bar 3: 6 14 15) | 2 6 10 14 15 |
| clap / cowbell | trolleybus | 4 12 / 0 8 | same |

The kick (0 4 8 12) is the grid itself and never moves. The tambourine, arp and pad also stay on the grid, as the reference you hear the displacement against.

**Fixed priority order.**
1. All hits of a pattern are sorted from weakest to strongest:
   - first by metrical weight inside the bar (downbeat 4, beat 3 → 3, beats 2 and 4 → 2, 8ths 1, 16ths 0);
   - then by hypermetre (bar 4 weakest, then bar 2, bar 3, bar 1);
   - then by position, later first.
2. Hit *i* of *H* gets the rank ρ = (i + 0.5) / H.

**Class of a hit.** Take the shares of the mode's own stop events in the bin where the hit falls:

| condition | class | displacement |
|---|---|---|
| ρ < l180 | > 180 s | triplet: to the next 16th-triplet position (+2/3, +1/3, +2/3, +1/3 of a 16th for the four 16ths of a beat) |
| ρ < l180 + l90 | 90–180 s | syncopated: pushed one 16th later |
| ρ < l180 + l90 + l30 | 30–90 s | laid back: +¼ 16th (a 64th) |
| otherwise | early or on time (±30 s) | on the grid |

So with constant shares, exactly share × H hits move, and the weakest move furthest.

- A displaced hit takes the chord that is sounding where it lands.
- If it lands on a hit the same instrument already has at that instant, the two merge.
- The "delay drama" slider scales the shares (100 % = the data).

Share of hits per class, 07:00–09:30, in % for grid / laid back / 16th / triplet:

| day | bass (metro) | hats | plucks | stabs (bus) | clap |
|---|---|---|---|---|---|
| Typical Tuesday | 80/15/3/3 | 37/20/22/20 | 33/29/22/16 | 33/21/18/27 | 47/20/20/13 |
| The Meltdown | 95/5/0/0 | 35/20/24/20 | 29/33/18/20 | 24/24/15/36 | 40/27/20/13 |
| Easter Monday | 97/3/0/0 | 55/31/10/4 | 56/29/16/0 | 67/15/12/6 | 67/33/0/0 |

## B. Anomaly z → harmonic tension

- **Key and mode** follow v1's rule unchanged. The root is D. The mode comes from the day's mean surface delay: < 40 s lydian, < 70 s ionian, < 100 s dorian, < 130 s aeolian, otherwise phrygian.
- **Block z** is the mean of the defined surface z values in each 20-minute block, or 0 if none are defined.

**Ladder.** The level is evaluated once per block. It climbs at most one rung per block and falls as far as z requires.

| rung | function | climb when z ≥ | leave when z < | 2-bar cell |
|---|---|---|---|---|
| 0 | tonic | – | – | T · Ts |
| 1 | subdominant | 0.5 | 0 | T · S |
| 2 | dominant | 1 | 0.5 | S · D |
| 3 | dominant + tensions | 2 | 1.5 | (S Dt) · Dt |
| 4 | secondary dominants / diminished | 3 | 2.5 | (V/V Dt) · (vii°7/V Dt) |

**Why these thresholds.** They are set a priori in robust SD and were not tuned on the five days:
- 1 SD is the chorus threshold, so the dominant arrives together with the chorus.
- 0.5 SD is half of that.
- 2 SD and 3 SD are the usual "unusual" and "extreme" marks.
- The hysteresis band is 0.5 SD on every rung.

**Harmonic rhythm.**
- Rungs 0–2 change chord on bar boundaries.
- Rungs 3–4 change on half bars.
- The cell restarts whenever the rung changes.

**Cadence.** When the level falls from rung ≥ 2 to rung ≤ 1, the first bar of that block is | Dt | T |, an authentic cadence on the half bar. A fall from rung 1 to rung 0 resolves plagally, S → T.

**Chords.** Pitch classes are spelled by scale letter.
- T = the diatonic seventh on degree 1.
- Ts = the relative chord: vi in lydian and ionian, III in dorian, aeolian and phrygian.
- S = IV (in lydian II, because lydian's IV is diminished).
- D = A7 in every mode. Its leading tone C♯ and seventh G♮ are borrowed where the mode lacks them, as in harmonic minor. The fifth E is left out where it is not diatonic (phrygian).
- Dt = D plus the 9th the mode allows (B in lydian, ionian and dorian; B♭ in aeolian and phrygian). Phrygian also gets ♯11 (D♯ = E♭), the only mode where it is diatonic. The pads play it rootless.
- V/V = E7. vii°7/V = G♯°7.

| mode | T | Ts | S | D | Dt |
|---|---|---|---|---|---|
| lydian | Dmaj7 | Bm7 | E7 | A7 | A9 |
| ionian | Dmaj7 | Bm7 | Gmaj7 | A7 | A9 |
| dorian | Dm7 | Fmaj7 | G7 | A7 | A9 |
| aeolian | Dm7 | Fmaj7 | Gm7 | A7 | A7♭9 |
| phrygian | Dm7 | F7 | Gm7 | A7 | A7♭9♯11 |

**Voice leading.**
- There are 4 pad voices in a fixed range, G3–E5 (MIDI 55–76), strictly ascending, so voices never cross.
- Each new chord takes the voicing with the least total semitone movement from the previous one. Voicings with parallel fifths or octaves between any voice pair are excluded.
- If the chord has 3 pitch classes, the root is doubled. If it has 5, the root is left out of the pads.
- On ties the voicing nearer the centre wins, then the lower one.
- The voices are 4 persistent oscillator pairs that glide to the new voicing (25 ms), so the voice leading is literally audible.
- The plan has been checked to contain zero parallels on all five days and at both scales.

**Bass.** The bass plays the chord root at D2–C♯3. On the last beat before a chord change it walks into the new root: a whole step on the "and", then the chromatic leading note.

**Detune.** Only a fixed chorus remains: stabs ±5 cents, pads ±4 cents. Delay no longer detunes anything.

## C. Persistence → feedback delay

- Plucks and lead each have a dotted-eighth delay (0.75 beat, follows the tempo slider).
- The repeats are filtered in the loop (high-pass 350 Hz, low-pass 2.4 kHz). Wet level is 0.32.
- Feedback = 0.55 · r², capped at 0.55. Here r is the period-wide lag-1 persistence of trams (for the plucks) or of surface transport (for the lead) at the current local hour. r² is the share of delay variance carried to the next stop.
- This is a property of the network: it changes only with the time of day and is the same on all five days.
- Range: tram 0.25 at 03:00 to 0.51; surface 0.36 to 0.51. Around 08:00 it is 0.50 for trams and 0.51 for surface.

## D. Structure

- **Chorus.** Block z above **+1.0** enters the chorus. It is left when block z falls below **+0.5** (Schmitt trigger), and only after at least **2 blocks** (40 min of data, 2 bars at the default scale; a chorus shorter than a 2-bar phrase is not heard as a section).
- **Why these numbers.** They are fixed a priori and not tuned by listening. +1 = one robust SD above a normal day of the same type. +0.5 = half of that, a standard hysteresis band.
- **Night rule.** v1's night rule (no metro before 05:00 or after 22:30 → night) is applied afterwards. Any chorus remnant shorter than 2 blocks goes back to verse.
- **Results:**
  - Typical Tuesday: 09:20–10:20.
  - Meltdown: 06:40–24:00.
  - Easter Monday: none.
  - Back to School: 05:20–07:40, 09:00–12:40 and 20:20–21:00.
  - Summer Sunday: none.
- **Pre-chorus break.** The last two beats before a chorus are a snare roll and a riser, and the chorus opens with a crash.
- **In the chorus** come the pad (louder), the arp and the tambourine. Levels rise by 15 %.

## E. Melody (Voice of the City)

- **Pitch from the data.** The target scale degree is round(surface delay / 30 s), with the delay taken from v1's smoothed event-weighted series. One step per 30 s, the width of the on-time band.
  - The range is D4 and up: data degrees 0–10, and with the motif up to 14 (two octaves).
- **Motif.** Fixed motif per bar: verse at 16ths 0 3 6 10 12 (offsets 0 1 0 2 1); chorus 0 3 6 10 12 14 (offsets 0 2 1 3 2 4).
- **Pitch set.** The chord-scale: the day's scale, with each chord tone replacing the scale degree of the same letter. So the melody uses C♯ under A7 and is always in tune with the chord.
- **Motion.** At most 4 scale steps and at most 7 semitones (a fifth) from the previous note. The largest leap on any day is 7 semitones.
- **Downbeats** snap to the nearest chord tone.
- **Phrases.** 4-bar phrases end, at 16th 12 of bar 4 and held 1.75 beats, on the chord's root or fifth (the third if the chord has no fifth). 8-bar phrases end on the chord's root.
- **Timing.** The melody stays on the grid.

## F. Mix

- **Signal chain:** instruments → buses → mix (0.42) → glue compressor (−20 dB, 2.5:1, 12 ms / 160 ms) → high shelf −3 dB at 7 kHz → limiter (−4 dB, 20:1, 2 ms / 120 ms) → soft ceiling → volume.
  - The soft ceiling is linear up to −2.5 dBFS, then a tanh knee that never passes −0.5 dBFS.
- **Buses:** the drum bus, plus a music bus that ducks to 0.4 on every kick and recovers within 0.3 s (sidechain).
- **Reverb:** subtle and optional (toggle), a 1.8 s deterministic impulse with return 0.16.

## Renders and checks

- **How they are made.** `renderOffline({engine, day, startBin, seconds, bpm, binBeats})` renders with an OfflineAudioContext in headless Chromium.
- **What was rendered.** The review excerpts are 07:00–09:30 at 120 BPM with `binBeats: 4`: one bar per 5 minutes, 30 bars = 60 s, default volume 85 %, for both engines.
- **Peaks and loudness.** No render has a sample above −0.3 dBFS. True peak is −2.2 to −3.1 dBTP. Loudness is −16.8 to −20.4 LUFS.
