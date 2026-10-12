"""Extract v2 features for the sonification player "Delayed All the Time".

Reads prague_transit.duckdb (table stop_times_history_modeling, read-only) and
writes sonification_v2.json — aggregates only, no stop events or trip ids:

  1. baseline   – per day type x mode x 5-min bin: median of the per-day mean
                  delay and a robust spread (MAD x 1.4826); per selected day a
                  z-score per bin, plus a network-level (surface) z-score
  2. lateness   – per selected day x mode x bin: shares of stop events in fixed
                  lateness classes, p50 and p90
  3. persistence – lag-1 correlation and regression slope of arrival delay
                  between consecutive stops of a trip, per mode x hour
                  (whole-period profile and per selected day)
  4. geography  – per selected day x mode x bin: mean delay west / east of the
                  median stop longitude (coordinates from PID GTFS stops.txt)

Definitions shared with v1 (extract_sonification_data.py): delay field
current_stop_arr_delay, clipped to [-600, 3600] s (rows outside are dropped),
local-time (Europe/Prague) 5-minute bins of current_stop_arrival, route_type
as mode, days selected by the year/month/day partition columns.

Inputs, neither redistributed here:
  - the thesis DuckDB build of the Golemio PID stop-time history
    (prague_transit.duckdb), default: next to this script, or SONIF_DB;
  - the PID GTFS stops.txt (only for the geography pass), default:
    gtfs/stops.txt next to this script, or SONIF_STOPS.
Output defaults to sonification_v2.json next to this script, or SONIF_OUT.

    SONIF_DB=/path/to/prague_transit.duckdb SONIF_STOPS=/path/to/stops.txt \
        python extract_v2.py
    python embed_v2_features.py sonification_v2.json
"""
import duckdb
import json
import os
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("SONIF_DB", HERE / "prague_transit.duckdb"))
STOPS = Path(os.environ.get("SONIF_STOPS", HERE / "gtfs" / "stops.txt"))
OUT = Path(os.environ.get("SONIF_OUT", HERE / "sonification_v2.json"))

# Same five days as v1 (selection criteria documented there).
DAYS = [
    dict(id="typical",  y=2025, m=6, d=17, label="Typical Tuesday",
         sub="17 Jun · the most median day in the data",        disc="Tue 17 Jun 2025"),
    dict(id="meltdown", y=2025, m=4, d=30, label="The Meltdown",
         sub="30 Apr · worst delays of the year, avg 158 s",    disc="Wed 30 Apr 2025"),
    dict(id="easter",   y=2025, m=4, d=21, label="Easter Monday",
         sub="21 Apr · the calmest day, avg 36 s",              disc="Mon 21 Apr 2025"),
    dict(id="school",   y=2025, m=9, d=1,  label="Back to School",
         sub="1 Sep · first school day + peak ferry season",    disc="Mon 1 Sep 2025"),
    dict(id="summer",   y=2025, m=7, d=13, label="Summer Sunday",
         sub="13 Jul · holiday-season Sunday, city half asleep", disc="Sun 13 Jul 2025"),
]

# Czech public holidays 2025 inside the data period (15 Mar – 8 Sep).
HOLIDAYS = {date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 1),
            date(2025, 5, 8), date(2025, 7, 5), date(2025, 7, 6)}

BINS = 288                 # 24 h in 5-minute windows
CLIP = (-600, 3600)        # seconds, same as v1
MIN_N = 5                  # min stop events for a day-bin mean to count
MIN_DAYS = 5               # min contributing days for a baseline cell
SPREAD_FLOOR = 5.0         # s; z denominator = max(MAD*1.4826, SPREAD_FLOOR)
MAD_K = 1.4826
SURFACE = ("autobus", "tramvaj", "trolejbus")
# lateness classes (s): early < -30 | on time [-30, 30] | (30, 90] | (90, 180] | > 180
CLASSES = ("early", "on", "l30", "l90", "l180")

DELAY_OK = f"current_stop_arr_delay BETWEEN {CLIP[0]} AND {CLIP[1]}"
LOCAL = "current_stop_arrival AT TIME ZONE 'Europe/Prague'"
# NB: DuckDB "/" is float division — the "// 5" integer division is load-bearing
BIN5 = f"((extract(hour FROM {LOCAL})*60 + extract(minute FROM {LOCAL}))::INT // 5)"
HOUR = f"extract(hour FROM {LOCAL})::INT"
DAY_KEY = "make_date(year::INT, month::INT, day::INT)"
SEL = " OR ".join(f"(year={D['y']} AND month={D['m']} AND day={D['d']})" for D in DAYS)


def day_type(dt):
    if dt in HOLIDAYS or dt.isoweekday() == 7:
        return "sunday_holiday"
    return "saturday" if dt.isoweekday() == 6 else "weekday"


def r1(x):
    return None if x is None else round(float(x), 1)


def median(xs):
    s = sorted(xs); k = len(s)
    return (s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2)


def robust(xs):
    m = median(xs)
    return m, MAD_K * median([abs(x - m) for x in xs])


def corr_slope(n, sx, sy, sxx, syy, sxy):
    if n < 30:
        return None, None
    cxy = sxy - sx * sy / n; vx = sxx - sx * sx / n; vy = syy - sy * sy / n
    if vx <= 0 or vy <= 0:
        return None, None
    return round(cxy / (vx * vy) ** 0.5, 3), round(cxy / vx, 3)


t0 = time.time()
con = duckdb.connect(str(DB), read_only=True)
con.execute("SET threads=2; SET memory_limit='6GB'")

# ---- 1. per-day mean delay per mode x bin, all days of the period ----------
rows = con.execute(f"""
    SELECT {DAY_KEY} AS dt, route_type, {BIN5} AS bin5,
           count(*) AS n, avg(current_stop_arr_delay) AS mean
    FROM stop_times_history_modeling
    WHERE current_stop_arr_delay IS NOT NULL AND {DELAY_OK}
    GROUP BY ALL
""").fetchall()
print(f"[1] day x mode x bin rows: {len(rows)}  ({time.time()-t0:.0f}s)")

daily = {}   # (dt, mode) -> {bin: (n, mean)}
for dt, mode, b, n, mean in rows:
    if 0 <= b < BINS:
        daily.setdefault((dt, mode), {})[b] = (n, mean)
# network-level surface series = event-weighted mean of bus + tram + trolleybus
for dt in {k[0] for k in daily}:
    acc = {}
    for mode in SURFACE:
        for b, (n, mean) in daily.get((dt, mode), {}).items():
            a = acc.setdefault(b, [0, 0.0]); a[0] += n; a[1] += n * mean
    daily[(dt, "surface")] = {b: (n, s / n) for b, (n, s) in acc.items()}

all_dates = sorted({k[0] for k in daily})
modes = sorted({k[1] for k in daily} - {"surface"})
series = modes + ["surface"]

baseline = {}  # dtype -> mode -> {med, spr, ndays}
for dtype in ("weekday", "saturday", "sunday_holiday"):
    dts = [d for d in all_dates if day_type(d) == dtype]
    baseline[dtype] = {"n_days": len(dts)}
    for mode in series:
        med = [None] * BINS; spr = [None] * BINS; nd = [0] * BINS
        for b in range(BINS):
            xs = [daily[(d, mode)][b][1] for d in dts
                  if b in daily.get((d, mode), {}) and daily[(d, mode)][b][0] >= MIN_N]
            nd[b] = len(xs)
            if len(xs) >= MIN_DAYS:
                m, s = robust(xs); med[b] = r1(m); spr[b] = r1(s)
        baseline[dtype][mode] = {"med": med, "spr": spr, "min_days": min(nd), "max_days": max(nd)}

raw_spreads = sorted(s for bt in baseline.values() for k, v in bt.items() if k != "n_days"
                     for s in v["spr"] if s is not None)
print("[1] raw spread quantiles p05/p25/p50/p75/p95:",
      [raw_spreads[int(q * (len(raw_spreads) - 1))] for q in (.05, .25, .5, .75, .95)],
      f"share below floor {SPREAD_FLOOR}s:",
      round(sum(s < SPREAD_FLOOR for s in raw_spreads) / len(raw_spreads), 3))
for mode in series:
    ss = [s for bt in baseline.values() for s in bt.get(mode, {}).get("spr", []) if s is not None]
    if ss:
        print(f"    {mode}: floor binds in {sum(s < SPREAD_FLOOR for s in ss)/len(ss):.2f} of cells")

# ---- 2. lateness distribution for the five days ----------------------------
lat = con.execute(f"""
    SELECT {DAY_KEY} AS dt, route_type, {BIN5} AS bin5, count(*) AS n,
           avg(current_stop_arr_delay) AS mean,
           quantile_cont(current_stop_arr_delay, 0.5) AS p50,
           quantile_cont(current_stop_arr_delay, 0.9) AS p90,
           avg((current_stop_arr_delay < -30)::INT) AS early,
           avg((current_stop_arr_delay BETWEEN -30 AND 30)::INT) AS on_,
           avg((current_stop_arr_delay > 30 AND current_stop_arr_delay <= 90)::INT) AS l30,
           avg((current_stop_arr_delay > 90 AND current_stop_arr_delay <= 180)::INT) AS l90,
           avg((current_stop_arr_delay > 180)::INT) AS l180
    FROM stop_times_history_modeling
    WHERE ({SEL}) AND current_stop_arr_delay IS NOT NULL AND {DELAY_OK}
    GROUP BY ALL
""").fetchall()
print(f"[2] lateness rows: {len(lat)}  ({time.time()-t0:.0f}s)")
latd = {(r[0], r[1], r[2]): r[3:] for r in lat}

# ---- 3. persistence: arrival delay at stop k vs. k+1 of the same trip ------
# next_stop_arr_delay is the real arrival delay at the next stop of the same
# rt_trip_id (pre-joined in the table); both ends must be inside the clip.
pers = con.execute(f"""
    SELECT {DAY_KEY} AS dt, route_type, {HOUR} AS hr, count(*) AS n,
           sum(current_stop_arr_delay::DOUBLE) AS sx,
           sum(next_stop_arr_delay::DOUBLE) AS sy,
           sum(current_stop_arr_delay::DOUBLE^2) AS sxx,
           sum(next_stop_arr_delay::DOUBLE^2) AS syy,
           sum(current_stop_arr_delay::DOUBLE * next_stop_arr_delay) AS sxy
    FROM stop_times_history_modeling
    WHERE current_stop_arr_delay IS NOT NULL AND next_stop_arr_delay IS NOT NULL
      AND {DELAY_OK}
      AND next_stop_arr_delay BETWEEN {CLIP[0]} AND {CLIP[1]}
    GROUP BY ALL
""").fetchall()
print(f"[3] persistence rows: {len(pers)}  ({time.time()-t0:.0f}s)")


def pers_block(recs):
    acc = {}
    for _, mode, hr, *s in recs:
        a = acc.setdefault(mode, [[0.0] * 6 for _ in range(24)])
        for i, v in enumerate(s):
            a[hr][i] += v
    out = {}
    for mode, hrs in acc.items():
        rr, bb, nn = [], [], []
        for h in range(24):
            c, b = corr_slope(*hrs[h]); rr.append(c); bb.append(b); nn.append(int(hrs[h][0]))
        tot = [sum(h[i] for h in hrs) for i in range(6)]
        c, b = corr_slope(*tot)
        out[mode] = {"r": rr, "slope": bb, "n": nn, "r_all": c, "slope_all": b}
    return out


profile = pers_block(pers)

# ---- 4. geography: west / east of the median stop longitude ----------------
geo = None
if STOPS.exists():
    con.execute(f"""
        CREATE TEMP TABLE stops AS
        SELECT stop_id, stop_lon::DOUBLE AS lon
        FROM read_csv('{STOPS}', all_varchar=true) WHERE stop_lon IS NOT NULL
    """)
    lon_split, n_stops = con.execute("""
        SELECT median(s.lon), count(*) FROM
          (SELECT DISTINCT gtfs_stop_id FROM stop_times_history_modeling) u
        JOIN stops s ON u.gtfs_stop_id = s.stop_id
    """).fetchone()
    g = con.execute(f"""
        SELECT {DAY_KEY} AS dt, route_type, {BIN5} AS bin5,
               CASE WHEN s.lon < {lon_split} THEN 'west' ELSE 'east' END AS half,
               count(*) AS n, avg(current_stop_arr_delay) AS mean
        FROM stop_times_history_modeling m JOIN stops s ON m.gtfs_stop_id = s.stop_id
        WHERE ({SEL}) AND current_stop_arr_delay IS NOT NULL AND {DELAY_OK}
        GROUP BY ALL
    """).fetchall()
    cov = con.execute(f"""
        SELECT avg((s.stop_id IS NOT NULL)::INT) FROM stop_times_history_modeling m
        LEFT JOIN stops s ON m.gtfs_stop_id = s.stop_id
        WHERE ({SEL}) AND current_stop_arr_delay IS NOT NULL AND {DELAY_OK}
    """).fetchone()[0]
    geo = {"lon_split": round(lon_split, 5), "n_stops": n_stops,
           "event_coverage": round(cov, 4), "rows": g}
    print(f"[4] geo split lon={lon_split:.5f} over {n_stops} stops, "
          f"coverage {cov:.4f}  ({time.time()-t0:.0f}s)")
else:
    print(f"[4] {STOPS} not found — geography skipped")

# ---- assemble ---------------------------------------------------------------
out_days = []
for D in DAYS:
    dt = date(D["y"], D["m"], D["d"]); dtype = day_type(dt)
    day = {"id": D["id"], "label": D["label"], "sub": D["sub"], "disc": D["disc"],
           "date": dt.isoformat(), "day_type": dtype, "modes": {}}
    total = 0
    for mode in series:
        cells = daily.get((dt, mode), {})
        n = [0] * BINS; dl = [None] * BINS; z = [None] * BINS
        base = baseline[dtype][mode]
        for b, (cn, mean) in cells.items():
            n[b] = cn; dl[b] = r1(mean)
            if cn >= MIN_N and base["med"][b] is not None:
                z[b] = round((mean - base["med"][b]) / max(base["spr"][b], SPREAD_FLOOR), 2)
        rec = {"n": n, "delay": dl, "z": z}
        if mode != "surface":
            total += sum(n)
            p50 = [None] * BINS; p90 = [None] * BINS
            cls = {c: [None] * BINS for c in CLASSES}
            for b in range(BINS):
                v = latd.get((dt, mode, b))
                if v is None:
                    continue
                p50[b] = r1(v[2]); p90[b] = r1(v[3])
                for c, share in zip(CLASSES, v[4:]):
                    cls[c][b] = round(share * 100)   # integer percent
            rec.update(p50=p50, p90=p90, cls=cls)
        day["modes"][mode] = rec
    day["total"] = total
    day["persistence"] = pers_block([r for r in pers if r[0] == dt])
    if geo:
        gd = {}
        for gdt, mode, b, half, cn, mean in geo["rows"]:
            if gdt != dt or not 0 <= b < BINS:
                continue
            h = gd.setdefault(mode, {}).setdefault(
                half, {"n": [0] * BINS, "delay": [None] * BINS})
            h["n"][b] = cn; h["delay"][b] = r1(mean)
        # surface = event-weighted bus + tram + trolleybus, as in section 1
        for half in ("west", "east"):
            sn = [0] * BINS; sd = [None] * BINS
            for b in range(BINS):
                parts = [(gd[m][half]["n"][b], gd[m][half]["delay"][b]) for m in SURFACE
                         if half in gd.get(m, {}) and gd[m][half]["n"][b]]
                if parts:
                    sn[b] = sum(p[0] for p in parts)
                    sd[b] = r1(sum(p[0] * p[1] for p in parts) / sn[b])
            gd.setdefault("surface", {})[half] = {"n": sn, "delay": sd}
        day["geo"] = gd
    out_days.append(day)
    print(D["id"], dtype, "events:", total)

doc = {
    "version": 2, "bin_minutes": 5, "clip_s": list(CLIP),
    "period": [all_dates[0].isoformat(), all_dates[-1].isoformat()],
    "n_days": len(all_dates), "modes": modes, "surface": list(SURFACE),
    "params": {"min_n": MIN_N, "min_days": MIN_DAYS, "spread": "MAD*1.4826",
               "spread_floor_s": SPREAD_FLOOR,
               "classes_s": {"early": "<-30", "on": "[-30,30]", "l30": "(30,90]",
                             "l90": "(90,180]", "l180": ">180"},
               "holidays": sorted(d.isoformat() for d in HOLIDAYS)},
    "baseline": baseline,
    "persistence_profile": profile,
    "geo": {k: geo[k] for k in ("lon_split", "n_stops", "event_coverage")} if geo else None,
    "days": out_days,
}
OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
print("written", OUT, f"{OUT.stat().st_size/1024:.0f} KB", f"total {time.time()-t0:.0f}s")
