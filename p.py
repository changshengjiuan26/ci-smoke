#!/usr/bin/env python3
"""service reachability sampler.

Collects Mach service names from the system job definitions, sends one empty
dictionary to each, and records the reply object type.  Prints aggregate
counts only; the per-service table goes to /tmp/o.json.
"""
import ctypes, json, os, plistlib, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

LIB = "/usr/lib/libxpc.dylib"
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


def one(name):
    x = ctypes.CDLL(LIB)
    x.xpc_connection_create_mach_service.restype = ctypes.c_void_p
    x.xpc_connection_create_mach_service.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint64]
    x.xpc_dictionary_create.restype = ctypes.c_void_p
    x.xpc_dictionary_create.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64]
    x.xpc_connection_resume.argtypes = [ctypes.c_void_p]
    x.xpc_connection_send_message_with_reply_sync.restype = ctypes.c_void_p
    x.xpc_connection_send_message_with_reply_sync.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    x.xpc_get_type.restype = ctypes.c_void_p
    x.xpc_get_type.argtypes = [ctypes.c_void_p]
    c = x.xpc_connection_create_mach_service(name.encode(), None, 0)
    if not c:
        print("noc")
        return 1
    x.xpc_connection_resume(c)
    m = x.xpc_dictionary_create(None, None, 0)
    if not m:
        print("nom")
        return 1
    r = x.xpc_connection_send_message_with_reply_sync(c, m)
    if not r:
        print("nor")
        return 1
    t = x.xpc_get_type(r)
    def sym(n):
        for cand in (n, n.lstrip("_")):
            try:
                return ctypes.c_void_p.in_dll(x, cand).value
            except Exception:
                pass
        return object()
    if t == sym("_xpc_type_dictionary"):
        print("d")
    elif t == sym("_xpc_type_error"):
        print("e")
    else:
        print("o")
    return 0


def main():
    ns = names()
    print("n=%d" % len(ns))

    def run(n):
        try:
            p = subprocess.run([sys.executable, __file__, "one", n],
                               capture_output=True, text=True, timeout=6)
            return (n, (p.stdout or "").strip()[:4] or "x")
        except subprocess.TimeoutExpired:
            return (n, "t")
        except Exception:
            return (n, "x")

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, ns))

    tally = {}
    for _, v in res:
        tally[v] = tally.get(v, 0) + 1
    with open("/tmp/o.json", "w") as fh:
        json.dump(res, fh)
    print("tally", json.dumps(tally))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "one":
        sys.exit(one(sys.argv[2]))
    main()
