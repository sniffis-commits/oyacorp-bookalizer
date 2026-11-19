#!/usr/bin/env python3
# Build content.html for the Vivliostyle Rambam PoC.
# Content is kept as data (semantic anchors via id/data-for attributes),
# layout lives entirely in the template CSS files.
import re, html, pathlib

BASE = pathlib.Path(__file__).parent

H3 = "נושאי המת שעברו בו תחת האכסדרה והגיף אחד מהן את הדלת וסמכו במפתח כדי שלא יטמא הבית. וכן אם היה אדם מבפנים או מבחוץ סומך הדלת אם יכול הדלת לעמוד בפני עצמו הבית טהור. ואם לאו הבית טמא לפי שנמצא האדם הוא שחצץ בפני הטומאה והאדם והכלים מביאין ואינן חוצצין כמו שביארנו:"

H4 = "תנור שהוא עומד בתוך הבית ועינו קמורה לחוץ והאהילו נושאי המת על עינו הקמורה התנור טמא והבית טהור. שהרי אין התנור גבוה מעל הארץ כדי שיביא טומאה לבית. מגדל הבא במדה שהוא עומד בתוך הפתח ונפתח לחוץ טומאה בתוכו הבית טהור טומאה בבית מה שבתוכו טמא שהרי הוא פתוח בתוך הפתח ודרך הטומאה לצאת ואין דרכה להכנס. היתה מוכני שלו משוכה לאחוריו ויוצאת פחות מטפח ואינה נשמטת וטומאה שם בתוכה כנגד הקורות הבית טהור שאע\"פ שהיא יוצאה אינה נשמטת ואינה יוצאת טפח. והוא שיהיה בה טפח על רום טפח חלול. אבל אם אין במוכני חלל טפח הרי הטומאה רצוצה בתוך הבית והבית טמא. היה המגדל עומד בתוך הבית והטומאה בתוכו או בתוך התיבה שלו אע\"פ שאין ביציאתו פותח טפח הבית טמא. טומאה בבית מה שבתוכו טהור שדרך הטומאה לצאת ואין דרכה להכנס:"

H5 = "כלים שבין המגדל ובין הארץ שבינו ובין הכותל ושבינו ובין הקורות אם יש שם פותח טפח טמאים ואם לאו טהורים שהרי אנו רואים את הקורות כאילו הן יורדות וסותמות:"

RAAVAD4 = "שאין התנור גבוה מעל הארץ. א\"א זה הטעם אינו כלום שב\"ש למה מטמאים את הכל ועוד שהתוספתא מפרשא שאין התנור טמא אלא בעין גבוה טפח ורוחב טפח אלא הטעם לב\"ש מפני שהמת מתאהל על אויר עינו של תנור והעין מביא טומאה לתנור והתנור כיון שהוא טמא אינו חוצץ וכאילו נכנסה הטומאה לאויר הבית וב\"ה סברי דיו לאויר העין שיטמא את התנור אבל לא נחשוב אויר העין כאויר הבית ור\"ע סבר הכל טהור ואויר העין כאויר התנור למי שמאהיל עליו ואם נתן על אויר העין נסר שהוא רחב וארוך אע\"פ שאין בקימורו רוחב טפח בקעה טומאה את הנסר שאין הנסר מציל אלא בצמיד פתיל ועוד שהנסר משופע ועולה ומקבל טומאה ואינו חוצץ ומביא את הטומאה לתנור, תוספתא:"

RAAVAD5 = "כלים שבין המגדל ובין הארץ שבינו ובין הכותל וכו' אם יש שם פותח טפח טמאים ואם לאו טהורים. א\"א לא כל הענינים שוים כשהכלים בינו ובין הארץ או בינו ובין הקורות די להם באותו פותח טפח להביא טומאה לכלי שבאמצע אבל כשהכלים בינו ובין הכותל לא תביא להם טומאה באותו חלל טפח בלבד עד שיהא ג\"כ פותח טפח או מלמעלה או מלמטה:"

def km_blocks():
    """Extract the Kesef Mishneh block from the fetched mfid page and split it
    per halacha at the dibbur-hamatchil boundary."""
    raw = pathlib.Path('/tmp/km.json').read_text(encoding='utf-8')
    sec1 = raw.split('[2]')[0]
    m = re.search(r'\| [^|]*?כסף משנה[^|]*?\| (.*?) \|\s*\n\| --- \|', sec1, re.S)
    block = re.sub(r'\s+', ' ', m.group(1)).strip()
    marker = 'פירוש אם יש טפח בין מגדל לכותל'
    i = block.find(marker)
    assert i > 0, 'KM split marker not found'
    i = block.rfind('ומ"ש', 0, i)
    return block[:i].strip(), block[i:].strip()

KM4, KM5 = km_blocks()

def pcomm(fname):
    """Extract one commentary text from a fetched HebrewBooks mfid page
    (browser innerText). The page repeats the halacha (+ Raavad), then a
    nav line whose links are separated by bare 'i' lines; the commentary
    runs from after the last 'i' line to the footer."""
    lines = pathlib.Path(fname).read_text(encoding='utf-8').splitlines()
    last_i = max(i for i, l in enumerate(lines) if l.strip() == 'i')
    body = []
    for l in lines[last_i + 1:]:
        if l.strip().startswith('©2026'):
            break
        body.append(l.strip())
    text = re.sub(r'\s+', ' ', ' '.join(body)).strip()
    assert len(text) > 20, f'commentary extraction failed for {fname}'
    return text

KM3 = pcomm('/tmp/comm/p1.txt')     # כסף משנה על הלכה ג
MR3 = pcomm('/tmp/comm/p2.txt')     # מעשה רקח על הלכה ג
OH4 = pcomm('/tmp/comm/p3.txt')     # אור הישר על הלכה ד
MR4 = pcomm('/tmp/comm/p4.txt')     # מעשה רקח על הלכה ד
MKM4 = pcomm('/tmp/comm/p5.txt')    # מרכבת המשנה על הלכה ד
SV4 = pcomm('/tmp/comm/p6.txt')     # שהם וישפה על הלכה ד
TI5 = pcomm('/tmp/comm/p7.txt')     # טהרת ישראל על הלכה ה
MKM5 = pcomm('/tmp/comm/p8.txt')    # מרכבת המשנה על הלכה ה

def comm(name, cls, anchor, letter, dibbur, text):
    body = (f'<span class="dibbur">{html.escape(dibbur)}</span> ' if dibbur else '') + html.escape(text)
    return (f'<aside class="comm {cls} st-comm" data-for="{anchor}">'
            f'<b class="comm-name st-label">[הלכה {letter}] {html.escape(name)}:</b> {body}</aside>')

# Source is segmented so each commentary sits right after the passage it
# comments on (semantic anchor = document position), not dumped at the end.
H4_S1 = "תנור שהוא עומד בתוך הבית ועינו קמורה לחוץ והאהילו נושאי המת על עינו הקמורה התנור טמא והבית טהור. שהרי אין התנור גבוה מעל הארץ כדי שיביא טומאה לבית."
H4_REST = H4[len("תנור שהוא עומד בתוך הבית ועינו קמורה לחוץ והאהילו נושאי המת על עינו הקמורה התנור טמא והבית טהור. שהרי אין התנור גבוה מעל הארץ כדי שיביא טומאה לבית."):].strip()

units = [
    ('h3', 'ג', [(H3, [comm('כסף משנה', 'km', 'h3', 'ג', '', KM3),
                       comm('מעשה רקח', 'mr', 'h3', 'ג', '', MR3)])]),
    ('h4', 'ד', [
        (H4_S1, [comm('השגות הראב"ד', 'raavad', 'h4', 'ד', '', RAAVAD4)]),
        (H4_REST, [comm('כסף משנה', 'km', 'h4', 'ד', '', KM4),
                   comm('אור הישר', 'oh', 'h4', 'ד', '', OH4),
                   comm('מעשה רקח', 'mr', 'h4', 'ד', '', MR4),
                   comm('מרכבת המשנה', 'mkm', 'h4', 'ד', '', MKM4),
                   comm('שהם וישפה', 'sv', 'h4', 'ד', '', SV4)]),
    ]),
    ('h5', 'ה', [
        (H5, [comm('השגות הראב"ד', 'raavad', 'h5', 'ה', '', RAAVAD5),
              comm('כסף משנה', 'km', 'h5', 'ה', '', KM5),
              comm('טהרת ישראל', 'ti', 'h5', 'ה', '', TI5),
              comm('מרכבת המשנה', 'mkm', 'h5', 'ה', '', MKM5)]),
    ]),
]

sections = []
for uid, letter, segments in units:
    parts = []
    for text, comms in segments:
        # Raavad floats INSIDE the central text (user model, 16:07): a float
        # only wraps content that follows it, so the raavad aside must be
        # emitted before the source block it annotates.
        raavad = [c for c in comms if 'comm raavad ' in c]
        others = [c for c in comms if 'comm raavad ' not in c]
        parts.extend(raavad)
        parts.append(f'<div class="source st-src"><p>{html.escape(text)}</p></div>')
        parts.extend(others)
    body = '\n  '.join(parts)
    sections.append(f'''<section class="halacha" id="{uid}" data-addr="פרק י״ח, הלכה {letter}">
  <h2 class="halacha-head st-head">הלכה {letter}</h2>
  {body}
</section>''')

doc = f'''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>משנה תורה, הלכות טומאת מת פרק י״ח — PoC</title>
<style>
  html {{ font-family: "Noto Serif Hebrew", "David", serif; }}
  body {{ font-size: 12pt; line-height: 1.6; }}
  h1.book {{ font-size: 16pt; text-align: center; margin: 0 0 4pt; }}
  p.sub {{ text-align: center; font-size: 9pt; color: #666; margin: 0 0 14pt; }}
  h2.halacha-head {{ font-size: 13pt; margin: 10pt 0 4pt; }}
  .comm {{ font-size: 9.5pt; }}
  .comm-name {{ font-weight: bold; }}
  .dibbur {{ font-weight: bold; }}
</style>
</head>
<body>
<header>
  <h1 class="book">משנה תורה לרמב״ם — הלכות טומאת מת, פרק י״ח</h1>
  <p class="sub">הלכות ג–ה · מקור: HebrewBooks.org · הוכחת היתכנות לעימוד עם Vivliostyle</p>
</header>
{chr(10).join(sections)}
</body>
</html>
'''

(BASE / 'content.html').write_text(doc, encoding='utf-8')
print('wrote content.html,', len(doc), 'bytes; km4 =', len(KM4), 'chars; km5 =', len(KM5), 'chars')
