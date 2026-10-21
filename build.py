#!/usr/bin/env python3
"""يبني كل نسخ المحاكي من الكود المصدري:
   dist/ev3-simulator.html  — ملف واحد يعمل بدون إنترنت (three.js مدمج)
   dist/EV3-Simulator.apk   — تطبيق أندرويد (يحتاج Java: keytool + jarsigner)
   dist/EV3-Simulator.exe   — تطبيق Windows (يحتاج Go 1.21+)
   index.html               — نسخة GitHub Pages

الاستخدام:  python3 tools/build.py [html|apk|exe|all]
"""
import os, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
CDN_TAG = '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js" crossorigin="anonymous"></script>'
HEAD = ('<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="theme-color" content="#13171c"></head><body>')

def p(*a): return os.path.join(ROOT, *a)

def build_html():
    src = open(p("src", "ev3-sim.html"), encoding="utf-8").read()
    three = open(p("vendor", "three.min.js"), encoding="utf-8").read()
    if CDN_TAG not in src:
        sys.exit("لم أجد وسم three.js في src/ev3-sim.html")
    page = HEAD + src.replace(CDN_TAG, "<script>/* three.js r128 — MIT License — https://threejs.org */\n" + three + "\n</script>") + "</body></html>"
    os.makedirs(DIST, exist_ok=True)
    for out in (os.path.join(DIST, "ev3-simulator.html"), p("index.html")):
        open(out, "w", encoding="utf-8").write(page)
    print("✓ dist/ev3-simulator.html و index.html")

def build_apk():
    html = os.path.join(DIST, "ev3-simulator.html")
    if not os.path.exists(html): build_html()
    ks = os.environ.get("EV3_KEYSTORE", p("android", "release.keystore"))
    pw = os.environ.get("EV3_KEYSTORE_PASS", "change-me")
    if not os.path.exists(ks):
        print("… إنشاء مفتاح توقيع جديد في", ks, "(لا ترفعه إلى GitHub)")
        subprocess.check_call(["keytool", "-genkeypair", "-keystore", ks, "-storepass", pw, "-keypass", pw, "-alias", "ev3",
                               "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-dname", "CN=EV3 Simulator, C=OM"])
    unsigned = os.path.join(DIST, "unsigned.apk"); out = os.path.join(DIST, "EV3-Simulator.apk")
    subprocess.check_call([sys.executable, p("android", "build_apk.py"), html, unsigned], cwd=DIST)
    shutil.copy(unsigned, out)
    subprocess.check_call(["jarsigner", "-keystore", ks, "-storepass", pw, "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256", out, "ev3"])
    for f in ("unsigned.apk", "classes.dex", "AndroidManifest.bin"):
        try: os.remove(os.path.join(DIST, f))
        except OSError: pass
    print("✓ dist/EV3-Simulator.apk")

def build_exe():
    html = os.path.join(DIST, "ev3-simulator.html")
    if not os.path.exists(html): build_html()
    w = p("windows")
    shutil.copy(html, os.path.join(w, "index.html"))
    subprocess.check_call([sys.executable, "mkres.py"], cwd=w)
    env = dict(os.environ, GOOS="windows", GOARCH="amd64", CGO_ENABLED="0")
    subprocess.check_call(["go", "build", "-trimpath", "-ldflags", "-s -w -H=windowsgui", "-o", os.path.join(DIST, "EV3-Simulator.exe"), "."], cwd=w, env=env)
    print("✓ dist/EV3-Simulator.exe")

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"html": [build_html], "apk": [build_apk], "exe": [build_exe], "all": [build_html, build_apk, build_exe]}
    if what not in steps: sys.exit("الخيارات: html | apk | exe | all")
    for step in steps[what]: step()
