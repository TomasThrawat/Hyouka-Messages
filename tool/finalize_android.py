from pathlib import Path
import re
import shutil

ROOT = Path("android")
OLD_PACKAGE = "com.tomasthrawat.hyouka_messages"
NEW_PACKAGE = "com.messages.chat"

old_dir = ROOT / "app/src/main/kotlin" / Path(OLD_PACKAGE.replace(".", "/"))
new_dir = ROOT / "app/src/main/kotlin" / Path(NEW_PACKAGE.replace(".", "/"))

if old_dir.exists():
    new_dir.parent.mkdir(parents=True, exist_ok=True)
    if new_dir.exists():
        shutil.rmtree(new_dir)
    shutil.move(str(old_dir), str(new_dir))

for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix in {".kt", ".java", ".xml", ".gradle", ".kts", ".properties"}:
        text = path.read_text(encoding="utf-8")
        updated = text.replace(OLD_PACKAGE, NEW_PACKAGE)
        if updated != text:
            path.write_text(updated, encoding="utf-8")

manifest = ROOT / "app/src/main/AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")

application_match = re.search(r"<application\b[^>]*>", text)
if not application_match:
    raise RuntimeError("Android application element not found")

application = application_match.group(0)
if "android:label=" in application:
    application = re.sub(
        r'android:label="[^"]*"',
        'android:label="رسائل"',
        application,
        count=1,
    )
else:
    application = application[:-1] + ' android:label="رسائل">'

text = text[:application_match.start()] + application + text[application_match.end():]
manifest.write_text(text, encoding="utf-8")

gradle_files = list((ROOT / "app").glob("build.gradle*"))
if not gradle_files:
    raise RuntimeError("Android app Gradle file not found")

gradle_text = gradle_files[0].read_text(encoding="utf-8")
if NEW_PACKAGE not in gradle_text:
    raise RuntimeError("Generated Android project does not use com.messages.chat")

main_activity = new_dir / "MainActivity.kt"
if not main_activity.exists():
    raise RuntimeError("MainActivity.kt was not moved to com.messages.chat")
