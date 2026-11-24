#!/usr/bin/env python3
"""Genera la web del Class Diary a partir de content/AAAA-MM.md.

Cada archivo de content/ es un mes: empieza con '# Mes Año' y contiene
sesiones '## Sesión N · día…' (la más reciente arriba).
Los deberes se escriben en una línea:  HW[Título|Descripción][Título|Descripción]
Uso: python3 build.py
"""
import html
import pathlib
import re

import json

import markdown
from markdown_it import MarkdownIt

MD = MarkdownIt("commonmark", {"html": True, "typographer": False}).enable("table").enable("strikethrough")

ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "content"
SITE_TITLE = "Class Diary · Básico A2"
YEAR = "2026-27"
import hashlib
CSS_V = hashlib.md5((pathlib.Path(__file__).parent / "assets" / "style.css").read_bytes()).hexdigest()[:8]


def slugify(text):
    text = text.lower()
    for a, b in zip("áéíóúüñ", "aeiouun"):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def homework(match):
    items = re.findall(r"\[([^|\]]+)\|([^\]]+)\]", match.group(0))
    rows = []
    for title, desc in items:
        key = slugify(title)[:40]
        rows.append(
            f'<li><label><input type="checkbox" data-key="{{SESSION}}-{key}">'
            f'<span><strong>{html.escape(title)}</strong>'
            f'<small>{html.escape(desc)}</small></span></label></li>'
        )
    return (
        '<div class="hw"><div class="hw-head">Homework · Deberes para la próxima clase</div>'
        f'<ul>{"".join(rows)}</ul></div>'
    )


def render_md(text):
    text = re.sub(r"^HW(\[[^\n]*)$", homework, text, flags=re.M)
    out = MD.render(text)
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    out = re.sub(r"<h3>• ", "<h3>", out)
    out = re.sub(r'<a href="(http[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', out)
    return out


def plain(text):
    return re.sub(r"<[^>]+>", "", text)


def h3_slug(sid, inner):
    return sid + "-" + slugify(html.unescape(plain(inner)))


def find_anchor(sid, hint, body_html):
    for slug in re.findall(r'<h3 id="([^"]+)">', body_html):
        if slug.startswith(sid + "-" + hint):
            return slug
    return sid


def tag_headings(body_html, sid, num):
    def repl(m):
        inner = m.group(1)
        slug = h3_slug(sid, inner)
        tags = []
        for c in COLLECTIONS:
            for n in c["items"]:
                for r in n["refs"]:
                    if r[0] == num and len(r) > 2 and slug.startswith(sid + "-" + r[2]):
                        tags.append(f'<a class="ntag {c["cls"]}" href="{c["prefix"]}-{n["id"]}.html#{slug}"><span>{c["tag"]}&nbsp;·</span> {html.escape(n["title"])}</a>')
                        break
        tag_html = f'<div class="ntags">{"".join(tags)}</div>' if tags else ""
        return f'<h3 id="{slug}">{inner}</h3>{tag_html}'
    return re.sub(r"<h3>(.*?)</h3>", repl, body_html)


def load_months():
    months = []
    for path in sorted(CONTENT.glob("*.md"), reverse=True):
        raw = path.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", raw, re.M).group(1).strip()
        parts = re.split(r"^## ", raw, flags=re.M)[1:]
        sessions = []
        for part in parts:
            heading, _, body = part.partition("\n")
            sid = slugify(heading.split("·")[0])
            date = heading.split("·", 1)[1].strip() if "·" in heading else ""
            num = re.search(r"\d+", heading).group(0)
            lead = ""
            m = re.match(r"\s*([^\n#][^\n]*)\n", body)
            if m:
                lead = m.group(1).strip()
                body = body[m.end():]
            body_html = render_md(body).replace("{SESSION}", sid)
            body_html = tag_headings(body_html, sid, int(num))
            sessions.append({"id": sid, "num": num, "date": date, "lead": re.sub(r"^\s*<p>|</p>\s*$", "", render_md(lead)), "html": body_html})
        months.append({"slug": path.stem, "title": title, "sessions": sessions})
    return months


def nav(months, current):
    links = ['<a href="index.html" class="{}">Inicio</a>'.format("on" if current == "index" else "")]
    for m in months:
        links.append(f'<a href="{m["slug"]}.html" class="{"on" if current == m["slug"] else ""}">{m["title"]}</a>')
    for c in COLLECTIONS:
        links.append(f'<a href="{c["key"]}.html" class="{"on" if current == c["key"] else ""}">{c["label"]}</a>')
    links.append('<a href="materiales.html" class="{}">Materiales</a>'.format("on" if current == "materiales" else ""))
    return '<nav class="months" aria-label="Meses">' + "".join(links) + "</nav>"


def load_materials():
    path = CONTENT / "materiales.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


MATERIALS = load_materials()


COLLECTIONS = [
    {"key": "notions", "label": "Notions", "tag": "Notion", "prefix": "notion", "cls": "",
     "badge": "Artículo", "badge_sub": "Todo lo visto, explicado y ordenado",
     "intro": "Las <b>notions</b> son las <b>ideas</b> que expresamos con la lengua: la cantidad y los números, el tiempo y las fechas, "
              "dónde está algo, el contenido y el envase… Responden a la pregunta <i>¿qué idea quiero expresar?</i> "
              "Cada una es un artículo que reúne la gramática y las palabras que necesitamos, con enlaces a las sesiones."},
    {"key": "functions", "label": "Functions", "tag": "Function", "prefix": "function", "cls": "f",
     "badge": "Artículo", "badge_sub": "Todo lo visto, explicado y ordenado",
     "intro": "Las <b>functions</b> son lo que <b>hacemos</b> con la lengua: saludar y despedirnos, presentarnos, pedir algo, "
              "corregir información, deletrear, confirmar un dato… Responden a la pregunta <i>¿qué quiero hacer?</i> "
              "Cada una es un artículo con las fórmulas y ejemplos, y enlaces a las sesiones."},
    {"key": "grammar", "label": "Grammar", "tag": "Grammar", "prefix": "grammar", "cls": "g",
     "badge": "Artículo", "badge_sub": "Todo lo visto, explicado y ordenado",
     "intro": "La <b>grammar</b> explica <b>cómo se construyen</b> las frases: el verbo <i>be</i>, las preguntas, los demostrativos, "
              "las preposiciones… Responde a la pregunta <i>¿cómo se forma?</i> "
              "Cada punto es un artículo con todo lo visto en clase; pulsa una sesión para ir a esa parte."},
    {"key": "vocabulary", "label": "Vocabulary", "tag": "Vocabulary", "prefix": "vocab", "cls": "v",
     "badge": "Lista", "badge_sub": "Pronunciación británica (RP)",
     "intro": "El <b>vocabulary</b> son las <b>palabras</b>, en listas por temas con su pronunciación en inglés británico (RP) "
              "y su traducción, y con sets de Quizlet para practicar. Responde a la pregunta <i>¿qué palabras necesito?</i>"},
]
for _c in COLLECTIONS:
    _p = CONTENT / f'{_c["key"]}.json'
    _c["items"] = json.loads(_p.read_text(encoding="utf-8")) if _p.exists() else []
NOTIONS = COLLECTIONS[0]["items"]


def session_card(s):
    used = [m for m in MATERIALS if int(s["num"]) in m["sessions"]]
    mats = ""
    if used:
        links = "".join(
            f'<a href="{m["file"]}" target="_blank" rel="noopener"><b>{m["code"]}</b> {html.escape(m["title"])}</a>'
            for m in used
        )
        mats = f'<div class="mats"><span>Materiales de la sesión</span>{links}</div>'
    for c in COLLECTIONS:
        nots = [n for n in c["items"] if any(int(s["num"]) == r[0] for r in n["refs"])]
        if nots:
            links = "".join(f'<a href="{c["prefix"]}-{n["id"]}.html">{html.escape(n["title"])}</a>' for n in nots)
            mats += f'<div class="mats nots {c["cls"]}"><span>{c["label"]} de la sesión</span>{links}</div>'
    return (
        f'<article class="session" id="{s["id"]}">'
        f'<header><span class="badge">Sesión {s["num"]}</span><time>{s["date"]}</time></header>'
        f'<p class="lead">{s["lead"]}</p>{mats}{s["html"]}</article>'
    )


def materials_page(months):
    where = {s["num"]: (m["slug"], s["id"]) for m in months for s in m["sessions"]}
    cards = []
    for mat in MATERIALS:
        sess = [str(n) for n in mat["sessions"] if str(n) in where]
        if sess:
            used = "Usada en: " + " · ".join(
                f'<a href="{where[n][0]}.html#{where[n][1]}">Sesión {n}</a>' for n in sess
            )
        else:
            used = "Para las próximas sesiones"
        cards.append(
            f'<article class="mat-card"><span class="mat-code">{mat["code"]}</span>'
            f'<div><h2>{html.escape(mat["title"])}</h2><p>{html.escape(mat["topic"])}</p>'
            f'<p class="used">{used}</p></div>'
            f'<a class="btn" href="{mat["file"]}" target="_blank" rel="noopener">Abrir PDF</a></article>'
        )
    return (
        '<h1 class="month-title">Materiales</h1>'
        '<p class="intro">Las fichas de clase (worksheets) en PDF, para repasar o imprimir. '
        'Cada ficha indica en qué sesiones la usamos.</p>' + "".join(cards)
    )


def quizlet_html(n):
    q = n.get("quizlet") or []
    if not q:
        return ""
    links = "".join(f'<a class="qz" href="{html.escape(x["url"])}" target="_blank" rel="noopener">Quizlet · {html.escape(x["title"])}</a>' for x in q)
    return f'<div class="qzs">{links}</div>'


def extract_section(body_html, anchor):
    m = re.search(rf'<h3 id="{re.escape(anchor)}">(.*?)</h3>', body_html)
    if not m:
        return None, ""
    rest = body_html[m.end():]
    nxt = re.search(r'<h3 id=|<div class="hw">', rest)
    chunk = rest[: nxt.start()] if nxt else rest
    chunk = re.sub(r'<div class="ntags">.*?</div>', "", chunk, flags=re.S)
    chunk = chunk.replace('id="', 'data-id="')
    return m.group(1), chunk


def notion_article(n, months, c):
    where = {s["num"]: (m["slug"], s["id"], s["html"], s["date"]) for m in months for s in m["sessions"]}
    parts, toc = [], []
    for r in sorted(n["refs"], key=lambda r: r[0]):
        k = str(r[0])
        if k not in where or len(r) < 3:
            continue
        slug, sid, body, date = where[k]
        anchor = find_anchor(sid, r[2], body)
        heading, chunk = extract_section(body, anchor)
        if heading is None:
            continue
        toc.append(f'<a href="#{anchor}">Sesión {k}<small>{html.escape(r[1])}</small></a>')
        parts.append(
            f'<article class="session art" id="{anchor}">'
            f'<header><span class="badge">Sesión {k}</span><time>{date}</time></header>'
            f'<h3>{heading}</h3>{chunk}'
            f'<p class="back"><a href="{slug}.html#{anchor}">Ver en el diario de la sesión {k} →</a></p></article>'
        )
    summary_path = CONTENT / c["key"] / f'{n["id"]}.md'
    summary = ""
    if summary_path.exists():
        summary = (
            f'<article class="session summary {c["cls"]}" id="resumen"><header><span class="badge sum">{c["badge"]}</span>'
            f'<time>{c["badge_sub"]}</time></header>' + quizlet_html(n)
            + render_md(summary_path.read_text(encoding="utf-8")).replace("<h3>", "<h3 class=\"sh\">")
            + "</article>"
        )
        toc.insert(0, f'<a href="#resumen">{c["badge"]}<small>Todo junto</small></a>')
    return (
        f'<p class="crumbs {c["cls"]}"><a href="{c["key"]}.html">{c["label"]}</a> ›</p>'
        f'<h1 class="month-title">{html.escape(n["title"])} <small class="en">{html.escape(n["en"])}</small></h1>'
        f'<p class="intro">{html.escape(n["desc"])} Primero, todo junto; después, lo que vimos en cada sesión.</p>'
        f'<div class="toc">{"".join(toc)}</div>' + summary
        + ('<h2 class="section-title">Sesión a sesión</h2>' if parts else "") + "".join(parts)
    )


def notions_page(months, c):
    where = {s["num"]: (m["slug"], s["id"], s["html"]) for m in months for s in m["sessions"]}
    cards = []
    for n in c["items"]:
        refs = []
        for r in sorted(n["refs"], key=lambda r: r[0]):
            num, label = r[0], r[1]
            k = str(num)
            if k in where:
                anchor = find_anchor(where[k][1], r[2], where[k][2]) if len(r) > 2 else where[k][1]
                refs.append(f'<li><a href="{c["prefix"]}-{n["id"]}.html#{anchor}"><b>Sesión {k}</b> · {html.escape(label)}</a></li>')
        cards.append(
            f'<article class="notion {c["cls"]}" id="{n["id"]}"><h2><a href="{c["prefix"]}-{n["id"]}.html">{html.escape(n["title"])}</a> <small>{html.escape(n["en"])}</small></h2>'
            f'<p>{html.escape(n["desc"])}</p>{quizlet_html(n)}<ul>{"".join(refs)}</ul>'
            f'<a class="btn read" href="{c["prefix"]}-{n["id"]}.html">{"Ver la lista completa" if c["key"] == "vocabulary" else "Leer el artículo completo"}</a></article>'
        )
    return (
        f'<h1 class="month-title">{c["label"]}</h1>'
        f'<p class="intro">{c["intro"]}</p>' + "".join(cards)
    )


def page(title, months, current, main):
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="icon" href="assets/logo-eoi.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400;1,700&family=Baloo+2:wght@600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css?v={CSS_V}">
</head>
<body>
<header class="top">
  <div class="wrap top-inner">
    <a href="index.html" class="brand"><img src="assets/logo-eoi.png" alt="EOI de Zamora"><span><b>Class Diary</b><small>Básico A2 · {YEAR}</small></span></a>
  </div>
  <div class="wrap">{nav(months, current)}</div>
</header>
<main class="wrap">
{main}
</main>
<footer class="wrap foot">
  <img src="assets/licencia-cc.png" alt="Licencia Creative Commons BY-NC-SA, Laura Jambrina Alonso">
  <p>© Laura Jambrina Alonso, EOI de Zamora. Contenido bajo licencia <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es" target="_blank" rel="noopener">CC BY-NC-SA 4.0</a>. Las referencias al libro <i>English File</i> (Oxford University Press) pertenecen a sus autores.</p>
</footer>
<script>
document.querySelectorAll('.hw input[type=checkbox]').forEach(function (box) {{
  var key = 'cd-' + box.dataset.key;
  try {{ box.checked = localStorage.getItem(key) === '1'; }} catch (e) {{}}
  box.addEventListener('change', function () {{
    try {{ localStorage.setItem(key, box.checked ? '1' : '0'); }} catch (e) {{}}
  }});
}});
</script>
</body>
</html>
"""


def build():
    months = load_months()
    latest_month = months[0]
    latest = latest_month["sessions"][0]
    month_cards = "".join(
        f'<a class="month-card" href="{m["slug"]}.html"><b>{m["title"]}</b>'
        f'<span>{len(m["sessions"])} {"sesión" if len(m["sessions"]) == 1 else "sesiones"}</span></a>'
        for m in months
    )
    index_main = f"""
<section class="hero">
  <h1>Class Diary <span>Básico A2</span></h1>
  <p>Resumen de cada clase para seguir el curso y repasar: qué vimos, lo que se escribió en la pizarra y los deberes.</p>
  <ul class="facts"><li><b>Libro</b> <i>English File</i> 5th edition A1/A2 (Oxford)</li><li><b>Horario</b> 10:05–10:55 y 11:00–12:05</li></ul>
</section>
<h2 class="section-title">Última sesión</h2>
{session_card(latest)}
<h2 class="section-title">Diario por meses</h2>
<div class="month-grid">{month_cards}</div>
"""
    (ROOT / "index.html").write_text(page(SITE_TITLE, months, "index", index_main), encoding="utf-8")
    for m in months:
        toc = "".join(f'<a href="#{s["id"]}">Sesión {s["num"]}<small>{s["date"]}</small></a>' for s in m["sessions"])
        main = (
            f'<h1 class="month-title">{m["title"]}</h1>'
            f'<div class="toc">{toc}</div>'
            + "".join(session_card(s) for s in m["sessions"])
        )
        (ROOT / f'{m["slug"]}.html').write_text(page(f'{m["title"]} · {SITE_TITLE}', months, m["slug"], main), encoding="utf-8")
    (ROOT / "materiales.html").write_text(
        page(f"Materiales · {SITE_TITLE}", months, "materiales", materials_page(months)), encoding="utf-8"
    )
    for c in COLLECTIONS:
        for n in c["items"]:
            (ROOT / f'{c["prefix"]}-{n["id"]}.html').write_text(
                page(f'{n["title"]} · {c["label"]} · {SITE_TITLE}', months, c["key"], notion_article(n, months, c)), encoding="utf-8"
            )
        (ROOT / f'{c["key"]}.html').write_text(
            page(f'{c["label"]} · {SITE_TITLE}', months, c["key"], notions_page(months, c)), encoding="utf-8"
        )
    print("OK:", ", ".join(m["slug"] for m in months))


if __name__ == "__main__":
    build()
