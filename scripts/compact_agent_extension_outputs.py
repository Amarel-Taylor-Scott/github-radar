#!/usr/bin/env python3
"""Normalize Agent Extension Radar outputs for efficient daily publication.

The collector intentionally works with self-contained records because that is
simple and safe while sources are being merged. Publishing those same expanded
records in every catalog, in the aggregate feed, and inside the HTML page would
rewrite tens of megabytes every day. This post-processor converts the generated
bundle into one normalized dataset:

* repository metadata is stored once and referenced by full name;
* catalog JSON files contain metadata and leaderboard IDs, not duplicate items;
* the static page loads its adjacent JSON file instead of embedding the dataset;
* JSON is rendered one record per line for reviewable Git diffs.

It never changes the collector's in-memory model or ranking behavior.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 2


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def compact_mapping(value: dict[str, Any]) -> dict[str, Any]:
    """Remove representational noise without discarding meaningful zeroes."""
    result: dict[str, Any] = {}
    for key, item in value.items():
        if item is None or item == "" or item == [] or item == {}:
            continue
        if isinstance(item, dict):
            nested = compact_mapping(item)
            if nested:
                result[key] = nested
        else:
            result[key] = item
    return result


def render_normalized_json(payload: dict[str, Any]) -> str:
    """Render deterministic JSON with one repository/item per line."""
    scalar_keys = [
        "schema_version",
        "generated_at",
        "count",
        "catalogs",
    ]
    lines = ["{"]
    for key in scalar_keys:
        if key not in payload:
            continue
        rendered = json.dumps(payload[key], ensure_ascii=False, separators=(",", ":"))
        lines.append(f"  {json.dumps(key)}: {rendered},")

    repositories = payload.get("repositories") or {}
    lines.append('  "repositories": {')
    repository_names = sorted(repositories)
    for index, name in enumerate(repository_names):
        suffix = "," if index + 1 < len(repository_names) else ""
        rendered = json.dumps(repositories[name], ensure_ascii=False, separators=(",", ":"))
        lines.append(f"    {json.dumps(name, ensure_ascii=False)}: {rendered}{suffix}")
    lines.append("  },")

    items = payload.get("items") or []
    lines.append('  "items": [')
    for index, item in enumerate(items):
        suffix = "," if index + 1 < len(items) else ""
        rendered = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"    {rendered}{suffix}")
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def render_small_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def normalize_payload(expanded: dict[str, Any]) -> dict[str, Any]:
    items = expanded.get("items")
    if not isinstance(items, list):
        raise ValueError("latest.json does not contain an items array")

    repositories: dict[str, dict[str, Any]] = {}
    normalized_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        raw_repo = raw_item.get("repo")
        if not isinstance(raw_repo, dict):
            continue
        full_name = str(raw_repo.get("full_name") or "").strip()
        item_identifier = str(raw_item.get("id") or "").strip()
        if not full_name or not item_identifier or item_identifier in seen_ids:
            continue
        seen_ids.add(item_identifier)

        repo_record = compact_mapping(dict(raw_repo))
        repo_record.pop("full_name", None)
        existing = repositories.get(full_name)
        if existing is None or len(json.dumps(repo_record)) > len(json.dumps(existing)):
            repositories[full_name] = repo_record

        item_record = dict(raw_item)
        item_record["repo"] = full_name
        item_record = compact_mapping(item_record)
        normalized_items.append(item_record)

    normalized_items.sort(
        key=lambda item: (
            -float((item.get("scores") or {}).get("overall") or 0.0),
            str(item.get("id") or ""),
        )
    )
    catalogs = expanded.get("catalogs") if isinstance(expanded.get("catalogs"), list) else []
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": str(expanded.get("generated_at") or ""),
        "count": len(normalized_items),
        "catalogs": catalogs,
        "repositories": repositories,
        "items": normalized_items,
    }


def catalog_index(expanded: dict[str, Any], dataset_name: str = "latest.json") -> dict[str, Any]:
    catalog = expanded.get("catalog") if isinstance(expanded.get("catalog"), dict) else {}
    leaderboards = expanded.get("leaderboards") if isinstance(expanded.get("leaderboards"), dict) else {}
    cleaned_boards = {
        str(name): [str(item) for item in values if item]
        for name, values in leaderboards.items()
        if isinstance(values, list)
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": str(expanded.get("generated_at") or ""),
        "catalog": catalog,
        "count": int(expanded.get("count") or 0),
        "dataset": dataset_name,
        "filter": {"catalog_id": str(catalog.get("id") or "")},
        "leaderboards": cleaned_boards,
    }


def iter_catalog_json(feed_dir: Path) -> Iterable[Path]:
    reserved = {"latest.json", "history.json", "status.json"}
    for path in sorted(feed_dir.glob("*.json")):
        if path.name not in reserved:
            yield path


def render_html_shell() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Extension Radar</title>
<style>
:root{color-scheme:dark;--bg:#090b12;--panel:#111522;--muted:#9aa6bc;--line:#25304a;--accent:#b8c2ff;--text:#eef2ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#182044 0,transparent 34%),var(--bg);color:var(--text);font:15px/1.5 ui-sans-serif,system-ui,sans-serif}
main{max-width:1500px;margin:auto;padding:42px 24px 80px}h1{font-size:clamp(34px,5vw,66px);line-height:1;margin:0 0 14px}.lede{color:var(--muted);max-width:900px;font-size:18px}
.controls{display:grid;grid-template-columns:minmax(260px,2fr) repeat(3,minmax(160px,1fr));gap:12px;margin:30px 0 20px;position:sticky;top:0;padding:14px 0;background:linear-gradient(var(--bg) 70%,transparent);z-index:3}
input,select{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:12px;color:var(--text);padding:12px 14px;font:inherit}.stats{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.pill{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:7px 12px;color:var(--muted)}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:16px;background:rgba(17,21,34,.9)}table{border-collapse:collapse;width:100%;min-width:1050px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.07em;background:#101522;position:sticky;top:76px}tr:hover td{background:#151b2c}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}.score{font-variant-numeric:tabular-nums;font-weight:700;color:#d9deff}.desc{max-width:460px;color:var(--muted)}.tag{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 7px;margin:1px 3px 1px 0;font-size:12px;color:#c8d0e3}.empty{padding:50px;text-align:center;color:var(--muted)}.error{border-color:#6d3440;color:#ffc2ca}
@media(max-width:900px){.controls{grid-template-columns:1fr 1fr}.controls input{grid-column:1/-1}}
</style></head><body><main>
<h1>Agent Extension Radar</h1><p class="lede">Daily discovery and momentum rankings for Claude skills, Claude tools, Claude plugins, Codex skills, MCP servers, Gemini CLI extensions, and other agent ecosystems.</p>
<div class="stats"><span class="pill" id="count">Loading dataset…</span><span class="pill" id="generated"></span><span class="pill">Measured history replaces estimates automatically</span></div>
<div class="controls"><input id="search" placeholder="Search names, descriptions, repositories…"><select id="catalog"><option value="">All catalogs</option></select><select id="kind"><option value="">All kinds</option></select><select id="sort"><option value="overall">Overall</option><option value="momentum">Momentum</option><option value="rising">Rising</option><option value="popular">Popular</option><option value="stars">Stars</option></select></div>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Extension</th><th>Kind / platform</th><th>Repository</th><th>Stars</th><th>Δ7d</th><th>Score</th><th>Description</th></tr></thead><tbody id="rows"></tbody></table><div class="empty" id="empty" hidden>No matching extensions.</div></div>
</main><script>
const state={items:[],repos:{},catalogs:[]};
const search=document.querySelector('#search'),catalog=document.querySelector('#catalog'),kind=document.querySelector('#kind'),sort=document.querySelector('#sort'),rows=document.querySelector('#rows'),empty=document.querySelector('#empty'),count=document.querySelector('#count'),generated=document.querySelector('#generated');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function repoFor(i){return state.repos[i.repo]||{}}
function render(){const q=search.value.toLowerCase().trim(),cat=catalog.value,k=kind.value,key=sort.value;let data=state.items.filter(i=>(!cat||(i.catalogs||[]).includes(cat))&&(!k||i.kind===k)&&(!q||`${i.name||''} ${i.description||''} ${i.repo||''}`.toLowerCase().includes(q)));data.sort((a,b)=>key==='stars'?(repoFor(b).stars||0)-(repoFor(a).stars||0):((b.scores||{})[key]||0)-((a.scores||{})[key]||0));count.textContent=`${data.length.toLocaleString()} extensions`;rows.innerHTML=data.slice(0,500).map((i,n)=>{const r=repoFor(i),delta=(i.growth||{}).delta_7d==null?'—':`${i.growth.delta_7d>=0?'+':''}${i.growth.delta_7d}`,score=key==='stars'?(i.scores||{}).overall:(i.scores||{})[key],repoUrl=r.html_url||`https://github.com/${i.repo}`;return `<tr><td>${n+1}</td><td><a href="${esc(i.source_url||repoUrl)}"><strong>${esc(i.name)}</strong></a><br><small>${esc(i.path||'')}</small></td><td><span class="tag">${esc(i.kind)}</span><br>${(i.platforms||[]).map(p=>`<span class="tag">${esc(p)}</span>`).join('')}</td><td><a href="${esc(repoUrl)}">${esc(i.repo)}</a></td><td>${Number(r.stars||0).toLocaleString()}</td><td>${delta}</td><td class="score">${Number(score||0).toFixed(1)}</td><td class="desc">${esc(i.description||'')}</td></tr>`}).join('');empty.hidden=data.length>0}
async function boot(){try{const response=await fetch('latest.json',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);const payload=await response.json();state.items=payload.items||[];state.repos=payload.repositories||{};state.catalogs=payload.catalogs||[];catalog.insertAdjacentHTML('beforeend',state.catalogs.map(c=>`<option value="${esc(c.id)}">${esc(c.title||c.id)}</option>`).join(''));[...new Set(state.items.map(i=>i.kind))].sort().forEach(v=>kind.insertAdjacentHTML('beforeend',`<option value="${esc(v)}">${esc(v)}</option>`));generated.textContent=`Generated ${payload.generated_at||'unknown'}`;render()}catch(error){count.textContent='Dataset failed to load';count.classList.add('error');empty.hidden=false;empty.textContent=`Unable to load latest.json: ${error}`}}
[search,catalog,kind,sort].forEach(el=>el.addEventListener('input',render));boot();
</script></body></html>"""


def compact_outputs(feed_dir: Path, site_dir: Path) -> dict[str, int]:
    latest_path = feed_dir / "latest.json"
    expanded = json.loads(latest_path.read_text(encoding="utf-8"))
    normalized = normalize_payload(expanded)
    normalized_text = render_normalized_json(normalized)
    atomic_write(latest_path, normalized_text)
    atomic_write(site_dir / "latest.json", normalized_text)

    catalog_count = 0
    for path in iter_catalog_json(feed_dir):
        payload = json.loads(path.read_text(encoding="utf-8"))
        atomic_write(path, render_small_json(catalog_index(payload)))
        catalog_count += 1

    atomic_write(site_dir / "index.html", render_html_shell())

    status_path = feed_dir / "status.json"
    status: dict[str, Any] = {}
    if status_path.exists():
        parsed = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            status = parsed
    status.update(
        {
            "publication_schema": SCHEMA_VERSION,
            "normalized": True,
            "repositories": len(normalized["repositories"]),
            "catalog_indexes": catalog_count,
        }
    )
    atomic_write(status_path, render_small_json(status))
    return {
        "items": len(normalized["items"]),
        "repositories": len(normalized["repositories"]),
        "catalogs": catalog_count,
        "dataset_bytes": len(normalized_text.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed-dir", default="feeds/agent-extensions")
    parser.add_argument("--site-dir", default="docs/agent-extensions")
    args = parser.parse_args()
    stats = compact_outputs(Path(args.feed_dir), Path(args.site_dir))
    print(
        "Normalized {items} items across {repositories} repositories and {catalogs} "
        "catalog indexes ({dataset_bytes:,} bytes).".format(**stats)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
