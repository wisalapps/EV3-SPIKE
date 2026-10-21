#!/usr/bin/env python3
"""Builds a minimal WebView APK (no Android SDK needed): hand-written DEX + binary manifest."""
import struct, zlib, hashlib, zipfile, sys, os

PKG = "com.ev3sim.app"
CLS = "Lcom/ev3sim/app/MainActivity;"
URL = "file:///android_asset/index.html"

# ---------------------------------------------------------------- DEX
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dexgen import build_dex
def align(b, n=4):
    while len(b) % n: b.append(0)
dex = bytearray(build_dex())

# ---------------------------------------------------------------- binary AndroidManifest.xml
NS = "http://schemas.android.com/apk/res/android"
A = {"theme": 0x01010000, "label": 0x01010001, "name": 0x01010003, "exported": 0x01010010,
     "configChanges": 0x0101001f, "screenOrientation": 0x0101001e, "minSdkVersion": 0x0101020c,
     "versionCode": 0x0101021b, "versionName": 0x0101021c, "targetSdkVersion": 0x01010270, "hardwareAccelerated": 0x010102d3}
T_REF, T_STR, T_DEC, T_HEX, T_BOOL = 0x01, 0x03, 0x10, 0x11, 0x12
LABEL = "محاكي EV3"
tree = ("manifest", [(None, "package", T_STR, PKG), ("a", "versionCode", T_DEC, 5), ("a", "versionName", T_STR, "1.4")], [
    ("uses-sdk", [("a", "minSdkVersion", T_DEC, 21), ("a", "targetSdkVersion", T_DEC, 29)], []),
    ("uses-permission", [("a", "name", T_STR, "android.permission.INTERNET")], []),
    ("application", [("a", "label", T_STR, LABEL), ("a", "theme", T_REF, 0x01030007), ("a", "hardwareAccelerated", T_BOOL, True)], [
        ("activity", [("a", "name", T_STR, PKG + ".MainActivity"), ("a", "exported", T_BOOL, True),
                      ("a", "configChanges", T_HEX, 0x0df0), ("a", "screenOrientation", T_DEC, 10)], [
            ("intent-filter", [], [
                ("action", [("a", "name", T_STR, "android.intent.action.MAIN")], []),
                ("category", [("a", "name", T_STR, "android.intent.category.LAUNCHER")], [])])])])])
attr_names = sorted(A, key=lambda k: A[k])
pool = list(attr_names)
def addp(s):
    if s not in pool: pool.append(s)
def walk(n):
    tag, attrs, kids = n; addp(tag)
    for ns, k, t, v in attrs:
        addp(k)
        if t == T_STR: addp(v)
    for c in kids: walk(c)
for s in ["android", NS]: addp(s)
walk(tree)
P = {s: i for i, s in enumerate(pool)}
def strpool(strs):
    offs, blob = [], bytearray()
    for s in strs:
        offs.append(len(blob)); u = s.encode("utf-16-le")
        blob += struct.pack("<H", len(u) // 2) + u + b"\x00\x00"
    align(blob)
    start = 28 + 4 * len(strs)
    chunk = struct.pack("<HHIIIIII", 0x0001, 28, start + len(blob), len(strs), 0, 0, start, 0)
    return chunk + b"".join(struct.pack("<I", o) for o in offs) + bytes(blob)
resmap = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(attr_names)) + b"".join(struct.pack("<I", A[k]) for k in attr_names)
NONE = 0xffffffff
nodes = bytearray(); line = [1]
def el(n):
    tag, attrs, kids = n
    attrs = sorted(attrs, key=lambda a: A.get(a[1], 0) if a[0] else -1)
    ab = bytearray()
    for ns, k, t, v in attrs:
        if t == T_STR: raw, data_ = P[v], P[v]
        elif t == T_BOOL: raw, data_ = NONE, 0xffffffff if v else 0
        else: raw, data_ = NONE, v
        ab += struct.pack("<IIIHBBI", P[NS] if ns else NONE, P[k], raw, 8, 0, t, data_)
    nodes.extend(struct.pack("<HHIII", 0x0102, 16, 36 + len(ab), line[0], NONE) +
                 struct.pack("<IIHHHHHH", NONE, P[tag], 0x14, 0x14, len(attrs), 0, 0, 0) + ab)
    line[0] += 1
    for c in kids: el(c)
    nodes.extend(struct.pack("<HHIIIII", 0x0103, 16, 24, line[0], NONE, NONE, P[tag])); line[0] += 1
nodes += struct.pack("<HHIIIII", 0x0100, 16, 24, 1, NONE, P["android"], P[NS])
el(tree)
nodes += struct.pack("<HHIIIII", 0x0101, 16, 24, line[0], NONE, P["android"], P[NS])
inner = strpool(pool) + resmap + bytes(nodes)
axml = struct.pack("<HHI", 0x0003, 8, 8 + len(inner)) + inner

# ---------------------------------------------------------------- package
out = sys.argv[2] if len(sys.argv) > 2 else "unsigned.apk"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("AndroidManifest.xml", axml)
    z.writestr("classes.dex", bytes(dex))
    z.write(sys.argv[1], "assets/index.html")
open("classes.dex", "wb").write(dex); open("AndroidManifest.bin", "wb").write(axml)
print("dex", len(dex), "bytes; manifest", len(axml), "bytes ->", out)
