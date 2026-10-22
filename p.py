#!/usr/bin/env python3
"""helpers for the service sampler: emit names, or tally a result file."""
import json
import os
import plistlib
import sys

DIRS = ["/System/Library/LaunchDaemons", "/Library/LaunchDaemons"]


def names():
    out = []
    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if not n.endswith(".plist"):
                continue
            try:
                with open(os.path.join(d, n), "rb") as fh:
                    pl = plistlib.load(fh)
            except Exception:
                continue
            ms = pl.get("MachServices") or {}
            if not isinstance(ms, dict):
                continue
            if pl.get("UserName", "root") not in ("root", "0"):
                continue
            for s in ms:
                if s not in out:
                    out.append(s)
    return out


def tally(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            name, _, desc = line.partition("\t")
            rows.append({"s": name, "d": desc[:160]})
    buckets = {}
    for r in rows:
        d = r["d"]
        if d.startswith("<"):
            k = d
        elif "Connection invalid" in d:
            k = "invalid"
        elif "XPC_TYPE_ERROR" in d or "Error:" in d:
            k = "error-other"
        else:
            k = "answered"
        buckets[k] = buckets.get(k, 0) + 1
    with open("/tmp/o.json", "w") as fh:
        json.dump(rows, fh)
    print("total=%d" % len(rows), json.dumps(buckets, ensure_ascii=False))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "names":
        for s in names():
            print(s)
    elif mode == "tally":
        tally(sys.argv[2] if len(sys.argv) > 2 else "/tmp/o.txt")
    else:
        print("modes: names | tally <file>")
