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

ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "content"
SITE_TITLE = "Class Diary · Básico A2"
YEAR = "2026-27"


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
    out = markdown.markdown(text, extensions=["tables", "sane_lists"])
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    out = re.sub(r"<h3>• ", "<h3>", out)
    out = re.sub(r'<a href="(http[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', out)
    return out


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
            sessions.append({"id": sid, "num": num, "date": date, "lead": render_md(lead)[3:-4], "html": body_html})
        months.append({"slug": path.stem, "title": title, "sessions": sessions})
    return months


def nav(months, current):
    links = ['<a href="index.html" class="{}">Inicio</a>'.format("on" if current == "index" else "")]
    for m in months:
        links.append(f'<a href="{m["slug"]}.html" class="{"on" if current == m["slug"] else ""}">{m["title"]}</a>')
    links.append('<a href="notions.html" class="{}">Notions</a>'.format("on" if current == "notions" else ""))
    links.append('<a href="materiales.html" class="{}">Materiales</a>'.format("on" if current == "materiales" else ""))
    return '<nav class="months" aria-label="Meses">' + "".join(links) + "</nav>"


def load_materials():
    path = CONTENT / "materiales.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


MATERIALS = load_materials()


def load_notions():
    path = CONTENT / "notions.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


NOTIONS = load_notions()


def session_card(s):
    used = [m for m in MATERIALS if int(s["num"]) in m["sessions"]]
    mats = ""
    if used:
        links = "".join(
            f'<a href="{m["file"]}" target="_blank" rel="noopener"><b>{m["code"]}</b> {html.escape(m["title"])}</a>'
            for m in used
        )
        mats = f'<div class="mats"><span>Materiales de la sesión</span>{links}</div>'
    nots = [n for n in NOTIONS if any(int(s["num"]) == r[0] for r in n["refs"])]
    if nots:
        links = "".join(f'<a href="notions.html#{n["id"]}">{html.escape(n["title"])}</a>' for n in nots)
        mats += f'<div class="mats nots"><span>Notions</span>{links}</div>'
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


def notions_page(months):
    where = {s["num"]: (m["slug"], s["id"], s["date"]) for m in months for s in m["sessions"]}
    cards = []
    for n in NOTIONS:
        refs = []
        for num, label in n["refs"]:
            k = str(num)
            if k in where:
                refs.append(f'<li><a href="{where[k][0]}.html#{where[k][1]}"><b>Sesión {k}</b> · {html.escape(label)}</a></li>')
        cards.append(
            f'<article class="notion" id="{n["id"]}"><h2>{html.escape(n["title"])} <small>{html.escape(n["en"])}</small></h2>'
            f'<p>{html.escape(n["desc"])}</p><ul>{"".join(refs)}</ul></article>'
        )
    return (
        '<h1 class="month-title">Notions</h1>'
        '<p class="intro">Las ideas que expresamos en inglés (lugar, cantidad, tiempo…) y las sesiones en que las hemos trabajado. '
        'Pulsa una sesión para ir directamente a su explicación.</p>' + "".join(cards)
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
<link rel="stylesheet" href="assets/style.css">
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
    (ROOT / "notions.html").write_text(
        page(f"Notions · {SITE_TITLE}", months, "notions", notions_page(months)), encoding="utf-8"
    )
    print("OK:", ", ".join(m["slug"] for m in months))


if __name__ == "__main__":
    build()
