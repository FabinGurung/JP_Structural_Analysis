"""Independent-solver adapter status registry.

These entries declare integration boundaries only. They do not claim that an
adapter is implemented or validated.
"""
ADAPTERS = {
    "pynite": {"status":"NOT_IMPLEMENTED","role":"elastic 3D benchmark","integration":"optional Python API"},
    "frame3dd": {"status":"NOT_IMPLEMENTED","role":"frame static/modal benchmark","integration":"CLI/data exchange"},
    "xc": {"status":"NOT_IMPLEMENTED","role":"civil FE comparison","integration":"external/API"},
    "calculix": {"status":"NOT_IMPLEMENTED","role":"shell/solid local benchmark","integration":"input deck/CLI"},
}
