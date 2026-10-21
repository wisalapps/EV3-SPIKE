"""Draws the app icon and writes rsrc_windows_amd64.syso (COFF .rsrc with RT_ICON + RT_GROUP_ICON + manifest)."""
import struct, io
from PIL import Image, ImageDraw

def icon_png(size):
    s = size / 256
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    R = lambda *v: [round(x * s) for x in v]
    d.rounded_rectangle(R(8, 8, 248, 248), radius=round(52 * s), fill=(19, 23, 28, 255))
    d.rounded_rectangle(R(44, 30, 212, 226), radius=round(26 * s), fill=(213, 216, 219, 255), outline=(149, 155, 161, 255), width=max(1, round(5 * s)))
    d.rounded_rectangle(R(66, 52, 190, 124), radius=round(8 * s), fill=(196, 203, 189, 255), outline=(85, 89, 94, 255), width=max(1, round(4 * s)))
    d.rectangle(R(78, 66, 136, 74), fill=(59, 64, 56, 255)); d.rectangle(R(78, 84, 118, 90), fill=(59, 64, 56, 255))
    d.rounded_rectangle(R(92, 146, 164, 212), radius=round(14 * s), fill=(61, 220, 132, 255))
    d.rounded_rectangle(R(100, 154, 156, 204), radius=round(10 * s), fill=(141, 148, 155, 255))
    d.rounded_rectangle(R(116, 168, 140, 190), radius=round(5 * s), fill=(76, 81, 87, 255))
    d.rounded_rectangle(R(150, 228, 238, 248), radius=round(6 * s), fill=(243, 178, 48, 255))
    return im

sizes = [256, 64, 48, 32, 16]
imgs = []
for z in sizes:
    b = io.BytesIO(); icon_png(z).save(b, "PNG"); imgs.append(b.getvalue())
icon_png(256).save("icon.png")

MANIFEST = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="1.4.0.0" name="EV3Simulator" type="win32"/>
  <description>EV3 Simulator</description>
  <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>
    <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
  </windowsSettings></application>
</assembly>'''

# resources: (type, id, data)
res = [(3, i + 1, imgs[i]) for i in range(len(imgs))]
grp = struct.pack("<HHH", 0, 1, len(imgs))
for i, z in enumerate(sizes):
    grp += struct.pack("<BBBBHHIH", 0 if z == 256 else z, 0 if z == 256 else z, 0, 0, 1, 32, len(imgs[i]), i + 1)
res.append((14, 1, grp))
res.append((24, 1, MANIFEST))

types = sorted({t for t, _, _ in res})
# layout: root dir, type dirs, name dirs (one per resource), data entries, data
def dirhdr(n): return struct.pack("<IIHHHH", 0, 0, 0, 0, 0, n)
root_size = 16 + 8 * len(types)
type_dirs = {t: sorted([r for r in res if r[0] == t], key=lambda r: r[1]) for t in types}
off = root_size
type_off = {}
for t in types: type_off[t] = off; off += 16 + 8 * len(type_dirs[t])
name_off = {}
for t in types:
    for r in type_dirs[t]: name_off[(t, r[1])] = off; off += 16 + 8
entry_off = {}
for t in types:
    for r in type_dirs[t]: entry_off[(t, r[1])] = off; off += 16
data_off = {}
for t in types:
    for r in type_dirs[t]:
        off = (off + 7) & ~7; data_off[(t, r[1])] = off; off += len(r[2])
buf = bytearray(off)
def put(o, b): buf[o:o + len(b)] = b
put(0, dirhdr(len(types)) + b"".join(struct.pack("<II", t, 0x80000000 | type_off[t]) for t in types))
relocs = []
for t in types:
    put(type_off[t], dirhdr(len(type_dirs[t])) + b"".join(struct.pack("<II", r[1], 0x80000000 | name_off[(t, r[1])]) for r in type_dirs[t]))
    for r in type_dirs[t]:
        k = (t, r[1])
        put(name_off[k], dirhdr(1) + struct.pack("<II", 0x0409, entry_off[k]))
        put(entry_off[k], struct.pack("<IIII", data_off[k], len(r[2]), 0, 0))
        relocs.append(entry_off[k])
        put(data_off[k], r[2])
raw = bytes(buf)
while len(raw) % 4: raw += b"\0"
HDR, SEC = 20, 40
p_raw = HDR + SEC; p_rel = p_raw + len(raw); p_sym = p_rel + 10 * len(relocs)
coff = struct.pack("<HHIIIHH", 0x8664, 1, 0, p_sym, 1, 0, 0)
coff += struct.pack("<8sIIIIIIHHI", b".rsrc\0\0\0", 0, 0, len(raw), p_raw, p_rel, 0, len(relocs), 0, 0x40000040)
coff += raw
for r in relocs: coff += struct.pack("<IIH", r, 0, 3)   # IMAGE_REL_AMD64_ADDR32NB against symbol 0
coff += struct.pack("<8sIhHBB", b".rsrc\0\0\0", 0, 1, 0, 3, 0)
coff += struct.pack("<I", 4)
open("rsrc_windows_amd64.syso", "wb").write(coff)
print("syso", len(coff), "bytes, icons", sizes)
