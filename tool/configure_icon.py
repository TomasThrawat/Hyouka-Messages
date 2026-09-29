from pathlib import Path

ROOT = Path("android")
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
DRAWABLE = ROOT / "app/src/main/res/drawable"
ICON = DRAWABLE / "messages_icon.xml"

DRAWABLE.mkdir(parents=True, exist_ok=True)

ICON.write_text(
r'''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="1536"
    android:viewportHeight="1458">
    <path
        android:fillColor="#FF000000"
        android:pathData="M0,0 L1536,0 L1536,1458 L0,1458 Z" />
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M1128,519 L1066,457 L1005,417 L912,379 L812,361 L705,363 L624,379 L551,407 L477,452 L431,493 L387,550 L361,605 L349,652 L349,741 L367,803 L405,869 L474,939 L476,994 L461,1034 L426,1070 L388,1087 L387,1098 L430,1110 L516,1100 L586,1070 L652,1021 L742,1033 L884,1021 L974,991 L1058,942 L1140,857 L1172,797 L1188,737 L1191,686 L1182,627 L1166,581 Z" />
</vector>
''',
encoding="utf-8"
)

text = MANIFEST.read_text(encoding="utf-8")
if 'android:icon="@drawable/messages_icon"' not in text:
    text = text.replace(
        '<application',
        '<application android:icon="@drawable/messages_icon" android:roundIcon="@drawable/messages_icon"',
        1
    )
MANIFEST.write_text(text, encoding="utf-8")
