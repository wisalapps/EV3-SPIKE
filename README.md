<div dir="rtl">

<img src="docs/icon.png" width="96" align="left" alt="">

# محاكي EV3

محاكي ثلاثي الأبعاد لروبوتات LEGO MINDSTORMS EV3 وSPIKE Prime، للتدريب على مسابقات الروبوت قبل التجربة على الروبوت الحقيقي. يعمل في المتصفح وعلى أندرويد وWindows، وبدون إنترنت.

![العرض ثلاثي الأبعاد](docs/screenshot-3d.png)

## التحميل

| النظام | الملف | ملاحظات |
|---|---|---|
| أندرويد | [`EV3-Simulator.apk`](release/EV3-Simulator.apk) | فعّل التثبيت من «مصادر غير معروفة». يدعم يد PlayStation وXbox عبر البلوتوث. |
| Windows 10 / 11 | [`EV3-Simulator.exe`](release/EV3-Simulator.exe) | بدون تثبيت. عند تحذير SmartScreen اضغط «معلومات إضافية» ثم «تشغيل على أي حال». |
| أي متصفح | [`index.html`](index.html) | ملف واحد. يفضّل Chrome أو Edge أو Safari. |

بعد تفعيل GitHub Pages يصبح المحاكي متاحاً على الرابط: `https://<اسم-المستخدم>.github.io/ev3-simulator/`

## المميزات

- **12 روبوتاً:** قاعدة القيادة، حامل المكعبات، الرافعة الشوكية، الجرّافة، السومو، TRACK3R، متتبع الخط، جايرو بوي، روبوت الفريق، و3 روبوتات SPIKE Prime.
- **7 حلبات بمقاسات حقيقية بالملم:** التوازن البيئي 2026 (2400 × 1200 مم)، ساحة التدريب، تتبع الخط، نقل المكعبات، المتاهة، سباق العوائق، السومو.
- **مستشعرات تقرأ مثل الحقيقية:** اللون والضوء المنعكس، فوق صوتي، جايرو، لمس، ودرجات المحركات، وتظهر كلها في شريط المنافذ.
- **البرمجة بالكتل** بصيغة SPIKE أو EV3 Classroom، مع تتبّع الخط حتى التقاطع والاستدارة بالجايرو.
- **البرمجة ببايثون** بصيغة Pybricks (`DriveBase`، `Motor`، `ColorSensor` …) بحد أقصى 5000 كلمة.
- **التحكم:** لوحة المفاتيح، أزرار لمس قابلة للتخصيص، ويد PlayStation أو Xbox مع تخصيص الأزرار. الاتجاه يكون بالنسبة للشاشة أو للروبوت.
- **5 كاميرات 3D:** ثابتة، مطاردة، أمامية، حرة، علوية، مع عرض ثنائي من الأعلى.
- **إنشاء روبوتات وحلبات بالوصف.**
- **مساعد أعطال** لروبوتك الحقيقي أو للمحاكي.

<p align="center"><img src="docs/screenshot-2d.png" width="58%" alt="حلبة التوازن البيئي 2026"> <img src="docs/screenshot-blocks.png" width="22%" alt="البرمجة بالكتل"></p>

## مثال بايثون

```python
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor
from pybricks.parameters import Port
from pybricks.robotics import DriveBase

left = Motor(Port.B)
right = Motor(Port.C)
claw = Motor(Port.A)
robot = DriveBase(left, right, wheel_diameter=56, axle_track=112)

claw.run_angle(300, -90)
robot.straight(355)
robot.turn(-90)
robot.straight(346)
claw.run_until_stalled(300)
```

الكود نفسه يعمل على روبوت EV3 الحقيقي بعد تثبيت Pybricks عليه.

## هيكل المشروع

```
src/ev3-sim.html        الكود المصدري الكامل للمحاكي (HTML + CSS + JavaScript)
vendor/three.min.js     مكتبة three.js r128 للعرض ثلاثي الأبعاد (رخصة MIT)
android/                بناء APK بدون Android SDK (DEX مكتوب يدوياً + جسر يد التحكم)
windows/                تطبيق Windows بلغة Go يعرض المحاكي في نافذة تطبيق
tools/build.py          يبني كل النسخ من الكود المصدري
release/                التطبيقات الجاهزة
index.html              نسخة GitHub Pages (تُبنى تلقائياً)
```

## البناء من الكود المصدري

المتطلبات: Python 3، وJava (لتوقيع APK)، وGo 1.21 أو أحدث (لملف exe).

```bash
python3 tools/build.py html   # index.html و dist/ev3-simulator.html
python3 tools/build.py apk    # dist/EV3-Simulator.apk
python3 tools/build.py exe    # dist/EV3-Simulator.exe
python3 tools/build.py all
```

لتوقيع APK بمفتاحك الخاص:

```bash
EV3_KEYSTORE=~/keys/ev3.keystore EV3_KEYSTORE_PASS=كلمة-سرك python3 tools/build.py apk
```

> ⚠️ احتفظ بملف المفتاح خارج المستودع. بدونه لن تستطيع إصدار تحديثات تُثبّت فوق النسخة القديمة.

## الرخصة

مكتبة three.js مرخّصة بـ MIT (انظر `vendor/three.LICENSE`). LEGO وMINDSTORMS وSPIKE علامات تجارية لمجموعة LEGO، وهذا المشروع غير تابع لها.

</div>
