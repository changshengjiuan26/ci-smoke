#!/usr/bin/env python3
"""single-service diagnostic: prints rc, stdout, stderr for each name."""
import ctypes
import subprocess
import sys

LIB = "/usr/lib/libxpc.dylib"
NAMES = ["__none__", "com.apple.system.logger", "com.apple.cfprefsd.daemon"]


def probe(name):
    x = ctypes.CDLL(LIB)
    x.xpc_connection_create_mach_service.restype = ctypes.c_void_p
    x.xpc_connection_create_mach_service.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                                                     ctypes.c_uint64]
    x.xpc_dictionary_create.restype = ctypes.c_void_p
    x.xpc_dictionary_create.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64]
    x.xpc_connection_resume.argtypes = [ctypes.c_void_p]
    x.xpc_connection_resume.restype = None
    x.xpc_connection_send_message_with_reply_sync.restype = ctypes.c_void_p
    x.xpc_connection_send_message_with_reply_sync.argtypes = [ctypes.c_void_p,
                                                              ctypes.c_void_p]
    x.xpc_get_type.restype = ctypes.c_void_p
    x.xpc_get_type.argtypes = [ctypes.c_void_p]
    x.xpc_copy_description.restype = ctypes.c_char_p
    x.xpc_copy_description.argtypes = [ctypes.c_void_p]
    print("step0 lib", flush=True)
    c = x.xpc_connection_create_mach_service(name.encode(), None, 0)
    print("conn", hex(c or 0), flush=True)
    x.xpc_connection_resume(c)
    print("resumed", flush=True)
    m = x.xpc_dictionary_create(None, None, 0)
    print("msg", hex(m or 0), flush=True)
    r = x.xpc_connection_send_message_with_reply_sync(c, m)
    print("rep", hex(r or 0), flush=True)
    t = x.xpc_get_type(r)
    print("type", hex(t or 0), flush=True)
    d = x.xpc_copy_description(r)
    print("desc", (d or b"<null>")[:120], flush=True)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "one":
        probe(sys.argv[2])
        sys.exit(0)
    for n in NAMES:
        try:
            p = subprocess.run([sys.executable, __file__, "one", n],
                               capture_output=True, text=True, timeout=8)
            out = (p.stdout or "").replace(chr(10), " ; ")[:300]
            err = (p.stderr or "").replace(chr(10), " ; ")[:200]
            print("NAME=%s rc=%s OUT=[%s] ERR=[%s]" % (n, p.returncode, out, err), flush=True)
        except subprocess.TimeoutExpired:
            print("NAME=%s TIMEOUT" % n, flush=True)
