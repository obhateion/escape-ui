"""Build the PDF guides (ru, en): HTML with the theme's own fonts, printed by Edge headless.

    python docs/guide/make_guide.py OUT_DIR
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FONTS = os.path.join(ROOT, "theme", "fonts").replace("\\", "/")
IMG = os.path.join(os.path.expanduser("~"), "escape-ui-github", "docs", "img").replace("\\", "/")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CSS = """
@font-face { font-family: Doto; src: url('file:///%(f)s/Doto[ROND,wght].ttf'); font-weight: 100 900; }
@font-face { font-family: Silk; src: url('file:///%(f)s/Silkscreen-Regular.ttf'); }
@font-face { font-family: Archivo; src: url('file:///%(f)s/Archivo[wdth,wght].ttf'); font-weight: 100 900; }
@font-face { font-family: Mono; src: url('file:///%(f)s/MartianMono[wdth,wght].ttf'); font-weight: 100 900; }
@page { size: A4; margin: 16mm 16mm 18mm; }
* { box-sizing: border-box; }
body { font: 10.4pt/1.5 Archivo, sans-serif; color: #141413; margin: 0; }
h1, h2, h3 { font-weight: 800; margin: 0; }
h2 { font: 900 22pt/1 Doto, monospace; letter-spacing: .02em; margin: 0 0 4mm; padding-top: 2mm; border-top: 1.2pt solid #141413; }
h3 { font: 10pt Silk, monospace; letter-spacing: .08em; text-transform: uppercase; margin: 5mm 0 1.5mm; }
p { margin: 0 0 2.4mm; }
ul, ol { margin: 0 0 3mm; padding-left: 5mm; }
li { margin: 0 0 1.2mm; }
code, .k { font: 8.6pt Mono, monospace; background: #ecebe6; padding: .2mm 1.2mm; border-radius: 1mm; }
pre { font: 8.2pt/1.5 Mono, monospace; background: #141413; color: #f2f2ee; padding: 3mm 4mm; border-radius: 1.5mm; white-space: pre-wrap; margin: 0 0 3mm; }
.tag { font: 7.5pt Silk, monospace; letter-spacing: .1em; text-transform: uppercase; color: #6e6e6b; }
figure { margin: 2mm 0 4mm; } figure img { width: 100%; border-radius: 1.5mm; display: block; }
figcaption { font: 7.5pt Silk, monospace; letter-spacing: .06em; color: #6e6e6b; margin-top: 1.4mm; text-transform: uppercase; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
.three { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 3mm; }
table { border-collapse: collapse; width: 100%; margin: 0 0 3mm; font-size: 9.4pt; }
td, th { border-bottom: .6pt solid #c9c8c2; padding: 1.4mm 2mm 1.4mm 0; text-align: left; vertical-align: top; }
th { font: 7.5pt Silk, monospace; letter-spacing: .08em; text-transform: uppercase; color: #6e6e6b; font-weight: normal; }
.note { border-left: 2.4pt solid #d8ff3c; background: #f6f6f1; padding: 2mm 3mm; margin: 0 0 3mm; }
.page { page-break-after: always; }
.cover { background: #000; color: #f2f2ee; height: 263mm; margin: -16mm -16mm 0; padding: 22mm 18mm; position: relative; page-break-after: always; }
.cover h1 { font: 900 54pt/1 Doto, monospace; letter-spacing: .04em; margin: 8mm 0 3mm; }
.cover .sub { font: 10pt Silk, monospace; letter-spacing: .14em; color: #8a8a86; text-transform: uppercase; }
.cover img.hero { width: 100%; margin-top: 12mm; border-radius: 2mm; }
.cover .gif { position: absolute; right: 18mm; top: 14mm; width: 52mm; }
.cover .foot { position: absolute; bottom: 16mm; left: 18mm; right: 18mm; font: 8pt Silk, monospace; letter-spacing: .1em; color: #8a8a86; display: flex; justify-content: space-between; }
.acc { color: #d8ff3c; }
"""

T = {
"ru": dict(
    title="escape/UI", sub="Тема для EmulationStation · TrimUI Brick · Knulli", guide="Инструкция",
    s1="Что это", p1="""<p>escape/UI — тема оболочки EmulationStation для TrimUI Brick с прошивкой Knulli. Чёрный экран,
тонкие линии, точечные шрифты и наклейки — смесь Nothing, Apple, Y2K и брутализма.</p>
<p>У каждой коллекции или консоли на главном экране — своя вращающаяся проволочная фигура (одна из 18), крупная
надпись и наклейки. У каждой игры — свой лист наклеек на сером узоре, с картинкой игры в виде полароида.
Всё это рисуется под ваши коллекции и игры заранее — приставка только показывает готовое.</p>""",
    s2="Установка", p2="""<ol>
<li>Скачайте архив <code>escape-ui-theme-vX.Y.zip</code> со страницы проекта на GitHub (Releases).</li>
<li>Скопируйте папки <code>themes</code> и <code>roms</code> из архива в корень раздела SHARE (<code>/userdata</code>) —
по сети (<code>\\\\KNULLI\\share</code>) или вставив карту в компьютер. Тема должна оказаться ровно в
<code>/userdata/themes/es-theme-escape-ui</code>.</li>
<li>На приставке выполните UPDATE GAMELISTS в меню (или перезагрузите её) и запустите <b>EscapeUI</b> из PORTS.</li>
<li>Экран установки: <span class="k">A</span> — включить тему; <span class="k">X</span> — то же и показывать кастомные
коллекции сразу на главном экране; <span class="k">B</span> — выйти, ничего не меняя.</li></ol>
<p>Первый запуск рисует картинки текущего цвета — несколько минут, с полосой прогресса. Потом оболочка
перезапустится уже с темой.</p>
<div class="note">Если PORTS у вас скрыт, добавьте EscapeUI в любую свою коллекцию (в списке игр: SELECT → ADD TO COLLECTION)
или временно покажите PORTS.</div>""",
    s3="Главный экран и списки", p3="""<p>Карточка коллекции: слева — номер, название, количество игр и папка; справа — фигура,
крупная подпись и наклейки (их количество задаёт уровень детализации). Внизу — полоса соседних коллекций.</p>
<p>В списке игр справа — лист наклеек выбранной игры: узор, её картинка-полароид (если есть) или логотип,
и наклейки по уровню «cover stickers».</p>""",
    cap_home="Главный экран", cap_list="Список игр",
    s4="Настройки темы", p4="""<p>START → USER INTERFACE SETTINGS → THEME CONFIGURATION. Всё переключается сразу.</p>
<table><tr><th>Пункт</th><th>Что делает</th></tr>
<tr><td>Detail level</td><td>Сколько наклеек на главном экране: 0 — только текст, 5 — всё. Первый пункт «default (3)» = 3.</td></tr>
<tr><td>Cover stickers</td><td>Сколько наклеек на листах игр: 0 — только узор, 5 — сколько поместится.</td></tr>
<tr><td>Figure motion</td><td>video — фигура вращается (с глитч-появлением); light — картинка медленно поворачивается и «дышит» (почти не тратит батарею); still — без движения.</td></tr>
<tr><td>Chromatic aberration</td><td>Лёгкое красно-голубое расслоение картинок темы (текст остаётся чистым).</td></tr>
<tr><td>Low battery pulse</td><td>Красная пульсирующая виньетка при низком заряде.</td></tr>
<tr><td>Charging screen</td><td>Экран зарядки (см. ниже).</td></tr>
<tr><td>Smooth mode</td><td>В меню процессор работает на полной частоте — анимации без рывков. В играх частотой управляет система.</td></tr>
<tr><td>Accent colour</td><td>Один из 10 цветов: white, red, orange, yellow, acid, green, ice, blue, violet, pink.</td></tr></table>""",
    cap_menu="Theme configuration",
    s5="Приложение escape-UI", p5="""<p>PORTS (или ваша коллекция APPS) → <b>EscapeUI</b>. Здесь то же, что в меню оболочки, и ещё:</p>
<ul><li><b>Figures</b> — фигура для каждой коллекции (18 вариантов);</li>
<li><b>Patterns of covers</b> — узор для каждой игры (16 вариантов);</li>
<li><b>Covers of games</b> — что лежит на листе: картинка игры, ваша картинка, логотип или ничего;</li>
<li><b>Boot logo</b> — фигура на экране загрузки и зарядки;</li>
<li><b>Draw all colours</b> — дорисовать недостающие цвета; <b>Reset</b> — сбросить фигуры и узоры.</li></ul>
<p>Управление: крестовина, <span class="k">A</span> — выбрать/изменить, <span class="k">B</span> или <span class="k">START</span> — сохранить
и выйти. Если библиотека вариантов нарисована заранее, смена фигуры или узора — это просто копирование файлов.</p>
<p>Своя картинка обложки: положите <code>&lt;название игры&gt;.png</code> или <code>.jpg</code> в
<code>/userdata/system/configs/escape-ui/covers/</code> и выберите «custom» в Covers of games.</p>""",
    s6="Экран зарядки", p6="""<p>Если приставка стоит на зарядке и её 15 секунд не трогают (в меню, не в игре), появляется экран
загрузки со случайной вращающейся фигурой, глитч-вспышками и процентом заряда. Любая кнопка возвращает в меню —
нажатие в меню не уходит, а фигура на главном экране проявляется через глитч. Пока заряжается, через 15 секунд
без кнопок экран вернётся с новой фигурой. Выключается в настройках темы.</p>""",
    cap_c1="Экран зарядки", cap_c2="Глитч-вспышка", cap_c3="Возврат: глитчит только фигура",
    s7="Коллекции, игры и названия", p7="""<ul>
<li>Новые коллекции и игры подхватываются сами: после выхода из игры и смены настроек генератор в фоне
дорисовывает недостающее. Пока картинки нет, коллекция показывается запасной карточкой со своим названием.</li>
<li>Без кастомных коллекций всё тоже работает: свои карточки получают консоли с играми (SYSTEM) и включённые
автоколлекции оболочки — избранное, последние, все игры (AUTO). Игры без скрапа тоже учитываются.</li>
<li>Названия на любом языке: буквы, которых нет в шрифтах темы (кириллица, японский, корейский), берутся из
системных шрифтов Knulli и в точечном шрифте перерисовываются точками. Эмодзи не рисуются.</li>
<li>Игры с <code>: ? * " &lt; &gt; |</code> в названии получают обложку по пути к файлу игры.</li></ul>""",
    s8="Всё заранее на компьютере", p8="""<p>Приставка умеет рисовать сама, но компьютер делает это раза в три быстрее и не нагружает её.
Нужны Python 3.12 с Pillow и numpy, а также ffmpeg.</p>
<pre># на приставке (ssh): что рисовать
python3 /userdata/themes/es-theme-escape-ui/tool/gen.py --snapshot > snapshot.json
# на компьютере, в папке themes/es-theme-escape-ui/tool
ESCAPE_PC=snapshot.json ESCAPE_GEN=out ESCAPE_FFMPEG=ffmpeg ESCAPE_JPFONT=NotoSansJP-VF.ttf \\
  python gen.py --all-colours --all-levels
ESCAPE_PC=snapshot.json ESCAPE_GEN=out python gen.py --library</pre>
<p>Папки из <code>out/</code> скопируйте в <code>/userdata/themes/es-theme-escape-ui/gen/</code> и перезапустите оболочку.
<code>--library</code> рисует все варианты: каждую коллекцию с каждой фигурой, каждую игру на каждом узоре,
каждое бут-лого — тогда приставке больше ничего не приходится рисовать.</p>""",
    s9="Если что-то не так", p9="""<table><tr><th>Что видно</th><th>Что сделать</th></tr>
<tr><td>Цвета нет в списке</td><td>Он ещё не нарисован: escape-UI → Draw all colours, или оставьте на зарядке, или нарисуйте на компьютере.</td></tr>
<tr><td>Новая коллекция — запасная карточка</td><td>Картинка появится после следующего запуска оболочки (или откройте и закройте escape-UI).</td></tr>
<tr><td>Лист игры «NO SHEET YET»</td><td>Генератор ещё не дошёл до игры — подождите или откройте escape-UI.</td></tr>
<tr><td>Меню подтормаживает</td><td>Идёт фоновая дорисовка; включите Smooth mode, Figure motion → light, или нарисуйте всё на компьютере.</td></tr>
<tr><td>Журнал</td><td><code>/userdata/system/configs/escape-ui/gen.log</code></td></tr></table>""",
    s10="Удаление", p10="""<p>THEME SET → другая тема. Затем удалите <code>/userdata/themes/es-theme-escape-ui</code>,
<code>/userdata/roms/ports/EscapeUI.sh</code>, <code>/userdata/system/configs/escape-ui</code>, файлы
<code>escape-ui.sh</code> в <code>/userdata/system/configs/emulationstation/scripts/*/</code> и две строки после
<code># escape/UI</code> в <code>/userdata/system/custom.sh</code>.</p>
<p class="tag">Шрифты Doto, Silkscreen, Archivo, Martian Mono — SIL Open Font License. Код — MIT.</p>"""),
"en": dict(
    title="escape/UI", sub="EmulationStation theme · TrimUI Brick · Knulli", guide="Guide",
    s1="What it is", p1="""<p>escape/UI is a theme for EmulationStation on the TrimUI Brick running Knulli. A black screen,
hairlines, dot-matrix type and stickers — Nothing, Apple, Y2K and brutalism in one.</p>
<p>Every collection or console on the home screen gets one of 18 turning wire figures, a big label and stickers.
Every game gets its own sticker sheet on a grey pattern, with its picture as a Polaroid. It is all drawn for your
collections and games ahead of time — the console only shows finished pictures.</p>""",
    s2="Install", p2="""<ol>
<li>Download <code>escape-ui-theme-vX.Y.zip</code> from the project's GitHub page (Releases).</li>
<li>Copy the <code>themes</code> and <code>roms</code> folders from the archive to the root of SHARE (<code>/userdata</code>) —
over the network (<code>\\\\KNULLI\\share</code>) or with the card in a computer. The theme must end up exactly at
<code>/userdata/themes/es-theme-escape-ui</code>.</li>
<li>On the Brick run UPDATE GAMELISTS from the menu (or reboot), then start <b>EscapeUI</b> from PORTS.</li>
<li>Setup screen: <span class="k">A</span> — turn the theme on; <span class="k">X</span> — the same, plus custom collections straight
on the home screen; <span class="k">B</span> — leave without changes.</li></ol>
<p>The first run draws the current colour — a few minutes, with a progress bar. Then ES restarts with the theme.</p>
<div class="note">If PORTS is hidden, add EscapeUI to one of your collections (game list: SELECT → ADD TO COLLECTION)
or show PORTS for a moment.</div>""",
    s3="Home screen and lists", p3="""<p>A collection card: on the left its number, name, game count and folder; on the right the figure,
the big label and stickers (how many depends on the detail level). At the bottom, the strip of neighbouring collections.</p>
<p>In a game list the selected game's sticker sheet sits on the right: a pattern, its picture as a Polaroid (when it has one)
or a logo, and stickers by the "cover stickers" level.</p>""",
    cap_home="Home screen", cap_list="Game list",
    s4="Theme settings", p4="""<p>START → USER INTERFACE SETTINGS → THEME CONFIGURATION. Everything switches instantly.</p>
<table><tr><th>Option</th><th>What it does</th></tr>
<tr><td>Detail level</td><td>How many stickers on the home screen: 0 — text only, 5 — everything. The first entry, "default (3)", equals 3.</td></tr>
<tr><td>Cover stickers</td><td>How many stickers on the game sheets: 0 — pattern only, 5 — as many as fit.</td></tr>
<tr><td>Figure motion</td><td>video — the figure turns (glitch entrance); light — a still picture turns slowly and breathes (almost free on battery); still — no motion.</td></tr>
<tr><td>Chromatic aberration</td><td>A slight red/cyan split on the theme's pictures (text stays clean).</td></tr>
<tr><td>Low battery pulse</td><td>A red pulsing vignette when the battery is low.</td></tr>
<tr><td>Charging screen</td><td>See below.</td></tr>
<tr><td>Smooth mode</td><td>Full CPU speed on the menus, so animations never stutter. Games keep the system's own setting.</td></tr>
<tr><td>Accent colour</td><td>One of 10: white, red, orange, yellow, acid, green, ice, blue, violet, pink.</td></tr></table>""",
    cap_menu="Theme configuration",
    s5="The escape-UI app", p5="""<p>PORTS (or your APPS collection) → <b>EscapeUI</b>. Everything from ES's menu, plus:</p>
<ul><li><b>Figures</b> — the figure of each collection (18);</li>
<li><b>Patterns of covers</b> — the pattern of each game (16);</li>
<li><b>Covers of games</b> — what is on a sheet: the game's picture, your own, a logo, or nothing;</li>
<li><b>Boot logo</b> — the figure of the boot and charging screens;</li>
<li><b>Draw all colours</b> — draw the missing colours; <b>Reset</b> — figures and patterns back to default.</li></ul>
<p>D-pad to move, <span class="k">A</span> to pick or change, <span class="k">B</span> or <span class="k">START</span> to save and leave.
With the variant library drawn ahead, a new figure or pattern is just a file copy.</p>
<p>Your own cover picture: put <code>&lt;game name&gt;.png</code> or <code>.jpg</code> into
<code>/userdata/system/configs/escape-ui/covers/</code> and choose "custom" in Covers of games.</p>""",
    s6="Charging screen", p6="""<p>On the charger and untouched for 15 seconds (on the menus, not in a game), the Brick shows the boot screen
with a random turning figure, glitch bursts and the charge. Any button brings the menu back — the press does not reach the menu,
and the figure on the home screen glitches back in. While charging, 15 more seconds without buttons bring it back with a new figure.
It can be turned off in the theme settings.</p>""",
    cap_c1="Charging screen", cap_c2="A glitch burst", cap_c3="The way back: only the figure glitches",
    s7="Collections, games and names", p7="""<ul>
<li>New collections and games are picked up on their own: after a game and after a settings change the generator fills in what is
missing in the background. Until then a collection shows a stand-in card with its name.</li>
<li>No custom collections needed: consoles with games (SYSTEM) and ES's own collections — favourites, last played, all games (AUTO) —
get cards too. Unscraped games count as well.</li>
<li>Names in any script: letters the theme's fonts lack (Cyrillic, Japanese, Korean…) come from Knulli's system fonts and are
redrawn as dots for the dot-matrix font. Emoji are left out.</li>
<li>Games with <code>: ? * " &lt; &gt; |</code> in their names get their sheets by rom file path.</li></ul>""",
    s8="Everything ahead on a PC", p8="""<p>The Brick can draw everything itself, but a PC is about three times faster and keeps the console idle.
You need Python 3.12 with Pillow and numpy, and ffmpeg.</p>
<pre># on the Brick (ssh): what to draw
python3 /userdata/themes/es-theme-escape-ui/tool/gen.py --snapshot > snapshot.json
# on the PC, in themes/es-theme-escape-ui/tool
ESCAPE_PC=snapshot.json ESCAPE_GEN=out ESCAPE_FFMPEG=ffmpeg ESCAPE_JPFONT=NotoSansJP-VF.ttf \\
  python gen.py --all-colours --all-levels
ESCAPE_PC=snapshot.json ESCAPE_GEN=out python gen.py --library</pre>
<p>Copy the folders from <code>out/</code> into <code>/userdata/themes/es-theme-escape-ui/gen/</code> and restart ES.
<code>--library</code> draws every variant — each collection with each figure, each game on each pattern, each boot logo —
so the Brick never has to draw anything.</p>""",
    s9="Troubleshooting", p9="""<table><tr><th>You see</th><th>Do</th></tr>
<tr><td>A colour is missing from the list</td><td>It is not drawn yet: escape-UI → Draw all colours, leave the Brick on the charger, or draw on a PC.</td></tr>
<tr><td>A new collection shows a stand-in card</td><td>Its art appears after the next ES start (or open and close escape-UI).</td></tr>
<tr><td>A sheet says "NO SHEET YET"</td><td>The generator has not reached that game yet — wait, or open escape-UI.</td></tr>
<tr><td>The menus stutter</td><td>A background drawing run is busy; turn on Smooth mode, set Figure motion → light, or draw everything on a PC.</td></tr>
<tr><td>Log</td><td><code>/userdata/system/configs/escape-ui/gen.log</code></td></tr></table>""",
    s10="Uninstall", p10="""<p>THEME SET → another theme. Then delete <code>/userdata/themes/es-theme-escape-ui</code>,
<code>/userdata/roms/ports/EscapeUI.sh</code>, <code>/userdata/system/configs/escape-ui</code>, the
<code>escape-ui.sh</code> files in <code>/userdata/system/configs/emulationstation/scripts/*/</code> and the two lines after
<code># escape/UI</code> in <code>/userdata/system/custom.sh</code>.</p>
<p class="tag">Fonts: Doto, Silkscreen, Archivo, Martian Mono — SIL Open Font License. Code: MIT.</p>"""),
}


def page(lang):
    t = T[lang]; i = IMG
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{t['title']} · {t['guide']}</title>
<style>{CSS.replace('%(f)s', FONTS)}</style></head><body>
<div class="cover"><div class="sub">{t['guide']} · v1.2</div><h1>escape<span class="acc">/</span>UI</h1>
<div class="sub">{t['sub']}</div><img class="hero" src="file:///{i}/home-apps.png">
<div class="foot"><span>github.com/obhateion/escape-ui</span><span>エスケープ</span></div></div>
<h2>{t['s1']}</h2>{t['p1']}
<h2>{t['s2']}</h2>{t['p2']}
<h2>{t['s3']}</h2>{t['p3']}
<div class="two"><figure><img src="file:///{i}/home-sound.png"><figcaption>{t['cap_home']}</figcaption></figure>
<figure><img src="file:///{i}/list.png"><figcaption>{t['cap_list']}</figcaption></figure></div>
<div class="page"></div>
<h2>{t['s4']}</h2>{t['p4']}
<figure><img src="file:///{i}/levels.png" style="width:70%"><figcaption>{t['cap_menu']}</figcaption></figure>
<h2>{t['s5']}</h2>{t['p5']}
<div class="page"></div>
<h2>{t['s6']}</h2>{t['p6']}
<div class="three"><figure><img src="file:///{i}/charging.png"><figcaption>{t['cap_c1']}</figcaption></figure>
<figure><img src="file:///{i}/charging-glitch.png"><figcaption>{t['cap_c2']}</figcaption></figure>
<figure><img src="file:///{i}/way-back.png"><figcaption>{t['cap_c3']}</figcaption></figure></div>
<h2>{t['s7']}</h2>{t['p7']}
<figure><img src="file:///{i}/figures.png" style="width:46%"><figcaption>18 × 10</figcaption></figure>
<div class="page"></div>
<h2>{t['s8']}</h2>{t['p8']}
<h2>{t['s9']}</h2>{t['p9']}
<h2>{t['s10']}</h2>{t['p10']}
</body></html>"""


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for lang in ("ru", "en"):
        html = os.path.join(HERE, "guide-%s.html" % lang)
        open(html, "w", encoding="utf-8").write(page(lang))
        pdf = os.path.abspath(os.path.join(out, "escape-ui-guide-%s.pdf" % lang))
        if os.path.exists(pdf):
            os.remove(pdf)
        import tempfile
        prof = tempfile.mkdtemp(prefix="escguide")   # its own profile: a running Edge would swallow the job
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--no-pdf-header-footer",
                        "--user-data-dir=" + prof, "--virtual-time-budget=8000",
                        "--print-to-pdf=" + pdf, "file:///" + html.replace("\\", "/")], check=True, timeout=180)
        import time   # Edge hands the job to a child and returns before the file is written
        last = -1
        for _ in range(120):
            time.sleep(1)
            n = os.path.getsize(pdf) if os.path.exists(pdf) else -1
            if n > 0 and n == last:
                break
            last = n
        print(pdf, os.path.getsize(pdf))


if __name__ == "__main__":
    main()
