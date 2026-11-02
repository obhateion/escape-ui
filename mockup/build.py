"""Assemble the mock-up page: src/page.html + the device data + the JS sources -> escape-ui.html."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
import sys
# --demo OUT.html: the public demo (made-up and free games, no scraped pictures) instead of the Brick's data
DEMO = sys.argv[sys.argv.index("--demo") + 1] if "--demo" in sys.argv else None
dev = json.load(open(os.path.join(HERE, "demo.json" if DEMO else "device.json"), encoding="utf-8"))
covers = {} if DEMO else json.load(open(os.path.join(HERE, "covers.json"), encoding="utf-8"))   # the Brick's own scraped images, 260 px
web = os.path.join(HERE, "covers-web.json")   # found online for games the Brick has no picture of (not in git)
if os.path.exists(web) and not DEMO:
    for k, v in json.load(open(web, encoding="utf-8")).items():
        covers.setdefault(k, v)
js = "const DEVICE = " + json.dumps(dev, ensure_ascii=False) + ";\nconst ORIGINAL = " + json.dumps(covers) + ";\n"
for f in ("pyrandom.js", "shapes.js", "art.js", "main.js"):
    js += "\n" + open(os.path.join(SRC, f), encoding="utf-8").read()
page = open(os.path.join(SRC, "page.html"), encoding="utf-8").read().replace("/*JS*/", js)
if DEMO:   # the public page: English intro, demo data, a link back to the project
    import re
    page = re.sub(r"<p>Макет 1:1.*?</p>", "<p>Try the theme without a console: this page draws every picture with the same code as the "
                  "generator on the Brick (same random numbers), at the sizes of theme.xml. The games are made-up or free ones. "
                  "Keys: arrows, Enter = A, Backspace = B, M = START. Turn CHARGING on and wait 15 s for the charging screen. "
                  "APPS → EscapeUI opens the settings app. "
                  "<a href=\"https://github.com/obhateion/escape-ui\">Project, install, guide →</a></p>", page, count=1, flags=re.S)
    page = page.replace("<title>escape UI</title>", "<title>escape/UI demo</title>")
out = DEMO or os.path.join(HERE, "escape-ui.html")
open(out, "w", encoding="utf-8", newline="\n").write(page)
print(out, len(page), "bytes")
