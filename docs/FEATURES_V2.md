# Delayed All the Time: v2 data features

Produced by `extract_v2.py` and written to `sonification_v2.json` (598,568 bytes, about 585 KiB, compact JSON, UTF-8).
The file holds aggregates only. It contains no stop events, trip ids or stop ids.

## Source and sample

- Data: `prague_transit.duckdb` (the thesis build; path via `SONIF_DB`, not redistributed), table `stop_times_history_modeling`, opened read-only. It holds about 121.2 M stop events across 173 partition days, 2025-03-16 to 2025-09-07.
- **No sampling.** Every pass reads the full table.
- Runtime: about 32 s wall time on DuckDB 1.5.6 with `threads=2`, `memory_limit=6GB` and `nice -n 20`. The queries run one after another, and peak RSS was about 2.6 GB.
- Coordinates come from the PID GTFS `stops.txt` (a Sep 2026 feed; path via `SONIF_STOPS`), joined on `gtfs_stop_id = stop_id`.

## Shared definitions (identical to v1 `extract_sonification_data.py`)

| item | definition |
|---|---|
| delay | `current_stop_arr_delay` in seconds. Rows that are NULL or outside **[-600, 3600]** are dropped, not winsorised |
| bin | local time (`current_stop_arrival AT TIME ZONE 'Europe/Prague'`), `(hour*60+minute)//5`, giving 288 bins |
| mode | `route_type`: autobus, tramvaj, trolejbus, metro, vlak, přívoz |
| day | the `year/month/day` partition columns, as in v1. These match the local date of `current_stop_arrival` for 99.2 % of rows. The remaining rows are mostly late-evening trips from the previous local day |
| five days | typical 2025-06-17, meltdown 04-30, easter 04-21, school 09-01, summer 07-13 |
| surface | an event-weighted pooled series for autobus + tramvaj + trolejbus. It is stored as the pseudo-mode `"surface"` |

## 1. Baseline and anomaly (z)

- **Day type.** `weekday` is Mon–Fri excluding holidays (120 days). `saturday` is non-holiday Saturdays (23 days). `sunday_holiday` is Sundays plus the holidays 18 Apr, 21 Apr, 1 May, 8 May, 5 Jul and 6 Jul (30 days). The holiday 5 Jul falls on a Saturday and therefore counts as `sunday_holiday`.
- **Per-day value.** This is the mean delay of a (day, mode, bin) cell. A cell enters the baseline only if it has **n ≥ 5** events (`min_n`).
- **Baseline.** Across all days of the given type in the full period, with each day itself included, the extractor takes the median of the per-day means (`med`) and the spread `spr = 1.4826 × MAD` (`spr`). A baseline cell needs **at least 5 contributing days** (`min_days`) and is `null` otherwise. Each baseline entry also stores `min_days` and `max_days`, the range of day counts over the bins.
- **z.** `z = (day mean − med) / max(spr, 5 s)`. It is `null` when the day cell has n < 5 or the baseline is null.
- **Spread floor = 5 s.** The raw spreads have a median of 11.4 s and a 5th percentile of 2.5 s. A 15 s floor would have bound in 60 % of cells and flattened z for bus and tram. At 5 s the floor binds in 4 % of autobus cells, 5 % of tramvaj, 9 % of surface and 0 % of trolejbus and vlak. It binds in **97 % of metro cells**, because the raw metro spread is about 2–4 s. Metro z is therefore effectively Δ / 5 s.
- **Network-level anomaly.** The `"surface"` pseudo-mode gets its own baseline and z, computed the same way from its event-weighted per-day mean.
- **Ferry (přívoz)** has no baseline and its z is always null. It runs about 25 events per day, so almost no bin reaches n ≥ 5.

## 2. Lateness distribution (five days only)

Per mode and bin, `cls` holds integer percentages of stop events in five classes:
`early` < −30 s; `on` [−30, 30]; `l30` (30, 90]; `l90` (90, 180]; `l180` > 180 s.
Rounding means the five classes may sum to 99–101. The arrays `p50` and `p90` are `quantile_cont` values in seconds. Fields are `null` where a bin has no events. The surface pseudo-mode has no `cls`, `p50` or `p90`.

## 3. Persistence

- **Trip and sequence columns.** The table has `rt_trip_id` and `gtfs_stop_sequence`, and each row also carries `next_stop_arr_delay`, the real arrival delay at the next stop of the same trip. On 17 Jun, `next_stop_arr_delay` equals the next row's `current_stop_arr_delay` in 99.3 % of the rows where both exist. The pair also covers the final segment into the terminal stop, which has no row of its own.
- **Pair.** x = arrival delay at stop k and y = arrival delay at stop k+1. Both must lie in [−600, 3600].
- **Measures,** per mode × local hour of the arrival at stop k:
  - `r` is the Pearson lag-1 correlation of x and y.
  - `slope` is the OLS slope of y on x (cov/var(x)), read as the share of delay retained at the next stop.
  - `n` is the number of pairs. `r` and `slope` are null when n < 30.
  - `r_all` and `slope_all` are the same measures pooled over all hours.
- **Where it is stored.** `persistence_profile` holds the whole period with all 173 days pooled. `days[].persistence` holds each of the five days.

## 4. Geography

- **Split.** The split longitude is the median longitude of the distinct stops that occur in the period and match GTFS: **14.50046** over 16,394 stops. That set includes regional PID stops, so the split lies east of central Prague (about 14.42). As a result **about 70 % of events fall in the west half.**
- **Coverage.** 98.8 % of events on the five days have coordinates. Stops without a match are excluded. They are mostly bus and tram stops, plus 15 of the 25 ferry events on 17 Jun.
- **Contents.** `days[].geo[mode].{west,east}` holds `n` and `delay`, the mean delay per bin, for every mode and for `surface`.

## JSON layout

```
version, bin_minutes, clip_s, period, n_days, modes, surface, params, geo{lon_split,n_stops,event_coverage}
baseline.{weekday|saturday|sunday_holiday}: n_days, <mode|surface>: {med[288], spr[288], min_days, max_days}
persistence_profile.<mode>: {r[24], slope[24], n[24], r_all, slope_all}
days[]: id, label, sub, disc, date, day_type, total,
        modes.<mode>: {n, delay, z, p50, p90, cls{early,on,l30,l90,l180}}   (surface: n, delay, z)
        persistence.<mode>: as in persistence_profile
        geo.<mode|surface>.{west,east}: {n[288], delay[288]}
```
`n` is 0 and `delay` is null for empty bins. Note that v1 wrote 0 for an empty delay, while v2 writes null.

## Sanity summary (five days)

Mean |z| and share of bins with z > 1, over all bins where z is defined:

| day | surface | autobus | tramvaj | trolejbus | metro | vlak |
|---|---|---|---|---|---|---|
| typical | 0.45 / 0.06 | 0.48 / 0.04 | 0.58 / 0.18 | 0.66 / 0.05 | 0.74 / 0.20 | 0.83 / 0.17 |
| meltdown | 2.82 / 0.70 | 3.23 / 0.71 | 1.29 / 0.49 | 1.65 / 0.45 | 0.33 / 0.01 | 0.72 / 0.18 |
| easter | 1.50 / 0.01 | 1.50 / 0.01 | 0.88 / 0.03 | 0.92 / 0.04 | 0.80 / 0.08 | 0.92 / 0.00 |
| school | 1.10 / 0.21 | 1.25 / 0.24 | 0.56 / 0.06 | 0.57 / 0.09 | 0.34 / 0.01 | 0.70 / 0.16 |
| summer | 0.73 / 0.02 | 0.66 / 0.04 | 0.90 / 0.04 | 0.78 / 0.19 | 0.44 / 0.01 | 0.64 / 0.06 |

Surface figures for 06:00–22:00:

| day | mean z | max z | share of bins z > 1 | event-weighted mean delay |
|---|---|---|---|---|
| typical | +0.10 | 1.3 | 0.05 | 92 s |
| meltdown | +3.48 | 10.0 | 0.85 | 181 s |
| easter | −1.67 | −0.4 | 0.00 | 38 s |
| school | +0.50 | 5.2 | 0.27 | 89 s |
| summer | −0.66 | 0.8 | 0.00 | 46 s |

The large |z| for Easter is negative: it sits below even the Sunday/holiday baseline.

Persistence `r_all` / `slope_all`:

| day | autobus | tramvaj | trolejbus | metro | vlak | přívoz |
|---|---|---|---|---|---|---|
| period | 0.945 / 0.990 | 0.944 / 0.963 | 0.931 / 0.970 | 0.936 / 0.997 | 0.964 / 0.984 | 0.653 / 0.788 |
| typical | 0.933 / 0.985 | 0.936 / 0.953 | 0.898 / 0.948 | 0.705 / 0.878 | 0.964 / 0.983 | n<30 |
| meltdown | 0.980 / 1.005 | 0.954 / 0.971 | 0.969 / 0.989 | 0.477 / 0.813 | 0.960 / 0.978 | n<30 |
| easter | 0.891 / 0.937 | 0.857 / 0.900 | 0.799 / 0.890 | 0.864 / 0.949 | 0.944 / 0.960 | n<30 |
| school | 0.939 / 0.986 | 0.926 / 0.943 | 0.872 / 0.915 | 0.548 / 0.786 | 0.955 / 0.978 | 0.721 / 0.926 |
| summer | 0.916 / 0.958 | 0.853 / 0.891 | 0.893 / 0.922 | 0.510 / 0.756 | 0.943 / 0.964 | 0.837 / 0.988 |

Hourly `r` in the period profile ranges from 0.83 to 0.97 for autobus and from 0.68 to 0.96 for tramvaj, with the lowest values between 01:00 and 04:00.

Lateness shares for surface modes pooled, 06:00–22:00, in % for early / on / 30–90 / 90–180 / >180:
typical 8 / 33 / 24 / 18 / 17; meltdown 6 / 26 / 21 / 18 / 29; easter 11 / 47 / 25 / 12 / 5; school 9 / 34 / 25 / 17 / 16; summer 10 / 44 / 26 / 13 / 6.

Surface mean delay west / east, 06:00–22:00: typical 84 / 110 s, meltdown 158 / 233 s, easter 37 / 40 s, school 82 / 103 s, summer 44 / 50 s.

**Meltdown vs typical.** The meltdown separates clearly. Its daytime surface mean z is +3.48 against +0.10 on the typical day, and 85 % of its daytime bins have z > 1 against 5 %. The separation comes from bus, followed by trolleybus and tram. Metro and train show no separation on that day (metro mean |z| is 0.33, train 0.72).

## Caveats

- The baseline includes the target day. With 30 days in the Sunday/holiday pool the effect is small, and it is negligible for weekdays.
- The weekday baseline pools school term with the Jul–Aug summer holidays, and makes no adjustment for bridge days such as 2 May and 9 May.
- Persistence r is close to saturation, between 0.85 and 0.98 for surface modes. Differences between days are small for bus and tram, and r alone mostly captures the delay level. Metro r is unstable on single days because its delay variance is tiny.
- The GTFS stops file is a 2026 feed. Stop ids missing from it, 1.2 % of events, are dropped from the geography section only.
- Delays outside [−600, 3600] are dropped rather than capped, which keeps v1 behaviour.
