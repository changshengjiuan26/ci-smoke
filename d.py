#!/usr/bin/env python3
"""single-service diagnostic: stage markers, rc and stderr for each name."""
import ctypes
import subprocess
import sys

LIB = "/usr/lib/libxpc.dylib"
NAMES = ["__none__", "com.apple.system.logger", "com.apple.cfprefsd.daemon"]

SIGS = [
    ("xpc_connection_create_mach_service", [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint64]),
    ("xpc_dictionary_create", [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64]),
    ("xpc_connection_resume", [ctypes.c_void_p]),
    ("xpc_connection_send_message_with_reply_sync", [ctypes.c_void_p, ctypes.c_void_p]),
    ("xpc_get_type", [ctypes.c_void_p]),
    ("xpc_copy_description", [ctypes.c_void_p]),
]


def load():
    x = ctypes.CDLL(LIB)
    missing = []
    for name, args in SIGS:
        try:
            fn = getattr(x, name)
            fn.argtypes = args
            if name != "xpc_connection_resume":
                fn.restype = ctypes.c_void_p
        except Exception as ex:
            missing.append("%s:%s" % (name, type(ex).__name__))
    return x, missing


def probe(name):
    print("stage=load", flush=True)
    x, missing = load()
    print("missing=%s" % (",".join(missing) or "-"), flush=True)
    print("stage=create", flush=True)
    c = x.xpc_connection_create_mach_service(name.encode(), None, 0)
    print("conn=%s" % hex(c or 0), flush=True)
    x.xpc_connection_resume(c)
    print("stage=msg", flush=True)
    m = x.xpc_dictionary_create(None, None, 0)
    print("msg=%s" % hex(m or 0), flush=True)
    print("stage=send", flush=True)
    r = x.xpc_connection_send_message_with_reply_sync(c, m)
    print("rep=%s" % hex(r or 0), flush=True)
    t = x.xpc_get_type(r)
    print("type=%s" % hex(t or 0), flush=True)
    d = x.xpc_copy_description(r)
    print("desc=%r" % ((d or b"<null>")[:120],), flush=True)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "one":
        probe(sys.argv[2])
        sys.exit(0)
    for n in NAMES:
        try:
            p = subprocess.run([sys.executable, __file__, "one", n],
                               capture_output=True, text=True, timeout=10)
            out = (p.stdout or "").replace(chr(10), " ; ")[:400]
            err = (p.stderr or "").replace(chr(10), " ; ")[:900]
            print("NAME=%s rc=%s OUT=[%s] ERR=[%s]" % (n, p.returncode, out, err), flush=True)
        except subprocess.TimeoutExpired:
            print("NAME=%s TIMEOUT" % n, flush=True)
