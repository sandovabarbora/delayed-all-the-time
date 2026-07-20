"""Extract 5-minute traffic aggregates for the sonification player.

Reads prague_transit.duckdb (table stop_times_history_modeling) and writes
sonification_days.json — per selected day, per transport mode, 288 five-minute
bins of: stop-event count, mean arrival delay, p90 arrival delay.

Run from the diplomka/ directory:
    python sonification/extract_sonification_data.py
"""
import duckdb
import json
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "prague_transit.duckdb"
OUT = Path(__file__).resolve().parent / "sonification_days.json"

# Five days, five moods. Selection criteria (all computed over the full dataset,
# weekdays = dow 1-5, delays clipped to [-600, 3600] s):
#   typical  – weekday closest to the median of both daily event count and mean delay
#   meltdown – highest daily mean delay in the data
#   easter   – lowest daily mean delay in the data (Easter Monday)
#   school   – first school day of the year
#   summer   – holiday-season Sunday with the lowest traffic
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

BINS = 288  # 24 h in 5-minute windows

con = duckdb.connect(str(DB), read_only=True)
out_days = []
for D in DAYS:
    # NB: DuckDB "/" is float division — the "// 5" integer division is load-bearing
    df = con.execute(f"""
        SELECT route_type,
               ((extract(hour   FROM current_stop_arrival AT TIME ZONE 'Europe/Prague')*60
               + extract(minute FROM current_stop_arrival AT TIME ZONE 'Europe/Prague'))::INT // 5) AS bin5,
               count(*)                                    AS n,
               avg(current_stop_arr_delay)                 AS avg_delay,
               quantile_cont(current_stop_arr_delay, 0.9)  AS p90_delay
        FROM stop_times_history_modeling
        WHERE year={D['y']} AND month={D['m']} AND day={D['d']}
          AND current_stop_arr_delay IS NOT NULL
          AND current_stop_arr_delay BETWEEN -600 AND 3600
        GROUP BY 1,2 ORDER BY 1,2
    """).df()

    modes = {}
    for mode, g in df.groupby("route_type"):
        arr_n = [0]*BINS; arr_d = [0]*BINS; arr_p = [0]*BINS
        for _, r in g.iterrows():
            b = int(r["bin5"])
            if 0 <= b < BINS:
                arr_n[b] = int(r["n"])
                arr_d[b] = round(float(r["avg_delay"]), 1)
                arr_p[b] = round(float(r["p90_delay"]), 1)
        modes[mode] = {"n": arr_n, "delay": arr_d, "p90": arr_p}

    out_days.append({"id": D["id"], "label": D["label"], "sub": D["sub"],
                     "disc": D["disc"], "total": int(df["n"].sum()), "modes": modes})
    print(D["id"], "events:", int(df["n"].sum()))

json.dump({"bin_minutes": 5, "days": out_days}, open(OUT, "w"))
print("written", OUT)
