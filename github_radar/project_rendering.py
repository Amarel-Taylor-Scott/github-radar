"""Markdown, normalized JSON, status, validation, and static HTML outputs."""

from __future__ import annotations

import html as html_lib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from github_radar.project_common import (
    PUBLICATION_SCHEMA, Project, atomic_write, days_since, markdown_escape,
)
from github_radar.project_discovery import catalog_map
from github_radar.project_scoring import catalog_leaderboards


def signal_text(project: Project, catalog_id: str, now: datetime) -> str:
    signals: list[str] = []
    delta = project.growth.get("delta_7d")
    if delta is not None:
        signals.append(f"{int(delta):+d} stars/7d")
    else:
        velocity = float(project.growth.get("stars_per_day") or 0.0)
        if velocity > 0:
            signals.append(f"~{velocity:.1f} stars/day lifetime")
    age = days_since(project.created_at, now)
    if age <= 180:
        signals.append(f"new ({age}d)")
    idle = days_since(project.pushed_at, now)
    if idle <= 30:
        signals.append(f"pushed {idle}d ago")
    quality = project.catalog_scores.get(catalog_id, {}).get("quality", 0.0)
    if quality >= 75:
        signals.append("strong quality signals")
    if len(project.provenance) > 1:
        signals.append(f"{len(project.provenance)} discovery paths")
    return "; ".join(signals[:3]) or "activity, relevance, and metadata quality"


def render_table(
    projects: list[Project], catalog_id: str, score_key: str, now: datetime
) -> str:
    lines = [
        "| # | Project | Type | Stars | Δ7d | Quality | Score | Why it surfaced |",
        "|--:|:--------|:-----|------:|----:|--------:|------:|:-----------------|",
    ]
    for index, project in enumerate(projects, 1):
        delta = project.growth.get("delta_7d")
        delta_text = "—" if delta is None else f"{int(delta):+d}"
        scores = project.catalog_scores.get(catalog_id, {})
        description = markdown_escape(project.description)
        if len(description) > 145:
            description = description[:142].rstrip() + "…"
        lines.append(
            "| {index} | [{name}]({url})<br><sub>{description}</sub> | {kind} | {stars:,} | {delta} | {quality:.1f} | {score:.1f} | {signal} |".format(
                index=index,
                name=markdown_escape(project.full_name),
                url=project.html_url,
                description=description,
                kind=markdown_escape(project.project_type),
                stars=project.stars,
                delta=delta_text,
                quality=float(scores.get("quality", 0.0)),
                score=float(scores.get(score_key, 0.0)),
                signal=markdown_escape(signal_text(project, catalog_id, now)),
            )
        )
    if not projects:
        lines.append("| — | No qualifying projects yet | — | — | — | — | — | History is still accumulating |")
    return "\n".join(lines)


def render_catalog_markdown(
    catalog: dict[str, Any], boards: dict[str, list[Project]], generated_at: str, count: int, now: datetime
) -> str:
    catalog_id = str(catalog["id"])
    sections = [
        ("Most Interesting", "interesting", "interesting"),
        ("High Momentum", "high_momentum", "momentum"),
        ("Up and Coming", "up_and_coming", "rising"),
        ("High Quality", "high_quality", "quality"),
        ("Hidden Gems", "hidden_gems", "hidden_gem"),
        ("Most Popular", "most_popular", "popular"),
        ("New Projects", "new_projects", "rising"),
    ]
    output = [
        f"# {catalog.get('title') or catalog_id}",
        "",
        str(catalog.get("description") or ""),
        "",
        f"_Generated {generated_at}. {count:,} matching repositories._",
        "",
        "> Scores are normalized inside this catalog. Momentum is repository-level and uses measured daily history when available; missing seven-day data is never represented as zero.",
        "",
    ]
    for heading, board_key, score_key in sections:
        output.extend(
            [
                f"## {heading}",
                "",
                render_table(boards[board_key], catalog_id, score_key, now),
                "",
            ]
        )
    if boards.get("daily_movers"):
        output.extend(
            [
                "## Latest One-Day Movers",
                "",
                render_table(boards["daily_movers"], catalog_id, "momentum", now),
                "",
            ]
        )
    output.extend(
        [
            "## Ranking model",
            "",
            "Popularity, momentum, acceleration, relative growth, freshness, maintenance, metadata quality, catalog relevance, confidence, and newness remain separate dimensions. The public leaderboards blend them transparently and apply archived, stale, fork, and template penalties. Discovery is read-only; projects are never cloned, installed, imported, or executed.",
            "",
        ]
    )
    return "\n".join(output)


def render_html(
    projects: list[Project], catalogs: list[dict[str, Any]], aggregate_id: str, generated_at: str
) -> str:
    project_payload = json.dumps([project.to_dict() for project in projects], ensure_ascii=False).replace("</", "<\\/")
    catalog_payload = json.dumps(catalogs, ensure_ascii=False).replace("</", "<\\/")
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GitHub Project Radars</title>
<style>
:root{color-scheme:dark;--bg:#080b12;--panel:#101725;--panel2:#151e31;--muted:#9ba8bd;--line:#26334c;--accent:#8ea2ff;--text:#f1f4ff;--good:#8fe1bd}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#1d2855 0,transparent 32%),var(--bg);color:var(--text);font:15px/1.5 ui-sans-serif,system-ui,sans-serif}main{max-width:1600px;margin:auto;padding:42px 24px 80px}h1{font-size:clamp(36px,5vw,68px);line-height:1;margin:0 0 14px}.lede{color:var(--muted);font-size:18px;max-width:920px}.stats{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}.pill{border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:7px 12px;color:var(--muted)}.controls{display:grid;grid-template-columns:minmax(280px,2fr) repeat(4,minmax(150px,1fr));gap:10px;position:sticky;top:0;z-index:3;padding:14px 0;background:linear-gradient(var(--bg) 74%,transparent)}input,select{width:100%;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:12px;padding:12px 13px;font:inherit}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:16px;background:rgba(16,23,37,.94)}table{border-collapse:collapse;width:100%;min-width:1220px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}th{position:sticky;top:76px;background:#111a2a;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}tr:hover td{background:var(--panel2)}a{color:#bec8ff;text-decoration:none}a:hover{text-decoration:underline}.desc{max-width:430px;color:var(--muted)}.score{font-variant-numeric:tabular-nums;font-weight:750}.good{color:var(--good)}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 7px;margin:1px 3px 1px 0;font-size:12px;color:#cbd3e4}.empty{padding:55px;text-align:center;color:var(--muted)}small{color:var(--muted)}@media(max-width:1050px){.controls{grid-template-columns:1fr 1fr}.controls input{grid-column:1/-1}}
</style></head><body><main>
<h1>GitHub Project Radars</h1><p class="lede">Daily, domain-aware discovery of high-quality, high-momentum, up-and-coming, and unusually interesting open-source projects. Scores are normalized inside each topic rather than forcing every ecosystem onto the same star scale.</p>
<div class="stats"><span class="pill" id="count"></span><span class="pill">Generated __GENERATED__</span><span class="pill">Read-only metadata collection</span><span class="pill">Measured history replaces estimates automatically</span></div>
<div class="controls"><input id="search" placeholder="Search projects, descriptions, topics…"><select id="catalog"></select><select id="language"><option value="">All languages</option></select><select id="type"><option value="">All project types</option></select><select id="sort"><option value="interesting">Interesting</option><option value="momentum">Momentum</option><option value="rising">Up and coming</option><option value="quality">Quality</option><option value="hidden_gem">Hidden gems</option><option value="popular">Popular</option><option value="stars">Stars</option><option value="delta_7d">7-day gain</option></select></div>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Project</th><th>Catalogs / type</th><th>Language</th><th>Stars</th><th>Δ7d</th><th>Quality</th><th>Score</th><th>Description</th></tr></thead><tbody id="rows"></tbody></table><div id="empty" class="empty" hidden>No matching projects.</div></div>
</main><script>
const projects=__PROJECTS__,catalogs=__CATALOGS__,aggregateId=__AGGREGATE__;
const search=document.querySelector('#search'),catalog=document.querySelector('#catalog'),language=document.querySelector('#language'),type=document.querySelector('#type'),sort=document.querySelector('#sort'),rows=document.querySelector('#rows'),empty=document.querySelector('#empty'),count=document.querySelector('#count');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
catalog.innerHTML=catalogs.map(c=>`<option value="${esc(c.id)}" ${c.id===aggregateId?'selected':''}>${esc(c.title||c.id)}</option>`).join('');
[...new Set(projects.map(p=>p.language).filter(Boolean))].sort().forEach(v=>language.insertAdjacentHTML('beforeend',`<option value="${esc(v)}">${esc(v)}</option>`));
[...new Set(projects.map(p=>p.project_type).filter(Boolean))].sort().forEach(v=>type.insertAdjacentHTML('beforeend',`<option value="${esc(v)}">${esc(v)}</option>`));
function render(){const q=search.value.toLowerCase().trim(),cat=catalog.value||aggregateId,lang=language.value,kind=type.value,key=sort.value;let data=projects.filter(p=>p.catalogs.includes(cat)&&(!lang||p.language===lang)&&(!kind||p.project_type===kind)&&(!q||`${p.full_name} ${p.description} ${p.topics.join(' ')}`.toLowerCase().includes(q)));data.sort((a,b)=>{if(key==='stars')return b.stars-a.stars;if(key==='delta_7d')return (b.growth.delta_7d??-Infinity)-(a.growth.delta_7d??-Infinity);return (b.catalog_scores[cat]?.[key]||0)-(a.catalog_scores[cat]?.[key]||0)});count.textContent=`${data.length.toLocaleString()} projects`;rows.innerHTML=data.slice(0,1000).map((p,n)=>{const s=p.catalog_scores[cat]||{},delta=p.growth.delta_7d==null?'—':`${p.growth.delta_7d>=0?'+':''}${p.growth.delta_7d}`,score=key==='stars'||key==='delta_7d'?s.interesting:s[key];return `<tr><td>${n+1}</td><td><a href="${esc(p.html_url)}"><strong>${esc(p.full_name)}</strong></a><br><small>${esc(p.topics.slice(0,4).join(' · '))}</small></td><td>${p.catalogs.filter(c=>c!==aggregateId).slice(0,3).map(c=>`<span class="tag">${esc(c)}</span>`).join('')}<br><span class="tag">${esc(p.project_type)}</span></td><td>${esc(p.language||'—')}</td><td>${Number(p.stars).toLocaleString()}</td><td>${delta}</td><td class="score good">${Number(s.quality||0).toFixed(1)}</td><td class="score">${Number(score||0).toFixed(1)}</td><td class="desc">${esc(p.description)}</td></tr>`}).join('');empty.hidden=data.length>0}
[search,catalog,language,type,sort].forEach(el=>el.addEventListener('input',render));render();
</script></body></html>"""
    return (
        template.replace("__GENERATED__", html_lib.escape(generated_at))
        .replace("__PROJECTS__", project_payload)
        .replace("__CATALOGS__", catalog_payload)
        .replace("__AGGREGATE__", json.dumps(aggregate_id))
    )


def previous_publication(output_dir: Path) -> tuple[int, dict[str, int]]:
    """Return the last healthy total and per-catalog counts, when readable."""
    path = output_dir / "latest.json"
    if not path.exists():
        return 0, {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0, {}
    if not isinstance(payload, dict):
        return 0, {}
    catalogs = {
        str(item.get("id")): int(item.get("count") or 0)
        for item in payload.get("catalogs", [])
        if isinstance(item, dict) and item.get("id")
    }
    return int(payload.get("count") or 0), catalogs


def previous_count(output_dir: Path) -> int:
    """Compatibility helper used by tests and external callers."""
    return previous_publication(output_dir)[0]


def validate_collection(
    projects: list[Project],
    config: dict[str, Any],
    source_health: list[dict[str, Any]],
    *,
    previous: int = 0,
    previous_catalogs: Optional[dict[str, int]] = None,
    allow_shrink: bool = False,
) -> None:
    if not projects:
        raise ValueError("no projects were collected")
    ids = [project.id for project in projects]
    names = [project.full_name.lower() for project in projects]
    if len(ids) != len(set(ids)) or len(names) != len(set(names)):
        raise ValueError("project ids and repository names must be unique")
    if len(projects) < int(config["minimum_total_projects"]):
        raise ValueError(
            f"collected {len(projects)} projects, below minimum_total_projects={config['minimum_total_projects']}"
        )
    if previous and not allow_shrink:
        minimum = math.floor(previous * float(config["minimum_previous_ratio"]))
        if len(projects) < minimum:
            raise ValueError(
                f"collection shrank from {previous} to {len(projects)}, below guarded minimum {minimum}"
            )
    aggregate_id = str(config["aggregate_catalog_id"])
    configured = [
        str(item["id"])
        for item in config["catalogs"]
        if isinstance(item, dict) and item.get("id") != aggregate_id
    ]
    successes = {
        str(item.get("catalog"))
        for item in source_health
        if item.get("ok") and item.get("mode") in {"active", "new", "custom"}
    }
    missing_sources = [catalog_id for catalog_id in configured if catalog_id not in successes]
    if missing_sources:
        raise ValueError(f"no successful discovery query for catalogs: {', '.join(missing_sources)}")
    catalog_counts = {
        catalog_id: sum(catalog_id in project.catalogs for project in projects)
        for catalog_id in configured
    }
    minimums = {
        str(item["id"]): int(item.get("minimum_items", 1))
        for item in config["catalogs"]
        if isinstance(item, dict) and item.get("id") != aggregate_id
    }
    if previous_catalogs and not allow_shrink:
        configured_map = catalog_map(config)
        collapsed: list[str] = []
        for catalog_id, current in catalog_counts.items():
            old = int(previous_catalogs.get(catalog_id, 0))
            if old <= 0:
                continue
            catalog = configured_map[catalog_id]
            ratio = float(
                catalog.get(
                    "minimum_previous_ratio",
                    config["minimum_previous_catalog_ratio"],
                )
            )
            guarded_minimum = max(minimums[catalog_id], math.floor(old * ratio))
            if current < guarded_minimum:
                collapsed.append(f"{catalog_id}={current}<{guarded_minimum} (previous {old})")
        if collapsed:
            raise ValueError("catalog shrink guards failed: " + ", ".join(collapsed))
    too_small = [
        f"{catalog_id}={count}<{minimums[catalog_id]}"
        for catalog_id, count in catalog_counts.items()
        if count < minimums[catalog_id]
    ]
    if too_small:
        raise ValueError("catalog minimums failed: " + ", ".join(too_small))


def write_outputs(
    projects: list[Project],
    config: dict[str, Any],
    history: dict[str, Any],
    source_health: list[dict[str, Any]],
    now: datetime,
    *,
    output_dir: Path,
    site_dir: Path,
) -> dict[str, int]:
    generated_at = now.replace(microsecond=0).isoformat()
    catalogs = [item for item in config["catalogs"] if isinstance(item, dict)]
    counts: dict[str, int] = {}
    catalog_summaries: list[dict[str, Any]] = []
    index_lines = [
        "# GitHub Project Radars",
        "",
        f"_Generated {generated_at}._",
        "",
        "One read-only engine publishes domain-specific catalogs of high-quality, high-momentum, up-and-coming, and interesting GitHub projects.",
        "",
        "| Catalog | Projects | Description |",
        "|:--------|---------:|:------------|",
    ]
    board_payloads: dict[str, dict[str, list[str]]] = {}
    for catalog in catalogs:
        catalog_id = str(catalog["id"])
        members = [project for project in projects if catalog_id in project.catalogs]
        boards = catalog_leaderboards(projects, catalog, config, now)
        counts[catalog_id] = len(members)
        board_ids = {key: [project.id for project in values] for key, values in boards.items()}
        board_payloads[catalog_id] = board_ids
        atomic_write(
            output_dir / f"{catalog_id}.md",
            render_catalog_markdown(catalog, boards, generated_at, len(members), now),
        )
        compact = {
            "schema_version": PUBLICATION_SCHEMA,
            "generated_at": generated_at,
            "catalog": catalog,
            "count": len(members),
            "project_ids": [project.id for project in members],
            "leaderboards": board_ids,
        }
        atomic_write(
            output_dir / f"{catalog_id}.json",
            json.dumps(compact, indent=2, ensure_ascii=False) + "\n",
        )
        catalog_summaries.append(
            {
                "id": catalog_id,
                "title": catalog.get("title", catalog_id),
                "description": catalog.get("description", ""),
                "count": len(members),
            }
        )
        index_lines.append(
            f"| [{markdown_escape(catalog.get('title') or catalog_id)}]({catalog_id}.md) | {len(members):,} | {markdown_escape(catalog.get('description') or '')} |"
        )

    successful = sum(bool(item.get("ok")) for item in source_health)
    failed = len(source_health) - successful
    payload = {
        "schema_version": PUBLICATION_SCHEMA,
        "generated_at": generated_at,
        "count": len(projects),
        "history_mode": "observed-history" if any(project.growth.get("signal_source") == "observed-history" for project in projects) else "lifetime-estimate",
        "catalogs": catalog_summaries,
        "leaderboards": board_payloads,
        "source_health": source_health,
        "projects": [project.to_dict() for project in projects],
    }
    status = {
        "ok": True,
        "schema_version": PUBLICATION_SCHEMA,
        "generated_at": generated_at,
        "projects": len(projects),
        "catalogs": counts,
        "source_health": {
            "total": len(source_health),
            "successful": successful,
            "failed": failed,
            "degraded": failed > 0,
        },
        "history_mode": payload["history_mode"],
    }
    atomic_write(output_dir / "README.md", "\n".join(index_lines) + "\n")
    atomic_write(output_dir / "latest.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    atomic_write(output_dir / "history.json", json.dumps(history, indent=2, sort_keys=True) + "\n")
    atomic_write(output_dir / "status.json", json.dumps(status, indent=2) + "\n")
    atomic_write(
        site_dir / "index.html",
        render_html(projects, catalogs, str(config["aggregate_catalog_id"]), generated_at),
    )
    atomic_write(site_dir / "latest.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return counts
