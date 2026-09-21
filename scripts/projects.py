"""Tarjetas de proyecto con métricas del repositorio."""
from __future__ import annotations

import datetime as dt
import json

from build import MONO, SANS, THEMES, TODAY, USER, esc, fmt, request, stars_layer

PROJECTS = [
    dict(slug="kuni", repo="Kuni", icon="K", title="Kuni", note="Innovation Fest 2026 · hackathon",
         desc="Clinic appointment platform with WhatsApp/SMS reminders, signed webhooks and row-level security per clinic.",
         tags=["Next.js", "PostgreSQL", "Twilio"],
         highlights=["Built a 20-table PostgreSQL model + 6 views", "Implemented RLS and signed Twilio webhooks", "Connected the reminder outbox to WhatsApp/SMS"],
         metrics=[("Tables", "20"), ("SQL views", "6"), ("Demo", "E2E")],
         flow=["ENROLL", "REMIND", "ALERT", "REVIEW"]),
    dict(slug="impa", repo="Adopciones-IMPA", icon="I", title="IMPA Adopciones", note="Backend lead · team of 4",
         desc="Pet adoption platform: PostgreSQL schema, JWT authentication and role-based access control.",
         tags=["TypeScript", "PostgreSQL", "JWT"],
         highlights=["Led backend architecture in a four-person team", "Modeled adoption, scheduling and report workflows", "Implemented JWT authentication + role access"],
         metrics=[("Team", "4"), ("Workflows", "4"), ("Access", "RBAC")],
         flow=["CLIENT", "API", "RBAC", "POSTGRES"]),
    dict(slug="fraud", repo="fraud-detection-itm", icon="F", title="Fraud Detection", note="ML research · co-author",
         desc="CRISP-DM pipeline for fraudulent transactions: F1 0.9976 and AUC-PR 0.9995 on 6.36M rows.",
         tags=["Python", "XGBoost", "scikit-learn"],
         highlights=["Researched the domain and defined hypotheses", "Co-built supervised + unsupervised pipelines", "Added Pytest checks and final TEST evaluation"],
         metrics=[("Rows", "6.36M"), ("F1", "0.9976"), ("AUC-PR", "0.9995")],
         flow=["DATA", "PREP", "MODELS", "TEST"]),
    dict(slug="homelab", repo=None, icon="H", title="Home Lab", note="Personal project · 24/7",
         desc="Self-hosted Ubuntu server: reverse proxy, SSO with 2FA, mesh VPN, tested backups and sandboxed AI agents.",
         tags=["Docker", "Linux", "Caddy"],
         highlights=["Operate 15+ self-hosted services on Ubuntu", "Secured access with TLS, SSO/2FA and mesh VPN", "Tested backups, monitoring and AI sandboxes"],
         metrics=[("Services", "15+"), ("Layers", "6"), ("AI agents", "2")],
         flow=["WAN", "CADDY", "SSO", "SERVICES"]),
    dict(slug="portfolio", repo="portfolio", icon="♞", title="Portfolio", note="React 19 · Vite 7 · Motion",
         desc="Space-themed bilingual portfolio with lazy-loaded sections, light/dark themes and smooth animations.",
         tags=["React", "TypeScript", "Tailwind"],
         highlights=["Built a bilingual React 19 experience", "Created light/dark themes with accessible motion", "Optimized lazy sections and responsive media"],
         metrics=[("Locales", "2"), ("Themes", "2"), ("Sections", "6")],
         flow=["CONTENT", "REACT", "MOTION", "DEPLOY"]),
    dict(slug="projexus", repo="ProjeXus", owner="TonyMed12", icon="P", title="ProjeXus", note="Backend developer · 2025",
         desc="Regional competition platform with a Spring Boot REST backend and PostgreSQL relational model.",
         tags=["Spring Boot", "PostgreSQL", "Next.js"],
         highlights=["Developed the Spring Boot REST backend", "Designed the PostgreSQL relational model", "Unified registration, judging and result workflows"],
         metrics=[("Role", "BACKEND"), ("API", "REST"), ("Delivery", "E2E")],
         flow=["REGISTER", "EVALUATE", "RESULTS"]),
    dict(slug="aquamarine", repo="Aquamarine-Resort", icon="A", title="Aquamarine Resort", note="Web development · 2025",
         desc="Hotel website with a PHP backend, built with HTML, CSS and vanilla JavaScript.",
         tags=["PHP", "JavaScript", "CSS"],
         highlights=["Built the room catalog and responsive interface", "Implemented availability and booking in PHP", "Connected discovery to the booking request flow"],
         metrics=[("Backend", "PHP"), ("Core flows", "3"), ("UI", "RESP.")],
         flow=["DISCOVER", "CHECK", "BOOK"]),
]


def repo_metrics(project: dict) -> dict:
    if not project["repo"]:
        return {}
    owner = project.get("owner", USER)
    base = f"https://api.github.com/repos/{owner}/{project['repo']}"
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


def project_svg(theme: str, project: dict, meta: dict) -> str:
    t = THEMES[theme]
    W, H = 480, 334

    contribution = "".join(
        f'<g class="fade" style="animation-delay:{0.28 + i * .09:.2f}s">'
        f'<circle cx="27" cy="{153 + i * 23}" r="3" fill="{t["accent"]}"/>'
        f'<text x="39" y="{157 + i * 23}" class="tx">{esc(line)}</text></g>'
        for i, line in enumerate(project["highlights"])
    )

    metric_rows = "".join(
        f'<g class="fade" style="animation-delay:{0.34 + i * .09:.2f}s">'
        f'<text x="330" y="{153 + i * 23}" class="sub">{esc(label)}</text>'
        f'<text x="458" y="{153 + i * 23}" class="val" text-anchor="end">{esc(value)}</text></g>'
        for i, (label, value) in enumerate(project["metrics"])
    )

    flow_nodes, fx = [], 22.0
    for i, item in enumerate(project["flow"]):
        w = max(52.0, len(item) * 6.3 + 24)
        flow_nodes.append(
            f'<g class="fade" style="animation-delay:{0.62 + i * .08:.2f}s">'
            f'<rect x="{fx:.0f}" y="246" width="{w:.0f}" height="25" rx="12.5" fill="{t["accent"]}" fill-opacity=".09" '
            f'stroke="{t["accent"]}" stroke-opacity=".35"/>'
            f'<circle cx="{fx + 12:.0f}" cy="258.5" r="2.5" fill="{t["accent"]}"/>'
            f'<text x="{fx + 22:.0f}" y="262" class="flow">{esc(item)}</text></g>'
        )
        if i < len(project["flow"]) - 1:
            flow_nodes.append(f'<text x="{fx + w + 8:.0f}" y="263" class="arrow">→</text>')
        fx += w + 28

    chips, cx = [], 22
    for tag in project["tags"]:
        w = len(tag) * 6.6 + 18
        chips.append(
            f'<rect x="{cx:.0f}" y="286" width="{w:.0f}" height="20" rx="10" fill="{t["accent"]}" fill-opacity=".12" '
            f'stroke="{t["accent"]}" stroke-opacity=".35"/>'
            f'<text x="{cx + w / 2:.0f}" y="300" class="chip" text-anchor="middle">{esc(tag)}</text>'
        )
        cx += w + 6

    owner = project.get("owner", USER)
    label = f"{owner.lower()}/{project['repo'].lower()}" if project["repo"] else "self-hosted/home-lab"
    if meta:
        repo_signal = f"{fmt(meta['commits'])} commits · #{meta['rank']} contributor · {ago(meta.get('pushed'))}"
    elif project["repo"]:
        repo_signal = "repository metrics temporarily unavailable"
    else:
        repo_signal = "private infrastructure · running 24/7"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(project["title"])}">
<title>{esc(project["title"])}</title>
<style>
text{{font-family:{SANS};fill:{t["text"]}}}
.tx{{font-size:11.2px;fill:{t["text"]}}}
.sub{{font-family:{MONO};font-size:11px;fill:{t["dim"]}}}
.val{{font-family:{MONO};font-size:12px;font-weight:700;fill:{t["accent"]}}}
.section{{font-family:{MONO};font-size:9.5px;font-weight:700;letter-spacing:1.5px;fill:{t["dim"]}}}
.chip{{font-family:{MONO};font-size:10.5px;fill:{t["accent"]}}}
.flow{{font-family:{MONO};font-size:9px;font-weight:700;fill:{t["text"]}}}
.arrow{{font-family:{MONO};font-size:13px;fill:{t["faint"]}}}
.card{{opacity:0;animation:up .6s ease-out forwards}}
@keyframes up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.fade{{opacity:0;animation:fd .5s ease-out forwards}}
@keyframes fd{{to{{opacity:1}}}}
.glow{{animation:gl 3.5s ease-in-out infinite}}
@keyframes gl{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}}}
</style>
<defs>
<linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".6"/><stop offset=".45" stop-color="{t["border"]}"/><stop offset="1" stop-color="{t["indigo"]}" stop-opacity=".6"/></linearGradient>
<linearGradient id="i" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["sky"]}"/></linearGradient>
<radialGradient id="g"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".13"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>
</defs>
<g class="card">
<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="{t["panel"]}" stroke="url(#b)" stroke-width="1.5"/>
<circle cx="425" cy="82" r="100" fill="url(#g)"/>
{stars_layer(t, W, H, sum(map(ord, project["slug"])), 18)}
<circle cx="22" cy="20" r="3" fill="{t["accent"]}" class="glow"/>
<text x="32" y="24" class="sub">{esc(label)}</text>
<line x1="1" y1="36.5" x2="{W - 1}" y2="36.5" stroke="{t["border"]}"/>
<rect x="22" y="50" width="42" height="42" rx="11" fill="url(#i)"/>
<text x="43" y="78" text-anchor="middle" style="font-size:20px;font-weight:700;fill:{t["bg"]}">{esc(project["icon"])}</text>
<text x="76" y="68" style="font-size:17px;font-weight:700">{esc(project["title"])}</text>
<text x="76" y="86" class="sub">{esc(project["note"])}</text>
<line x1="22" y1="104.5" x2="458" y2="104.5" stroke="{t["border"]}"/>
<text x="22" y="127" class="section">MY CONTRIBUTION</text>
{contribution}
<line x1="314" y1="117" x2="314" y2="204" stroke="{t["border"]}"/>
<text x="330" y="127" class="section">PROJECT SIGNAL</text>
{metric_rows}
<line x1="22" y1="218.5" x2="458" y2="218.5" stroke="{t["border"]}"/>
<text x="22" y="238" class="section">SYSTEM FLOW</text>
{"".join(flow_nodes)}
{"".join(chips)}
<text x="458" y="321" text-anchor="end" class="sub">{esc(repo_signal)}</text>
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
