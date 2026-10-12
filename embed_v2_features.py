"""Embed the v2 features that engine v2 uses into index.html as `const DATA2`.

Input: sonification_v2.json written by the thesis extractor `extract_v2.py`
(aggregates only; see docs/ENGINE_V2.md). Only four things are kept:

  z     per day: the network-level ("surface": bus + tram + trolleybus) anomaly
        z per 5-minute bin, rounded to 0.01. null where undefined.
  cls   per day x mode (tram, bus, trolleybus): the lateness-class shares
        l30 (30-90 s], l90 (90-180 s], l180 (>180 s) per bin. The engine pools
        l90 + l180 over the three surface modes into the groove state. Encoded as three
        characters per bin from the base64 alphabet, value = round(pct / 2), so
        the resolution is 2 percentage points. "..." marks a bin with no events.
  pers  lag-1 persistence r per local hour over the whole period (173 days):
        tram, and surface = event-weighted mean of bus, tram and trolleybus r.
        Hours where r is undefined (n < 30) fall back to the pooled r_all.

Dropped on purpose: per-mode z, p50/p90, per-day persistence and the west/east
geography (its split is skewed ~70/30 by regional stops, see the docs).

Usage:
    python embed_v2_features.py ../sonif-v2/sonification_v2.json
"""
import json
import re
import sys
from pathlib import Path

B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
CLS_MODES = ["tramvaj", "autobus", "trolejbus"]
SURFACE = ["autobus", "tramvaj", "trolejbus"]


def enc_cls(cls):
    out = []
    for i in range(288):
        vals = [cls[k][i] for k in ("l30", "l90", "l180")]
        if any(v is None for v in vals):
            out.append("...")
            continue
        out.append("".join(B64[min(63, int(v / 2 + 0.5))] for v in vals))
    return "".join(out)


def surface_r(profile):
    r_out = []
    for h in range(24):
        num = den = 0.0
        for m in SURFACE:
            p = profile[m]
            if p["r"][h] is not None and p["n"][h]:
                num += p["r"][h] * p["n"][h]
                den += p["n"][h]
        if den:
            r_out.append(round(num / den, 3))
        else:
            r_out.append(round(sum(profile[m]["r_all"] for m in SURFACE) / 3, 3))
    return r_out


def main(src):
    d = json.loads(Path(src).read_text())
    prof = d["persistence_profile"]
    tram = [round(v, 3) if v is not None else round(prof["tramvaj"]["r_all"], 3)
            for v in prof["tramvaj"]["r"]]
    out = {
        "v": 2,
        "period": d["period"],
        "pers": {"tram": tram, "surface": surface_r(prof)},
        "days": {},
    }
    for day in d["days"]:
        z = [None if v is None else round(v, 2) for v in day["modes"]["surface"]["z"]]
        out["days"][day["id"]] = {
            "type": day["day_type"],
            "z": z,
            "cls": {m: enc_cls(day["modes"][m]["cls"]) for m in CLS_MODES},
        }
    line = "const DATA2 = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    html = Path(__file__).with_name("index.html")
    text = html.read_text()
    if re.search(r"^const DATA2 = .*;$", text, flags=re.M):
        text = re.sub(r"^const DATA2 = .*;$", lambda _: line, text, count=1, flags=re.M)
    else:
        text = re.sub(r"^(const DATA = .*;)$", lambda m: m.group(1) + "\n" + line, text,
                      count=1, flags=re.M)
    html.write_text(text)
    print(f"DATA2 embedded: {len(line):,} bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../sonif-v2/sonification_v2.json")
