"""Builds price_index.json for the JoistLogic app.

Fetches the latest U.S. Producer Price Index value for each material
category (the series in lib/core/pricing/price_book.dart) and writes:

    {"asOf": "2026-10", "source": "BLS PPI", "series": {"WPU081": 283.1, ...}}

The app scales its built-in prices by latest / base for each category.

Data sources, in order:
  1. BLS Public Data API v2 (set BLS_API_KEY; free at https://data.bls.gov/registrationEngine/)
  2. BLS Public Data API v1 (no key, 25 requests/day)
  3. FRED CSV download (no key)

Run:  python tools/pricing/update_price_index.py out/price_index.json
"""
import csv
import io
import json
import os
import sys
import urllib.request

SERIES = ["WPU081", "WPU083", "WPU137", "WPU1333", "WPU133",
          "WPU1361", "WPU1392", "WPU0621", "WPU07", "WPU10"]
UA = {"User-Agent": "JoistLogic price index updater", "Content-Type": "application/json"}


def _latest_from_bls(payload):
    out, as_of = {}, None
    for s in payload.get("Results", {}).get("series", []):
        rows = [r for r in s.get("data", []) if r.get("period", "").startswith("M")
                and r.get("period") != "M13" and r.get("value") not in ("-", "")]
        if not rows:
            continue
        r = rows[0]  # BLS returns newest first
        out[s["seriesID"]] = float(r["value"])
        month = f'{r["year"]}-{r["period"][1:]}'
        as_of = month if as_of is None or month < as_of else as_of
    return out, as_of


def from_bls(version):
    body = {"seriesid": SERIES}
    key = os.environ.get("BLS_API_KEY")
    if version == 2:
        if not key:
            return {}, None
        body["registrationkey"] = key
    req = urllib.request.Request(f"https://api.bls.gov/publicAPI/v{version}/timeseries/data/",
                                 data=json.dumps(body).encode(), headers=UA, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(payload.get("message"))
    return _latest_from_bls(payload)


def from_fred():
    out, as_of = {}, None
    for sid in SERIES:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            rows = [row for row in csv.reader(io.StringIO(r.read().decode())) if row]
        for date, value in reversed(rows[1:]):
            if value not in (".", ""):
                out[sid] = float(value)
                month = date[:7]
                as_of = month if as_of is None or month < as_of else as_of
                break
    return out, as_of


def main(path):
    errors = []
    for name, fn in (("BLS v2", lambda: from_bls(2)), ("BLS v1", lambda: from_bls(1)), ("FRED", from_fred)):
        try:
            series, as_of = fn()
        except Exception as e:  # network or API error: try the next source
            errors.append(f"{name}: {e}")
            continue
        missing = [s for s in SERIES if s not in series]
        if missing:
            errors.append(f"{name}: missing {missing}")
            continue
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"asOf": as_of, "source": f"BLS PPI via {name}", "series": series}, f, indent=2)
        print(f"Wrote {path} ({name}, as of {as_of})")
        return 0
    print("Could not update the price index:\n  " + "\n  ".join(errors), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "price_index.json"))
