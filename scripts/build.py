#!/usr/bin/env python3
"""Genera las tarjetas SVG del README del perfil (modo oscuro y claro).

Uso:
    python scripts/build.py            # datos + SVG
    python scripts/build.py --avatar   # además regenera el retrato duotono (requiere Pillow)

Con GITHUB_TOKEN / ACCESS_TOKEN usa la API GraphQL. Sin token usa la API REST
pública y la página de contribuciones, útil para previsualizar en local.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import random
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

USER = "Cesaredmyt"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
TODAY = dt.date.today()

# Lenguajes que inflan el conteo por bytes sin representar código escrito a mano.
IGNORED_LANGS = {"Jupyter Notebook", "MDX", "Dockerfile", "Makefile", "PowerShell"}

# ---------------------------------------------------------------- contenido
# ("kv", clave, valor) · ("head", título) · ("gap",) · ("stats",)
PROFILE = [
    ("kv", "OS", "Windows 11, Ubuntu Server (home lab)"),
    ("kv", "Host", "Instituto Tecnológico de Morelia"),
    ("kv", "Kernel", "Backend Engineer · Full Stack"),
    ("kv", "Status", "Open to internships & junior roles"),
    ("gap",),
    ("kv", "Languages.Programming", "TypeScript, Java, Python, SQL"),
    ("kv", "Languages.Computer", "HTML, CSS, YAML, Bash"),
    ("kv", "Languages.Real", "Spanish, English (B2)"),
    ("gap",),
    ("kv", "Stack.Backend", "Node.js, Spring Boot, PostgreSQL"),
    ("kv", "Stack.Frontend", "React, Next.js, Tailwind, Motion"),
    ("kv", "Stack.Infra", "Docker, Linux, Caddy, Tailscale"),
    ("gap",),
    ("kv", "Hobbies.Board", "Chess ♞"),
    ("kv", "Hobbies.Garage", "Cars & motorsport"),
    ("kv", "Hobbies.Sky", "Space & astronomy"),
    ("head", "Contact"),
    ("kv", "Email", "dcesar664@gmail.com"),
    ("kv", "LinkedIn", "cesarenriquediazmaldonado"),
    ("kv", "Portfolio", "portfolio-xplq.vercel.app"),
    ("head", "GitHub Stats"),
    ("stats",),
]

THEMES = {
    "dark": dict(
        bg="#030712", panel="#0a0f1c", border="#1f2937", text="#e5e7eb", dim="#6b7280",
        faint="#374151", accent="#34d399", sky="#38bdf8", indigo="#818cf8", red="#f87171",
        amber="#fbbf24", star="#e5e7eb",
        heat=["#111827", "#064e3b", "#047857", "#10b981", "#6ee7b7"],
    ),
    "light": dict(
        bg="#f8fafc", panel="#ffffff", border="#e2e8f0", text="#0f172a", dim="#64748b",
        faint="#cbd5e1", accent="#059669", sky="#0284c7", indigo="#4f46e5", red="#dc2626",
        amber="#d97706", star="#94a3b8",
        heat=["#e2e8f0", "#a7f3d0", "#34d399", "#059669", "#065f46"],
    ),
}
DUOTONE = {
    "dark": ("#030712", "#0f766e", "#a7f3d0"),
    "light": ("#022c22", "#10b981", "#ecfdf5"),
}
# De sombra a luz: el brillo de cada punto decide su color y tamaño.
PARTICLE_COLORS = {
    "dark": ["#3730a3", "#4f46e5", "#38bdf8", "#2dd4bf", "#34d399", "#6ee7b7", "#a7f3d0", "#ecfdf5"],
    "light": ["#a5b4fc", "#818cf8", "#6366f1", "#3b82f6", "#0284c7", "#059669", "#047857", "#064e3b"],
}
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "Java": "#b07219",
    "HTML": "#e34c26", "CSS": "#663399", "PLpgSQL": "#336790", "PHP": "#4F5D95", "C": "#555555",
    "Shell": "#89e051", "SQL": "#e38c00",
}
MONO = "'JetBrains Mono','Cascadia Code',Consolas,'DejaVu Sans Mono',monospace"
SANS = "'Space Grotesk','Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"


# ------------------------------------------------------------------- datos
def request(url: str, payload: dict | None = None) -> str:
    headers = {"User-Agent": f"{USER}-profile-builder", "Accept": "application/vnd.github+json"}
    if TOKEN and url.startswith("https://api.github.com"):
        headers["Authorization"] = f"bearer {TOKEN}"
    body = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode()


def graphql(query: str, **variables) -> dict:
    res = json.loads(request("https://api.github.com/graphql", {"query": query, "variables": variables}))
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    return res["data"]["user"]


Q_USER = """query($login:String!){ user(login:$login){
  createdAt followers{totalCount} pullRequests{totalCount} issues{totalCount}
  repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY], includeUserRepositories:false){totalCount}
  repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC){ totalCount nodes{
    isFork stargazerCount
    languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name color } } } } } } }"""

Q_YEAR = """query($login:String!, $from:DateTime!, $to:DateTime!){ user(login:$login){
  contributionsCollection(from:$from, to:$to){ totalCommitContributions
    contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } } }"""


def fetch_graphql() -> dict:
    user = graphql(Q_USER, login=USER)
    start_year = int(user["createdAt"][:4])
    days: dict[str, int] = {}
    commits = 0
    for year in range(start_year, TODAY.year + 1):
        col = graphql(Q_YEAR, login=USER, **{"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        col = col["contributionsCollection"]
        commits += col["totalCommitContributions"]
        for week in col["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]

    langs: dict[str, list] = {}
    stars = 0
    for repo in user["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        if repo["isFork"]:
            continue
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            entry = langs.setdefault(name, [0, 0, edge["node"]["color"]])
            entry[0] += edge["size"]
            entry[1] += 1

    return dict(
        since=start_year, days=days, commits=commits, stars=stars, langs=langs,
        repos=user["repositories"]["totalCount"],
        contributed=user["repositoriesContributedTo"]["totalCount"],
        followers=user["followers"]["totalCount"],
        prs=user["pullRequests"]["totalCount"], issues=user["issues"]["totalCount"],
    )


def search_count(query: str) -> int | None:
    try:
        url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query)
        if query.startswith("author:") and "type:" not in query:
            url = "https://api.github.com/search/commits?q=" + urllib.parse.quote(query)
        return json.loads(request(url))["total_count"]
    except Exception:
        return None


def scrape_year(year: int) -> dict[str, int]:
    page = request(f"https://github.com/users/{USER}/contributions?from={year}-01-01&to={year}-12-31")
    ids = {}
    for tag in re.findall(r"<td[^>]*data-date=[^>]*>", page):
        date, cell = re.search(r'data-date="([\d-]+)"', tag), re.search(r'id="([^"]+)"', tag)
        if date and cell:
            ids[cell.group(1)] = date.group(1)
    days = {}
    for cell, count in re.findall(r'for="([^"]+)"[^>]*>(No|[\d,]+) contributions? on', page):
        if cell in ids:
            days[ids[cell]] = 0 if count == "No" else int(count.replace(",", ""))
    return days


def fetch_public() -> dict:
    user = json.loads(request(f"https://api.github.com/users/{USER}"))
    repos = json.loads(request(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"))
    start_year = int(user["created_at"][:4])
    days: dict[str, int] = {}
    for year in range(start_year, TODAY.year + 1):
        days.update(scrape_year(year))

    langs: dict[str, list] = {}
    for repo in repos:
        if repo["fork"]:
            continue
        for name, size in json.loads(request(repo["languages_url"])).items():
            entry = langs.setdefault(name, [0, 0, LANG_COLORS.get(name)])
            entry[0] += size
            entry[1] += 1

    return dict(
        since=start_year, days=days, langs=langs, repos=user["public_repos"],
        stars=sum(r["stargazers_count"] for r in repos), followers=user["followers"],
        commits=search_count(f"author:{USER}"), contributed=None,
        prs=search_count(f"author:{USER} type:pr"), issues=search_count(f"author:{USER} type:issue"),
    )


# ------------------------------------------------------------- cálculos
def streaks(days: dict[str, int]) -> dict:
    past = {d: c for d, c in days.items() if d <= TODAY.isoformat()}
    longest = (0, None, None)
    run, run_start = 0, None
    for date in sorted(past):
        if past[date] > 0:
            run_start = run_start if run else date
            run += 1
            if run > longest[0]:
                longest = (run, run_start, date)
        else:
            run = 0

    cursor = TODAY if past.get(TODAY.isoformat(), 0) else TODAY - dt.timedelta(days=1)
    end = cursor
    current = 0
    while past.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= dt.timedelta(days=1)
    return dict(
        total=sum(past.values()),
        current=current,
        current_range=(cursor + dt.timedelta(days=1), end) if current else None,
        longest=longest[0],
        longest_range=(dt.date.fromisoformat(longest[1]), dt.date.fromisoformat(longest[2])) if longest[0] else None,
    )


def top_languages(langs: dict[str, list], limit: int = 6) -> list[tuple[str, float, str]]:
    # Igual que github-readme-stats: pondera tamaño y número de repos para que un
    # proyecto enorme no aplaste a todos los demás.
    scores = {
        name: math.sqrt(size) * math.sqrt(count)
        for name, (size, count, _) in langs.items()
        if name not in IGNORED_LANGS
    }
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    total = sum(score for _, score in ranked) or 1
    return [(name, score / total * 100, langs[name][2] or LANG_COLORS.get(name, "#8b949e")) for name, score in ranked]


# ------------------------------------------------------------------ SVG
def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt(value) -> str:
    return "—" if value is None else f"{value:,}"


def short_date(day: dt.date) -> str:
    return day.strftime("%b %-d") if os.name != "nt" else day.strftime("%b %#d")


def date_range(rng) -> str:
    if not rng:
        return "—"
    a, b = rng
    if a == b:
        return f"{short_date(a)}, {a.year}"
    if a.year == b.year:
        return f"{short_date(a)} – {short_date(b)}, {b.year}"
    return f"{short_date(a)}, {a.year} – {short_date(b)}, {b.year}"


def stars_layer(t: dict, width: int, height: int, seed: int, count: int) -> str:
    rng = random.Random(seed)
    out = []
    for i in range(count):
        x, y = rng.uniform(0, width), rng.uniform(0, height)
        r = rng.choice([0.5, 0.6, 0.8, 1.0, 1.2])
        op = rng.uniform(0.15, 0.55)
        cls = ' class="tw"' if i % 6 == 0 else ""
        delay = f' style="animation-delay:{rng.uniform(0, 4):.2f}s"' if cls else ""
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{t["star"]}" opacity="{op:.2f}"{cls}{delay}/>')
    return "".join(out)


def particles(theme: str, px: float, py: float, size: float) -> str:
    dots = json.loads((ASSETS / "avatar-dots.json").read_text(encoding="utf-8"))
    rng = random.Random(5)
    levels = len(PARTICLE_COLORS[theme])
    out = []
    for x, y, light, lx, ly in dots:
        # En claro se imprime como semitono: lo oscuro pesa más.
        weight = light if theme == "dark" else 1 - light
        r = 0.25 + weight ** 1.4 * 1.45
        level = min(levels - 1, int(weight * levels))
        angle = rng.uniform(0, math.tau)
        dist = rng.uniform(80, 260)
        delay = 0.15 + y * 1.4 + rng.uniform(0, 0.6)
        wave = (math.atan2(y - 0.5, x - 0.5) + math.pi) / math.tau * 0.6
        cls = "p h" if weight > 0.8 and rng.random() < 0.12 else "p"
        out.append(
            f'<circle cx="{px + x * size:.1f}" cy="{py + y * size:.1f}" r="{r:.2f}" class="{cls} c{level}" '
            f'style="--dx:{math.cos(angle) * dist:.0f}px;--dy:{math.sin(angle) * dist:.0f}px;'
            f'--mx:{(lx - x) * size:.0f}px;--my:{(ly - y) * size:.0f}px;'
            f'animation-delay:{delay:.2f}s,{4.2 + wave:.2f}s"/>'
        )
    return "".join(out)


LINE_CHARS = 58


def kv_spans(t: dict, key: str, value: str, width: int, bullet: bool = True) -> str:
    prefix = ". " if bullet else ""
    used = len(prefix) + len(key) + 2 + len(value) + 1
    dots = " " + "." * max(2, width - used) + " "
    group, _, leaf = key.rpartition(".")
    key_spans = (
        f'<tspan fill="{t["sky"]}">{esc(group)}.</tspan><tspan fill="{t["accent"]}">{esc(leaf)}</tspan>'
        if group else f'<tspan fill="{t["accent"]}">{esc(key)}</tspan>'
    )
    return (
        f'<tspan fill="{t["faint"]}">{prefix}</tspan>{key_spans}<tspan fill="{t["dim"]}">:</tspan>'
        f'<tspan fill="{t["faint"]}">{dots}</tspan><tspan fill="{t["text"]}">{esc(value)}</tspan>'
    )


def profile_svg(theme: str, data: dict, st: dict) -> str:
    t = THEMES[theme]
    stats_rows = [
        [("Repos", f"{fmt(data['repos'])}" + (f" {{Contributed: {fmt(data['contributed'])}}}" if data["contributed"] is not None else "")),
         ("Stars", fmt(data["stars"]))],
        [("Commits", fmt(data["commits"])), ("Followers", fmt(data["followers"]))],
        [("Contributions", fmt(st["total"])), ("Streak", f"{st['current']}d")],
    ]

    x0, y0, lh = 390, 88, 19.5
    lines, y = [], y0
    for i, row in enumerate(PROFILE):
        kind = row[0]
        if kind == "gap":
            y += lh * 0.55
            continue
        if kind == "head":
            y += lh * 0.45
            title = f"— {row[1]} "
            body = (f'<tspan fill="{t["dim"]}">— </tspan><tspan fill="{t["text"]}" font-weight="700">{esc(row[1])}</tspan>'
                    f'<tspan fill="{t["faint"]}"> {"─" * (LINE_CHARS - len(title))}</tspan>')
            lines.append((y, body))
            y += lh
            continue
        if kind == "kv":
            lines.append((y, kv_spans(t, row[1], row[2], LINE_CHARS)))
            y += lh
            continue
        for pair in stats_rows:
            left = kv_spans(t, pair[0][0], pair[0][1], 30)
            right = kv_spans(t, pair[1][0], pair[1][1], LINE_CHARS - 33, bullet=False)
            lines.append((y, f'{left}<tspan fill="{t["faint"]}"> | </tspan>{right}'))
            y += lh

    height = int(y + 30)
    width = 985
    header = (
        f'<tspan fill="{t["accent"]}" font-weight="700">cesar</tspan><tspan fill="{t["dim"]}">@</tspan>'
        f'<tspan fill="{t["sky"]}" font-weight="700">morelia</tspan>'
        f'<tspan fill="{t["faint"]}"> {"─" * (LINE_CHARS - 14)}</tspan>'
    )
    rows = [f'<text x="{x0}" y="{y0 - 26}" class="ln" style="animation-delay:.1s">{header}</text>']
    for i, (ly, body) in enumerate(lines):
        rows.append(f'<text x="{x0}" y="{ly:.1f}" class="ln" style="animation-delay:{0.18 + i * 0.05:.2f}s">{body}</text>')
    cursor_y = lines[-1][0] + lh
    rows.append(
        f'<text x="{x0}" y="{cursor_y:.1f}" class="ln" style="animation-delay:{0.2 + len(lines) * 0.05:.2f}s">'
        f'<tspan fill="{t["accent"]}">❯ </tspan><tspan class="cur" fill="{t["accent"]}">█</tspan></text>'
    )

    px, py, ps = 45, 78, 300  # retrato
    cx, cy = px + ps / 2, py + ps / 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="César Díaz — Backend Engineer · Full Stack">
<title>César Díaz — Backend Engineer · Full Stack</title>
<style>
text{{font-family:{MONO};font-size:14.5px;white-space:pre}}
.ln{{opacity:0;animation:in .5s ease-out forwards}}
@keyframes in{{from{{opacity:0;transform:translateX(-6px)}}to{{opacity:1;transform:none}}}}
.tw{{animation:tw 3.6s ease-in-out infinite}}
@keyframes tw{{0%,100%{{opacity:.15}}50%{{opacity:.85}}}}
.cur{{animation:bl 1.05s steps(1) infinite}}
@keyframes bl{{50%{{opacity:0}}}}
.scan{{animation:sc 5s linear infinite}}
@keyframes sc{{from{{transform:translateY(-60px)}}to{{transform:translateY({ps + 20}px)}}}}
.pulse{{animation:pu 2s ease-out infinite;transform-origin:center;transform-box:fill-box}}
@keyframes pu{{from{{opacity:.7;transform:scale(1)}}to{{opacity:0;transform:scale(2.6)}}}}
.orbit{{animation:or 24s linear infinite;transform-origin:{cx}px {cy}px}}
@keyframes or{{to{{transform:rotate(360deg)}}}}
.p{{opacity:0;animation:as 1.6s cubic-bezier(.16,.84,.3,1) forwards,mo 12s cubic-bezier(.65,0,.35,1) infinite}}
.p.h{{fill:{t["text"]}}}
@keyframes as{{from{{opacity:0;translate:var(--dx) var(--dy)}}40%{{opacity:1}}to{{opacity:1;translate:0 0}}}}
@keyframes mo{{0%,34%{{transform:none}}46%,82%{{transform:translate(var(--mx),var(--my))}}94%,100%{{transform:none}}}}
{"".join(f".c{i}{{fill:{c}}}" for i, c in enumerate(PARTICLE_COLORS[theme]))}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}}}
</style>
<defs>
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".55"/><stop offset=".5" stop-color="{t["border"]}"/><stop offset="1" stop-color="{t["indigo"]}" stop-opacity=".5"/></linearGradient>
<radialGradient id="glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".16"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity="0"/><stop offset=".85" stop-color="{t["accent"]}" stop-opacity=".2"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></linearGradient>
<clipPath id="frame"><rect x="{px}" y="{py}" width="{ps}" height="{ps}" rx="14"/></clipPath>
</defs>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="{t["bg"]}" stroke="url(#edge)"/>
{stars_layer(t, width, height, 7, 90)}
<rect x="1" y="1" width="{width - 2}" height="38" rx="13" fill="{t["panel"]}"/>
<rect x="1" y="26" width="{width - 2}" height="13" fill="{t["panel"]}"/>
<line x1="1" y1="39.5" x2="{width - 1}" y2="39.5" stroke="{t["border"]}"/>
<circle cx="24" cy="20" r="5.5" fill="{t["red"]}" opacity=".85"/><circle cx="43" cy="20" r="5.5" fill="{t["amber"]}" opacity=".85"/><circle cx="62" cy="20" r="5.5" fill="{t["accent"]}" opacity=".85"/>
<text x="{width / 2}" y="24.5" text-anchor="middle" fill="{t["dim"]}" style="font-size:12.5px">cesar@morelia: ~ — neofetch</text>
<circle cx="{cx}" cy="{cy}" r="205" fill="url(#glow)"/>
<ellipse cx="{cx}" cy="{cy}" rx="186" ry="186" fill="none" stroke="{t["faint"]}" stroke-dasharray="2 7" opacity=".7"/>
<g class="orbit"><circle cx="{cx + 186}" cy="{cy}" r="3.5" fill="{t["sky"]}"/><circle cx="{cx - 186}" cy="{cy}" r="2" fill="{t["accent"]}" opacity=".7"/></g>
<g clip-path="url(#frame)">
<rect x="{px}" y="{py}" width="{ps}" height="{ps}" fill="{t["bg"]}"/>
{particles(theme, px, py, ps)}
<rect class="scan" x="{px}" y="{py}" width="{ps}" height="60" fill="url(#beam)"/>
</g>
<rect x="{px}" y="{py}" width="{ps}" height="{ps}" rx="14" fill="none" stroke="{t["border"]}"/>
<path d="M{px - 8} {py + 22}V{py - 8}H{px + 22}M{px + ps - 22} {py - 8}H{px + ps + 8}V{py + 22}M{px + ps + 8} {py + ps - 22}V{py + ps + 8}H{px + ps - 22}M{px + 22} {py + ps + 8}H{px - 8}V{py + ps - 22}" fill="none" stroke="{t["accent"]}" stroke-width="2" stroke-linecap="round"/>
<text x="{px}" y="{py + ps + 40}" fill="{t["text"]}" style="font-family:{SANS};font-size:19px;font-weight:700">César Díaz Maldonado</text>
<text x="{px}" y="{py + ps + 62}" fill="{t["dim"]}" style="font-size:12px">Morelia, MX · 19.70°N 101.19°W</text>
<circle cx="{px + 6}" cy="{py + ps + 84}" r="4" fill="{t["accent"]}"/><circle class="pulse" cx="{px + 6}" cy="{py + ps + 84}" r="4" fill="{t["accent"]}"/>
<text x="{px + 18}" y="{py + ps + 88}" fill="{t["accent"]}" style="font-size:12px">available · backend / full stack</text>
<line x1="{x0 - 28}" y1="64" x2="{x0 - 28}" y2="{height - 26}" stroke="{t["border"]}"/>
{"".join(rows)}
</svg>
'''


def stats_svg(theme: str, data: dict, st: dict, langs) -> str:
    t = THEMES[theme]
    W, H = 985, 385

    def panel(x, y, w, h, title, extra=""):
        return (f'<g class="card" style="animation-delay:{0.05 + x / 3000 + y / 2000:.2f}s">'
                f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["panel"]}" stroke="{t["border"]}"/>'
                f'<text x="{x + 22}" y="{y + 32}" class="lbl">{esc(title)}</text>{extra}</g>')

    # --- racha
    ax, aw, ah = 0, 485, 195
    cols = [ax + aw / 6, ax + aw / 2, ax + aw * 5 / 6]
    ring_c = 2 * math.pi * 38
    streak = (
        f'<text x="{cols[0]}" y="112" class="big" text-anchor="middle">{fmt(st["total"])}</text>'
        f'<text x="{cols[0]}" y="140" class="tx" text-anchor="middle">Total contributions</text>'
        f'<text x="{cols[0]}" y="160" class="sub" text-anchor="middle">{data["since"]} – present</text>'
        f'<circle cx="{cols[1]}" cy="100" r="38" fill="none" stroke="{t["border"]}" stroke-width="5"/>'
        f'<circle cx="{cols[1]}" cy="100" r="38" fill="none" stroke="{t["accent"]}" stroke-width="5" stroke-linecap="round" '
        f'stroke-dasharray="{ring_c:.1f}" stroke-dashoffset="{ring_c:.1f}" transform="rotate(-90 {cols[1]} 100)" class="ring"/>'
        f'<text x="{cols[1]}" y="111" class="big" text-anchor="middle" fill="{t["accent"]}">{st["current"]}</text>'
        f'<text x="{cols[1]}" y="160" class="tx" text-anchor="middle" fill="{t["accent"]}" font-weight="700">Current streak</text>'
        f'<text x="{cols[1]}" y="178" class="sub" text-anchor="middle">{date_range(st["current_range"])}</text>'
        f'<text x="{cols[2]}" y="112" class="big" text-anchor="middle">{st["longest"]}</text>'
        f'<text x="{cols[2]}" y="140" class="tx" text-anchor="middle">Longest streak</text>'
        f'<text x="{cols[2]}" y="160" class="sub" text-anchor="middle">{date_range(st["longest_range"])}</text>'
        f'<line x1="{ax + aw / 3}" y1="62" x2="{ax + aw / 3}" y2="172" stroke="{t["border"]}"/>'
        f'<line x1="{ax + aw * 2 / 3}" y1="62" x2="{ax + aw * 2 / 3}" y2="172" stroke="{t["border"]}"/>'
    )

    # --- lenguajes
    bx, bw = 500, 485
    bar_x, bar_w = bx + 22, bw - 44
    segs, legend, off = [], [], 0.0
    for i, (name, pct, color) in enumerate(langs):
        seg_w = bar_w * pct / 100
        segs.append(f'<rect x="{bar_x + off:.1f}" y="56" width="{max(seg_w - 2, 1):.1f}" height="10" fill="{color}" class="grow" style="animation-delay:{0.35 + i * 0.08:.2f}s"/>')
        off += seg_w
        col, row = i % 2, i // 2
        lx, ly = bar_x + col * (bar_w / 2), 102 + row * 28
        legend.append(
            f'<g class="fade" style="animation-delay:{0.5 + i * 0.07:.2f}s"><circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" class="tx">{esc(name)}</text>'
            f'<text x="{lx + bar_w / 2 - 16}" y="{ly}" class="sub" text-anchor="end">{pct:.1f}%</text></g>'
        )
    languages = f'<clipPath id="bar"><rect x="{bar_x}" y="56" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">{"".join(segs)}</g>{"".join(legend)}'

    # --- estadísticas
    cy0, cw, ch = 210, 300, 175
    items = [("Total stars", data["stars"], t["amber"]), ("Commits", data["commits"], t["accent"]),
             ("Pull requests", data["prs"], t["sky"]), ("Issues", data["issues"], t["indigo"]),
             ("Contributed to", data["contributed"], t["red"])]
    items = [it for it in items if it[1] is not None]
    stat_rows = "".join(
        f'<g class="fade" style="animation-delay:{0.4 + i * 0.07:.2f}s"><circle cx="30" cy="{cy0 + 61 + i * 24}" r="4" fill="{c}"/>'
        f'<text x="44" y="{cy0 + 65 + i * 24}" class="tx">{esc(label)}</text>'
        f'<text x="{cw - 22}" y="{cy0 + 65 + i * 24}" class="tx" text-anchor="end" font-weight="700">{fmt(v)}</text></g>'
        for i, (label, v, c) in enumerate(items)
    )

    # --- actividad mensual (el grid diario lo dibuja la serpiente)
    hx, hw = 315, 670
    months = []
    for back in range(11, -1, -1):
        year, month = TODAY.year, TODAY.month - back
        while month <= 0:
            year, month = year - 1, month + 12
        prefix = f"{year}-{month:02d}"
        months.append((dt.date(year, month, 1), sum(c for d, c in data["days"].items() if d.startswith(prefix))))
    peak = max(c for _, c in months) or 1
    year_total = sum(c for _, c in months)
    base_y, max_h = cy0 + ch - 34, 88
    slot = (hw - 44) / 12
    bars = []
    for i, (month, count) in enumerate(months):
        bh = max(3, count / peak * max_h)
        bx0 = hx + 22 + i * slot + slot * 0.18
        is_peak = count == peak
        bars.append(
            f'<rect x="{bx0:.1f}" y="{base_y - bh:.1f}" width="{slot * 0.64:.1f}" height="{bh:.1f}" rx="4" '
            f'fill="{t["accent"] if is_peak else t["heat"][2]}" class="rise" style="animation-delay:{0.3 + i * 0.06:.2f}s"/>'
            f'<text x="{bx0 + slot * 0.32:.1f}" y="{base_y - bh - 7:.1f}" class="sub fade" text-anchor="middle" '
            f'style="animation-delay:{0.9 + i * 0.06:.2f}s">{count}</text>'
            f'<text x="{bx0 + slot * 0.32:.1f}" y="{base_y + 18}" class="sub" text-anchor="middle">{month.strftime("%b")}</text>'
        )
    heat = (
        f'<text x="{hx + hw - 22}" y="{cy0 + 32}" class="sub" text-anchor="end">{fmt(year_total)} contributions · peak {max(months, key=lambda m: m[1])[0].strftime("%b %Y")}</text>'
        f'<line x1="{hx + 22}" y1="{base_y + .5}" x2="{hx + hw - 22}" y2="{base_y + .5}" stroke="{t["border"]}"/>'
        f'{"".join(bars)}'
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats de {USER}">
<title>GitHub stats · {USER}</title>
<style>
text{{font-family:{SANS};fill:{t["text"]}}}
.lbl{{font-family:{MONO};font-size:11.5px;letter-spacing:2px;fill:{t["dim"]}}}
.big{{font-size:30px;font-weight:700}}
.tx{{font-size:13.5px}}
.sub{{font-family:{MONO};font-size:11px;fill:{t["dim"]}}}
.card{{opacity:0;animation:up .6s ease-out forwards}}
@keyframes up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.fade{{opacity:0;animation:fd .5s ease-out forwards}}
@keyframes fd{{to{{opacity:1}}}}
.grow{{transform:scaleX(0);transform-box:fill-box;animation:gr .8s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes gr{{to{{transform:scaleX(1)}}}}
.rise{{transform:scaleY(0);transform-box:fill-box;transform-origin:bottom;animation:gr2 .9s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes gr2{{to{{transform:scaleY(1)}}}}
.ring{{animation:rg 1.4s .4s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes rg{{to{{stroke-dashoffset:{ring_c * (1 - min(st["current"], 30) / 30):.1f}}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important}}}}
</style>
{panel(ax, 0, aw, ah, "CONTRIBUTIONS", streak)}
{panel(bx, 0, bw, ah, "MOST USED LANGUAGES", languages)}
{panel(0, cy0, cw, ch, "GITHUB STATS", stat_rows)}
{panel(hx, cy0, hw, ch, "MONTHLY ACTIVITY", heat)}
</svg>
'''


def make_avatars() -> None:
    """Convierte la foto en puntos (sin fondo) y les asigna un destino en una "C"."""
    from PIL import Image, ImageFilter, ImageOps

    photo = Image.open(ASSETS / "avatar-source.webp").convert("RGB").crop((45, 20, 355, 330))
    w, h = photo.size
    pixels = photo.load()
    # La pared es verde: todo lo que no tenga ese exceso de verde es la persona.
    mask = Image.new("L", (w, h))
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            mp[x, y] = 255 if g - max(r, b) < 9 else 0
    mask = mask.filter(ImageFilter.MedianFilter(7)).filter(ImageFilter.MaxFilter(3)).load()
    gray = ImageOps.autocontrast(ImageOps.grayscale(photo), cutoff=1).filter(ImageFilter.GaussianBlur(1)).load()

    rng = random.Random(11)
    face, grid = [], 72
    step = w / grid
    for gy in range(grid):
        for gx in range(grid):
            x = min(w - 1, (gx + 0.5 + rng.uniform(-0.25, 0.25)) * step)
            y = min(h - 1, (gy + 0.5 + rng.uniform(-0.25, 0.25)) * step)
            if not mask[int(x), int(y)]:
                continue
            light = (gray[int(x), int(y)] / 255) ** 1.15
            face.append((x / w, y / h, light))

    # "C" geométrica: anillo abierto a la derecha, muestreado en rejilla uniforme.
    letter, n = [], len(face)
    outer, inner, gap = 0.40, 0.25, math.radians(48)
    spacing = math.sqrt((math.pi * (outer**2 - inner**2) * (1 - gap / math.pi)) / n)
    yy = 0.5 - outer
    while yy <= 0.5 + outer:
        xx = 0.5 - outer
        while xx <= 0.5 + outer:
            dx, dy = xx - 0.5, yy - 0.5
            dist, ang = math.hypot(dx, dy), abs(math.atan2(dy, dx))
            if inner <= dist <= outer and ang >= gap:
                letter.append((xx + rng.uniform(-0.2, 0.2) * spacing, yy + rng.uniform(-0.2, 0.2) * spacing))
            xx += spacing
        yy += spacing
    rng.shuffle(letter)
    letter = (letter * 2)[:n]

    # Emparejar por altura (con algo de ruido): la cara "fluye" hacia la C sin cruzarse
    # de lado a lado y los colores quedan repartidos por toda la letra.
    face.sort(key=lambda pt: pt[1] + rng.uniform(-0.08, 0.08))
    letter.sort(key=lambda pt: pt[1])
    dots = [[round(f[0], 4), round(f[1], 4), round(f[2], 3), round(c[0], 4), round(c[1], 4)]
            for f, c in zip(face, letter)]
    (ASSETS / "avatar-dots.json").write_text(json.dumps(dots, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    if "--avatar" in sys.argv:
        make_avatars()
    cache_file = ASSETS / "data-cache.json"
    try:
        data = fetch_graphql() if TOKEN else fetch_public()
        cache_file.write_text(json.dumps(data), encoding="utf-8")
    except Exception as error:  # noqa: BLE001 — sin red o sin cuota: último dato bueno
        print(f"aviso: se usan datos en caché ({error})")
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    st = streaks(data["days"])
    langs = top_languages(data["langs"])
    for theme in THEMES:
        (ASSETS / f"profile-{theme}.svg").write_text(profile_svg(theme, data, st), encoding="utf-8")
        (ASSETS / f"stats-{theme}.svg").write_text(stats_svg(theme, data, st, langs), encoding="utf-8")
    from projects import build_projects

    build_projects(ASSETS)
    print(f"ok · {st['total']} contribuciones · racha {st['current']} · {', '.join(n for n, _, _ in langs)}")


if __name__ == "__main__":
    main()
