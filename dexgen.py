"""Hand-assembled DEX for the EV3 simulator shell.

Java equivalent:
public class MainActivity extends Activity {
  WebView w;
  protected void onCreate(Bundle b) { super.onCreate(b); WebView v = new WebView(this); w = v;
    WebSettings s = v.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true);
    s.setMediaPlaybackRequiresUserGesture(false); v.loadUrl(URL); setContentView(v); }
  public boolean dispatchKeyEvent(KeyEvent e) {           // gamepad buttons -> JS
    int src = e.getSource();
    if ((src & SOURCE_GAMEPAD) == SOURCE_GAMEPAD || (src & SOURCE_JOYSTICK) == SOURCE_JOYSTICK) {
      w.evaluateJavascript("window.__nk&&__nk(" + e.getKeyCode() + "," + e.getAction() + ")", null); return true; }
    return super.dispatchKeyEvent(e); }
  public boolean dispatchGenericMotionEvent(MotionEvent e) { // sticks / triggers / hat -> JS
    if ((e.getSource() & SOURCE_JOYSTICK) == SOURCE_JOYSTICK && e.getAction() == ACTION_MOVE) {
      w.evaluateJavascript("window.__np&&__np(" + axes... + "0)", null); return true; }
    return super.dispatchGenericMotionEvent(e); }
}
"""
import struct, zlib, hashlib

URL = "file:///android_asset/index.html"
CLS = "Lcom/ev3sim/app/MainActivity;"
ACT, BUNDLE, CTX, VIEW, WS, WV, STR = ("Landroid/app/Activity;", "Landroid/os/Bundle;", "Landroid/content/Context;",
    "Landroid/view/View;", "Landroid/webkit/WebSettings;", "Landroid/webkit/WebView;", "Ljava/lang/String;")
KEV, MEV, SB, VCB = "Landroid/view/KeyEvent;", "Landroid/view/MotionEvent;", "Ljava/lang/StringBuilder;", "Landroid/webkit/ValueCallback;"
# axis ids: X Y Z RZ LTRIGGER RTRIGGER HAT_X HAT_Y GAS BRAKE RX RY
AXES = [0, 1, 11, 14, 17, 18, 15, 16, 22, 23, 12, 13]
SRC_GAMEPAD, SRC_JOYSTICK = 0x401, 0x1000010

def uleb(n):
    out = bytearray()
    while True:
        b = n & 0x7f; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)

def shorty(t): return t if len(t) == 1 else "L"
def proto(ret, *params): return ("".join([shorty(ret)] + [shorty(p) for p in params]), ret, tuple(params))

METHODS = {  # key -> (class, name, proto)
 "act_init": (ACT, "<init>", proto("V")), "act_onCreate": (ACT, "onCreate", proto("V", BUNDLE)),
 "act_setContentView": (ACT, "setContentView", proto("V", VIEW)),
 "act_dke": (ACT, "dispatchKeyEvent", proto("Z", KEV)), "act_dgme": (ACT, "dispatchGenericMotionEvent", proto("Z", MEV)),
 "my_init": (CLS, "<init>", proto("V")), "my_onCreate": (CLS, "onCreate", proto("V", BUNDLE)),
 "my_dke": (CLS, "dispatchKeyEvent", proto("Z", KEV)), "my_dgme": (CLS, "dispatchGenericMotionEvent", proto("Z", MEV)),
 "ws_js": (WS, "setJavaScriptEnabled", proto("V", "Z")), "ws_dom": (WS, "setDomStorageEnabled", proto("V", "Z")),
 "ws_media": (WS, "setMediaPlaybackRequiresUserGesture", proto("V", "Z")),
 "wv_init": (WV, "<init>", proto("V", CTX)), "wv_settings": (WV, "getSettings", proto(WS)),
 "wv_load": (WV, "loadUrl", proto("V", STR)), "wv_eval": (WV, "evaluateJavascript", proto("V", STR, VCB)),
 "ke_src": (KEV, "getSource", proto("I")), "ke_code": (KEV, "getKeyCode", proto("I")), "ke_act": (KEV, "getAction", proto("I")),
 "me_src": (MEV, "getSource", proto("I")), "me_act": (MEV, "getAction", proto("I")), "me_axis": (MEV, "getAxisValue", proto("F", "I")),
 "sb_init": (SB, "<init>", proto("V", STR)), "sb_appI": (SB, "append", proto(SB, "I")), "sb_appF": (SB, "append", proto(SB, "F")),
 "sb_appS": (SB, "append", proto(SB, STR)), "sb_str": (SB, "toString", proto(STR)),
}
FIELD = (CLS, WV, "w")
CONST_STRS = [URL, "window.__nk&&__nk(", "window.__np&&__np(", ",", ")", "0)"]

class Asm:
    def __init__(s): s.u = []; s.labels = {}; s.fix = []
    def raw(s, *units): s.u.extend(units)
    def label(s, n): s.labels[n] = len(s.u)
    def op(s, op, a=0): s.u.append((a << 8) | op)
    def inv(s, op, regs, m):  # 35c
        a = len(regs); r = list(regs) + [0] * (5 - a)
        s.u += [((a << 12) | (r[4] << 8) | op), m, (r[3] << 12) | (r[2] << 8) | (r[1] << 4) | r[0]]
    def br2(s, op, a, b, lbl):  # 22t if-eq/if-ne
        s.fix.append((len(s.u) + 1, len(s.u), lbl)); s.u += [((b << 12) | (a << 8) | op), 0]
    def brz(s, op, a, lbl):  # 21t if-eqz
        s.fix.append((len(s.u) + 1, len(s.u), lbl)); s.u += [((a << 8) | op), 0]
    def done(s):
        for at, base, l in s.fix: s.u[at] = (s.labels[l] - base) & 0xffff
        return b"".join(struct.pack("<H", x) for x in s.u)

def build_dex():
    types = {ACT, BUNDLE, CTX, VIEW, WS, WV, STR, KEV, MEV, SB, VCB, CLS, "V", "Z", "I", "F"}
    protos = {p for (_, _, p) in METHODS.values()}
    strings = set(types) | set(CONST_STRS) | {FIELD[2]}
    for sh, r, ps in protos: strings.add(sh)
    for c, n, p in METHODS.values(): strings.add(n)
    strings = sorted(strings, key=lambda x: x.encode())
    S = {x: i for i, x in enumerate(strings)}
    types = sorted(types, key=lambda t: S[t]); T = {t: i for i, t in enumerate(types)}
    protos = sorted(protos, key=lambda p: (T[p[1]], [T[x] for x in p[2]])); PI = {p: i for i, p in enumerate(protos)}
    meths = sorted(set(METHODS.values()), key=lambda m: (T[m[0]], S[m[1]], PI[m[2]])); MI = {m: i for i, m in enumerate(meths)}
    M = lambda k: MI[METHODS[k]]
    FI = 0
    # ---- code
    def c_init():
        a = Asm(); a.inv(0x70, [0], M("act_init")); a.op(0x0e); return (1, 1, 1, a.done())
    def c_onCreate():  # regs 5: v0..v2, p0=v3 p1=v4
        a = Asm(); a.inv(0x6f, [3, 4], M("act_onCreate"))
        a.op(0x22, 0); a.raw(T[WV]); a.inv(0x70, [0, 3], M("wv_init"))
        a.raw((3 << 12) | (0 << 8) | 0x5b, FI)                      # iput-object v0, p0, w
        a.inv(0x6e, [0], M("wv_settings")); a.op(0x0c, 1)
        a.raw(0x12 | (2 << 8) | (1 << 12))                          # const/4 v2, 1
        a.inv(0x6e, [1, 2], M("ws_js")); a.inv(0x6e, [1, 2], M("ws_dom"))
        a.raw(0x12 | (2 << 8) | (0 << 12)); a.inv(0x6e, [1, 2], M("ws_media"))
        a.op(0x1a, 2); a.raw(S[URL]); a.inv(0x6e, [0, 2], M("wv_load"))
        a.inv(0x6e, [3, 0], M("act_setContentView")); a.op(0x0e); return (5, 2, 2, a.done())
    def emit_js(a, p1):  # v0 = StringBuilder already holding prefix; evaluates & returns true
        a.inv(0x6e, [0], M("sb_str")); a.op(0x0c, 1)
        a.raw((p1 - 1 << 12) | (2 << 8) | 0x54, FI)                  # iget-object v2, p0, w
        a.brz(0x38, 2, "ret")
        a.raw(0x12 | (3 << 8) | (0 << 12))                          # const/4 v3, 0
        a.inv(0x6e, [2, 1, 3], M("wv_eval"))
        a.label("ret"); a.raw(0x12 | (0 << 8) | (1 << 12)); a.op(0x0f, 0)
    def c_dke():  # regs 6: v0..v3, p0=v4, p1=v5
        a = Asm(); p0, p1 = 4, 5
        a.inv(0x6e, [p1], M("ke_src")); a.op(0x0a, 0)
        a.op(0x13, 1); a.raw(SRC_GAMEPAD)                            # const/16 v1, 0x401
        a.raw(0x95 | (2 << 8), (1 << 8) | 0)                         # and-int v2, v0, v1
        a.br2(0x32, 2, 1, "gp")
        a.op(0x14, 1); a.raw(SRC_JOYSTICK & 0xffff, SRC_JOYSTICK >> 16)
        a.raw(0x95 | (2 << 8), (1 << 8) | 0)
        a.br2(0x32, 2, 1, "gp")
        a.inv(0x6f, [p0, p1], M("act_dke")); a.op(0x0a, 0); a.op(0x0f, 0)
        a.label("gp")
        a.op(0x22, 0); a.raw(T[SB]); a.op(0x1a, 1); a.raw(S["window.__nk&&__nk("]); a.inv(0x70, [0, 1], M("sb_init"))
        a.inv(0x6e, [p1], M("ke_code")); a.op(0x0a, 1); a.inv(0x6e, [0, 1], M("sb_appI"))
        a.op(0x1a, 1); a.raw(S[","]); a.inv(0x6e, [0, 1], M("sb_appS"))
        a.inv(0x6e, [p1], M("ke_act")); a.op(0x0a, 1); a.inv(0x6e, [0, 1], M("sb_appI"))
        a.op(0x1a, 1); a.raw(S[")"]); a.inv(0x6e, [0, 1], M("sb_appS"))
        emit_js(a, 5)
        return (6, 2, 3, a.done())
    def c_dgme():
        a = Asm(); p0, p1 = 4, 5
        a.inv(0x6e, [p1], M("me_src")); a.op(0x0a, 0)
        a.op(0x14, 1); a.raw(SRC_JOYSTICK & 0xffff, SRC_JOYSTICK >> 16)
        a.raw(0x95 | (2 << 8), (1 << 8) | 0)
        a.br2(0x33, 2, 1, "sup")                                     # if-ne v2, v1
        a.inv(0x6e, [p1], M("me_act")); a.op(0x0a, 0)
        a.raw(0x12 | (1 << 8) | (2 << 12))                           # const/4 v1, 2 (ACTION_MOVE)
        a.br2(0x33, 0, 1, "sup")
        a.op(0x22, 0); a.raw(T[SB]); a.op(0x1a, 1); a.raw(S["window.__np&&__np("]); a.inv(0x70, [0, 1], M("sb_init"))
        for ax in AXES:
            a.op(0x13, 1); a.raw(ax)
            a.inv(0x6e, [p1, 1], M("me_axis")); a.op(0x0a, 1); a.inv(0x6e, [0, 1], M("sb_appF"))
            a.op(0x1a, 1); a.raw(S[","]); a.inv(0x6e, [0, 1], M("sb_appS"))
        a.op(0x1a, 1); a.raw(S["0)"]); a.inv(0x6e, [0, 1], M("sb_appS"))
        emit_js(a, 5)
        a.label("sup"); a.inv(0x6f, [p0, p1], M("act_dgme")); a.op(0x0a, 0); a.op(0x0f, 0)
        return (6, 2, 3, a.done())
    codes = {"my_init": c_init(), "my_onCreate": c_onCreate(), "my_dke": c_dke(), "my_dgme": c_dgme()}
    # ---- layout
    HDR = 0x70
    n_s, n_t, n_p, n_f, n_m, n_c = len(strings), len(types), len(protos), 1, len(meths), 1
    off_s = HDR; off_t = off_s + 4 * n_s; off_p = off_t + 4 * n_t; off_f = off_p + 12 * n_p
    off_m = off_f + 8 * n_f; off_c = off_m + 8 * n_m; data_off = off_c + 32 * n_c
    data = bytearray()
    here = lambda: data_off + len(data)
    def align():
        while len(data) % 4: data.append(0)
    code_off = {}
    first_code = None
    for k, (regs, ins, outs, insns) in codes.items():
        align(); code_off[k] = here(); first_code = first_code or code_off[k]
        data.extend(struct.pack("<HHHHII", regs, ins, outs, 0, 0, len(insns) // 2) + insns)
    tl_off = {}
    for p in protos:
        if p[2] and p[2] not in tl_off:
            align(); tl_off[p[2]] = here()
            data.extend(struct.pack("<I", len(p[2])) + b"".join(struct.pack("<H", T[t]) for t in p[2]))
    align()
    sd_start = here(); str_off = []
    for x in strings:
        str_off.append(here()); data.extend(uleb(len(x)) + x.encode() + b"\x00")
    cd_off = here()
    direct = sorted(["my_init"], key=M); virt = sorted(["my_onCreate", "my_dke", "my_dgme"], key=M)
    acc = {"my_init": 0x10001, "my_onCreate": 0x4, "my_dke": 0x1, "my_dgme": 0x1}
    data.extend(uleb(0) + uleb(1) + uleb(len(direct)) + uleb(len(virt)))
    data.extend(uleb(FI) + uleb(0))                                        # instance field w
    prev = 0
    for k in direct: data.extend(uleb(M(k) - prev) + uleb(acc[k]) + uleb(code_off[k])); prev = M(k)
    prev = 0
    for k in virt: data.extend(uleb(M(k) - prev) + uleb(acc[k]) + uleb(code_off[k])); prev = M(k)
    align(); map_off = here()
    items = [(0x0000, 1, 0), (0x0001, n_s, off_s), (0x0002, n_t, off_t), (0x0003, n_p, off_p), (0x0004, n_f, off_f),
             (0x0005, n_m, off_m), (0x0006, n_c, off_c), (0x2001, len(codes), first_code), (0x1001, len(tl_off), min(tl_off.values())),
             (0x2002, n_s, sd_start), (0x2000, 1, cd_off), (0x1000, 1, map_off)]
    items.sort(key=lambda x: x[2])
    data.extend(struct.pack("<I", len(items)) + b"".join(struct.pack("<HHII", t, 0, sz, o) for t, sz, o in items))
    body = bytearray()
    for o in str_off: body += struct.pack("<I", o)
    for t in types: body += struct.pack("<I", S[t])
    for p in protos: body += struct.pack("<III", S[p[0]], T[p[1]], tl_off[p[2]] if p[2] else 0)
    body += struct.pack("<HHI", T[FIELD[0]], T[FIELD[1]], S[FIELD[2]])
    for c, n, p in meths: body += struct.pack("<HHI", T[c], PI[p], S[n])
    body += struct.pack("<IIIIIIII", T[CLS], 0x1, T[ACT], 0, 0xffffffff, 0, cd_off, 0)
    assert HDR + len(body) == data_off
    file_size = data_off + len(data)
    hdr = bytearray(b"dex\n035\x00") + bytes(24)
    hdr += struct.pack("<IIIIII", file_size, HDR, 0x12345678, 0, 0, map_off)
    for n, o in [(n_s, off_s), (n_t, off_t), (n_p, off_p), (n_f, off_f), (n_m, off_m), (n_c, off_c), (len(data), data_off)]:
        hdr += struct.pack("<II", n, o)
    assert len(hdr) == HDR
    dex = bytearray(hdr + body + data)
    dex[12:32] = hashlib.sha1(bytes(dex[32:])).digest()
    dex[8:12] = struct.pack("<I", zlib.adler32(bytes(dex[12:])) & 0xffffffff)
    return bytes(dex)
