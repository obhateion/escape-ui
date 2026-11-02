escape/UI — тема для EmulationStation на TrimUI Brick (Knulli)
==============================================================

Чёрный экран, тонкие линии, точечные шрифты, наклейки: Nothing + Apple + Y2K + брутализм.
У каждой коллекции (или консоли) своя вращающаяся фигура из 18 вариантов, у каждой игры —
свой лист наклеек на своём узоре. Всё рисуется прямо на приставке, под ваши коллекции и игры.

ЧТО ВНУТРИ
  themes/es-theme-escape-ui/   сама тема + генератор картинок (tool/), шрифты, шейдер, цвета
  roms/ports/EscapeUI.sh       приложение настроек «escape-UI»

УСТАНОВКА
  1. Скопируйте папки themes и roms из архива в корень раздела SHARE / userdata
     (по сети \\KNULLI\share или картой в компьютере). Путь темы должен получиться ровно
     /userdata/themes/es-theme-escape-ui (на этот путь рассчитаны приложение и фоновые скрипты).
  2. На приставке обновите списки игр (пункт UPDATE GAMELISTS в меню оболочки)
     или просто перезагрузите приставку, затем запустите «EscapeUI» из PORTS.
  3. Экран установки:
       A — включить тему и нарисовать её картинки;
       X — то же + показывать кастомные коллекции сразу на главном экране
           (без промежуточной карточки COLLECTIONS);
       B — выйти, ничего не меняя.
     Первый раз рисование занимает около 6 минут (видео фигур тоже рисуются), с полосой
     прогресса. Потом оболочка перезапустится уже с темой.
  4. По желанию: escape-UI > «Draw all colours» — нарисовать остальные 9 цветов акцента
     (около 50 минут на приставке; лучше на зарядке, пока вы ей не пользуетесь).
     Запускается вторым нажатием A (первое показывает, сколько это займёт); B — остановить,
     нарисованное сохранится.
  Если PORTS у вас скрыт — добавьте EscapeUI в любую свою коллекцию
  (в списке игр: SELECT/GAME OPTIONS > ADD TO COLLECTION) или временно покажите PORTS.

НАСТРОЙКИ
  START > UI SETTINGS > THEME CONFIGURATION — переключаются мгновенно:
    детализация 0–5 · наклейки на обложках 0–5 · движение фигур (video / light / still) ·
    (первый пункт «default (3)» — то же, что 3: так оболочка устроена, первый пункт = «по умолчанию»)
    хроматическая аберрация · красная виньетка при низком заряде · экран зарядки ·
    цвет акцента (в списке только уже нарисованные цвета).
  Приложение escape-UI — всё то же, плюс:
    бут-лого · фигура для каждой коллекции · узор для каждой игры · «Draw all colours» · сброс.
    B или START — сохранить и выйти: что нужно, перерисуется, оболочка перезапустится.

ЦВЕТА
  10 цветов: white, red, orange, yellow, acid, green, ice, blue, violet, pink. Каждый рисуется
  заранее в свою папку gen/<цвет>, поэтому переключение мгновенное. Выбор ещё не нарисованного
  цвета в escape-UI нарисует его (около 6 минут).
  Недостающие цвета приставка дорисовывает сама, когда стоит на зарядке и ей 5 минут не пользуются
  (tool/charged.py, запускается при загрузке из /userdata/system/custom.sh). Любая кнопка,
  отключение зарядки или запуск игры её сразу останавливают; нарисованное сохраняется.

ЭКРАН ЗАРЯДКИ
  Поставили на зарядку и 15 секунд ничего не трогали — открывается экран загрузки со случайной
  фигурой, глитч-вспышками и процентом заряда. Любая кнопка (она не уйдёт в меню) или отключение
  зарядки — назад, туда, где были. Пока заряжается, через 15 секунд без кнопок экран вернётся
  (с новой фигурой). Выключается в настройках темы.

ПЛАВНЫЙ РЕЖИМ (smooth mode, включён по умолчанию)
  Пока вы в меню, тема держит процессор на полной частоте (режим performance), чтобы анимации
  не ждали разгона. В играх частотой управляет сама система; при заряде ниже 15% без зарядки
  возвращается системная настройка. Ничего менять руками не нужно; выключается в настройках темы.

ДВИЖЕНИЕ ФИГУР
  video — фигура вращается (видео 24 кадра/с, на входе — короткий глитч). Красиво, но оболочка
          на главном экране держит занятым примерно одно ядро: батарея садится быстрее.
  light — неподвижная фигура медленно поворачивается и «дышит» (почти бесплатно).
  still — без движения.

НОВЫЕ КОЛЛЕКЦИИ И ИГРЫ
  Подхватываются сами: при изменении настроек и после выхода из игры генератор в фоне
  дорисовывает недостающее для текущего цвета. Пока своей картинки нет, коллекция
  показывается запасной карточкой со своим названием; своя появится после следующего запуска
  оболочки (или сразу — откройте escape-UI и выйдите по B). Другие цвета после этого
  нужно дорисовать заново («Draw all colours»), до тех пор они пропадают из списка цветов.

ДЛЯ ТЕХ, У КОГО ЕСТЬ КОМПЬЮТЕР (быстрее, необязательно)
  Все цвета можно нарисовать на ПК (Python 3.12 + Pillow + numpy + ffmpeg):
    на приставке:  python3 /userdata/themes/es-theme-escape-ui/tool/gen.py --snapshot > snapshot.json
    на ПК:         ESCAPE_PC=snapshot.json ESCAPE_GEN=out ESCAPE_FFMPEG=ffmpeg
                   ESCAPE_JPFONT=NotoSansJP-VF.ttf (взять с приставки: /usr/share/fonts/truetype/noto/)
                   python gen.py --all-colours
    папки из out/ скопируйте в /userdata/themes/es-theme-escape-ui/gen/ и перезапустите
    оболочку (или откройте и закройте escape-UI) — список цветов обновится сам.

КАРТОЧКИ И ИГРЫ
  · Без кастомных коллекций тоже работает: каждая консоль с играми получает свою карточку
    (SYSTEM, полное название, папка /roms/…), включённые автоколлекции оболочки (избранное,
    последние, все игры…) — свою (AUTO). Игры без скрапа (нет в gamelist.xml) тоже видны —
    по имени файла.
  · Названия на любом языке: буквы, которых нет в фирменных шрифтах (кириллица, японский,
    корейский…), берутся из системных шрифтов Knulli и в точечном шрифте перерисовываются
    точками. Эмодзи не рисуются (их нет ни в одном шрифте). Длинные названия уменьшаются и
    обрезаются многоточием.
  · Игры с символами : ? * " < > | \ / в названии (их нельзя использовать в имени файла на
    SHARE) получают обложку по пути к файлу игры — всё работает так же.
  · Обложки рисуются только для выбранного уровня наклеек; другой уровень дорисовывается при
    переключении (в escape-UI — сразу, из меню оболочки — в фоне). Так большая библиотека
    не занимает гигабайты: ~30 КБ на игру на цвет.

ЧТО ПОЛЕЗНО ЗНАТЬ
  · Настройки темы хранятся в /userdata/system/configs/escape-ui/config.json и в настройках
    оболочки — обновление темы их не стирает.
  · Ваши скрапнутые картинки игр тема не трогает: свои обложки она держит у себя (gen/).
  · Эффекты батареи — это значок батареи оболочки на весь экран; момент, когда оболочка
    считает батарею «пустой», задаёт сама оболочка (около 10%, может отличаться).
  · Хроматическая аберрация «always» действует на картинки темы, текст остаётся чистым.
  · Пока идёт перерисовка, не меняйте настройки темы в меню оболочки — дождитесь конца.

УДАЛЕНИЕ
  START > UI SETTINGS > THEME SET — выбрать другую тему. Потом удалить папку
  /userdata/themes/es-theme-escape-ui, файл /userdata/roms/ports/EscapeUI.sh,
  папку /userdata/system/configs/escape-ui и файлы escape-ui.sh в
  /userdata/system/configs/emulationstation/scripts/*/.
  В /userdata/system/custom.sh удалить две строки после «# escape/UI: draw the missing accent colours».

ШРИФТЫ: Doto, Silkscreen, Archivo, Martian Mono — SIL Open Font License (тексты в fonts/).
Японский текст набирается системным Noto Sans JP из Knulli.


escape/UI — EmulationStation theme for the TrimUI Brick (Knulli)
================================================================
Black screen, hairlines, dot-matrix type and stickers. Every collection (or console) gets one
of 18 turning figures, every game its own sticker sheet on a pattern — all drawn on the device.

INSTALL: copy `themes` and `roms` from this archive to the root of SHARE (/userdata); the theme
must end up at /userdata/themes/es-theme-escape-ui. Update gamelists, run "EscapeUI" from PORTS:
A = turn the theme on, X = the same + custom collections straight on the home screen, B = leave.
First drawing takes ~6 minutes, then ES restarts with the theme. "Draw all colours" in the app
draws the other 9 accent colours (~50 min on the Brick; or on a PC, see the Russian part above).
SETTINGS: UI SETTINGS > THEME CONFIGURATION (instant: levels, motion, effects, accent colour —
only drawn colours are listed), or the escape-UI app (also boot logo, per-collection figures,
per-game patterns). Motion "video" keeps about one core busy on the home screen; "light" is
almost free. New collections/games are drawn in the background for the current colour.
No custom collections needed: consoles and ES's auto collections get their own cards; unscraped
games count too. Names in any script (letters missing from the theme fonts come from Knulli's
system fonts, dotted for the dot-matrix font); names with characters SHARE can't store get their
covers by rom path. Covers are drawn for the cover level in use only (~30 KB per game per colour).
Settings: /userdata/system/configs/escape-ui/config.json. Fonts under SIL OFL.
