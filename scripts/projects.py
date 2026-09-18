"""Tarjetas de proyecto con métricas del repositorio."""
from __future__ import annotations

import datetime as dt
import json
import math

from build import MONO, SANS, THEMES, TODAY, USER, esc, fmt, request

PROJECTS = [
    dict(slug="kuni", repo="Kuni", icon="K", title="Kuni", note="Innovation Fest 2026 · hackathon",
         desc="Clinic appointment platform with WhatsApp/SMS reminders, signed webhooks and row-level security per clinic.",
         tags=["Next.js", "PostgreSQL", "Twilio"]),
    dict(slug="impa", repo="Adopciones-IMPA", icon="I", title="IMPA Adopciones", note="Backend lead · team of 4",
         desc="Pet adoption platform: PostgreSQL schema, JWT authentication and role-based access control.",
         tags=["TypeScript", "PostgreSQL", "JWT"]),
    dict(slug="fraud", repo="fraud-detection-itm", icon="F", title="Fraud Detection", note="ML research · co-author",
         desc="CRISP-DM pipeline for fraudulent transactions: F1 0.9976 and AUC-PR 0.9995 on 6.36M rows.",
         tags=["Python", "XGBoost", "scikit-learn"]),
    dict(slug="homelab", repo=None, icon="H", title="Home Lab", note="Personal project · 24/7",
         desc="Self-hosted Ubuntu server: reverse proxy, SSO with 2FA, mesh VPN, tested backups and sandboxed AI agents.",
         tags=["Docker", "Linux", "Caddy"],
         metrics=[("Services", "15+"), ("Layers", "6"), ("AI agents", "2")], ring=(1.0, "0", "open ports")),
    dict(slug="portfolio", repo="portfolio", icon="♞", title="Portfolio", note="React 19 · Vite 7 · Motion",
         desc="Space-themed bilingual portfolio with lazy-loaded sections, light/dark themes and smooth animations.",
         tags=["React", "TypeScript", "Tailwind"]),
    dict(slug="aquamarine", repo="Aquamarine-Resort", icon="A", title="Aquamarine Resort", note="Web development · 2025",
         desc="Hotel website with a PHP backend, built with HTML, CSS and vanilla JavaScript.",
         tags=["PHP", "JavaScript", "CSS"]),
]


def repo_metrics(project: dict) -> dict:
    if not project["repo"]:
        return {}
    base = f"https://api.github.com/repos/{USER}/{project['repo']}"
    repo = json.loads(request(base))
    people = [c for c in json.loads(request(f"{base}/contributors?per_page=100")) if not c["login"].endswith("[bot]")]
    total = sum(c["contributions"] for c in people) or 1
    mine = next((c["contributions"] for c in people if c["login"].lower() == USER.lower()), 0)
    rank = 1 + sum(1 for c in people if c["contributions"] > mine)
    return dict(stars=repo["stargazers_count"], pushed=repo["pushed_at"],
                commits=mine, share=mine / total, rank=rank, people=len(people))


def ago(stamp: str | None) -> str:
    if not stamp:
        return "running 24/7"
    days = (TODAY - dt.date.fromisoformat(stamp[:10])).days
    if days <= 0:
        return "updated today"
    if days < 31:
        return f"updated {days} day{'s' if days > 1 else ''} ago"
    months = days // 30
    return f"updated {months} month{'s' if months > 1 else ''} ago"


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line]


def project_svg(theme: str, project: dict, meta: dict) -> str:
    t = THEMES[theme]
    W, H = 480, 206
    if meta:
        metrics = [("Commits", fmt(meta["commits"])), ("Team", fmt(meta["people"])), ("Rank", f"#{meta['rank']}")]
        share, ring_text, ring_label = meta["share"], f"{meta['share'] * 100:.0f}%", "of commits"
    else:
        metrics = project["metrics"]
        share, ring_text, ring_label = project["ring"]
    circ = 2 * math.pi * 27
    final = circ * (1 - share)
    desc = "".join(
        f'<text x="22" y="{120 + i * 18}" class="tx">{esc(line)}</text>'
        for i, line in enumerate(wrap(project["desc"], 43)[:3])
    )
    chips, cx = [], 22
    for tag in project["tags"]:
        w = len(tag) * 6.6 + 18
        chips.append(
            f'<rect x="{cx:.0f}" y="172" width="{w:.0f}" height="20" rx="10" fill="{t["accent"]}" fill-opacity=".12" '
            f'stroke="{t["accent"]}" stroke-opacity=".35"/>'
            f'<text x="{cx + w / 2:.0f}" y="186" class="chip" text-anchor="middle">{esc(tag)}</text>'
        )
        cx += w + 6
    rows = "".join(
        f'<text x="322" y="{72 + i * 22}" class="sub">{esc(k)}</text>'
        f'<text x="396" y="{72 + i * 22}" class="val" text-anchor="end">{esc(v)}</text>'
        for i, (k, v) in enumerate(metrics)
    )
    label = f"{USER.lower()}/{project['repo'].lower()}" if project["repo"] else "self-hosted/home-lab"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(project["title"])}">
<title>{esc(project["title"])}</title>
<style>
text{{font-family:{SANS};fill:{t["text"]}}}
.tx{{font-size:12.5px;fill:{t["dim"]}}}
.sub{{font-family:{MONO};font-size:11px;fill:{t["dim"]}}}
.val{{font-family:{MONO};font-size:11.5px;font-weight:700}}
.chip{{font-family:{MONO};font-size:10.5px;fill:{t["accent"]}}}
.card{{opacity:0;animation:up .6s ease-out forwards}}
@keyframes up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.ring{{animation:rg 1.4s .35s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes rg{{to{{stroke-dashoffset:{final:.1f}}}}}
.glow{{animation:gl 3.5s ease-in-out infinite}}
@keyframes gl{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}.ring{{stroke-dashoffset:{final:.1f}}}}}
</style>
<defs>
<linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".6"/><stop offset=".45" stop-color="{t["border"]}"/><stop offset="1" stop-color="{t["indigo"]}" stop-opacity=".6"/></linearGradient>
<linearGradient id="i" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["sky"]}"/></linearGradient>
</defs>
<g class="card">
<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="{t["panel"]}" stroke="url(#b)" stroke-width="1.5"/>
<circle cx="22" cy="20" r="3" fill="{t["accent"]}" class="glow"/>
<text x="32" y="24" class="sub">{esc(label)}</text>
<line x1="1" y1="36.5" x2="{W - 1}" y2="36.5" stroke="{t["border"]}"/>
<rect x="22" y="50" width="42" height="42" rx="11" fill="url(#i)"/>
<text x="43" y="78" text-anchor="middle" style="font-size:20px;font-weight:700;fill:{t["bg"]}">{esc(project["icon"])}</text>
<text x="76" y="68" style="font-size:17px;font-weight:700">{esc(project["title"])}</text>
<text x="76" y="86" class="sub">{esc(project["note"])}</text>
{desc}
{"".join(chips)}
<line x1="308" y1="52" x2="308" y2="152" stroke="{t["border"]}"/>
{rows}
<circle cx="440" cy="92" r="27" fill="none" stroke="{t["border"]}" stroke-width="5"/>
<circle cx="440" cy="92" r="27" fill="none" stroke="{t["accent"]}" stroke-width="5" stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}" transform="rotate(-90 440 92)" class="ring"/>
<text x="440" y="97" text-anchor="middle" style="font-size:14px;font-weight:700;fill:{t["accent"]}">{esc(ring_text)}</text>
<text x="440" y="138" text-anchor="middle" class="sub">{esc(ring_label)}</text>
<text x="{W - 22}" y="186" text-anchor="end" class="sub">{esc(ago(meta.get("pushed")))}</text>
</g>
</svg>
'''


def build_projects(assets) -> None:
    # Si la API falla (límite de peticiones), se usan las últimas métricas buenas.
    cache_file = assets / "projects-cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    for project in PROJECTS:
        try:
            meta = repo_metrics(project)
            if meta:
                cache[project["slug"]] = meta
        except Exception as error:  # noqa: BLE001
            print(f"aviso: {project['slug']} usa caché ({error})")
            meta = cache.get(project["slug"], {})
        for theme in THEMES:
            (assets / f"project-{project['slug']}-{theme}.svg").write_text(
                project_svg(theme, project, meta), encoding="utf-8")
    cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
