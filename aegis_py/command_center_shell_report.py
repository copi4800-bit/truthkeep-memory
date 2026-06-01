from __future__ import annotations

import html
from typing import Any


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def render_command_center_shell_html(payload: dict[str, Any], *, title: str = "TruthKeep Command Center") -> str:
    result = payload["result"]
    hero = result["hero"]
    ordinary = "".join(f"<li><strong>{_escape(item.get('tool'))}</strong><span>{_escape(item.get('why'))}</span></li>" for item in result["ordinary_mode"]["actions"]) or "<li>No ordinary actions.</li>"
    workflow = "".join(f"<li><strong>{_escape(item.get('title'))}</strong><span>{_escape(item.get('summary') or item.get('tool'))}</span></li>" for item in result["workflow_loop"]["steps"]) or "<li>No workflow steps.</li>"
    timeline = "".join(f"<li>{_escape(item)}</li>" for item in result["truth_timeline"]["preview"]) or "<li>No transition preview.</li>"
    operator = "".join(f"<li>{_escape(item)}</li>" for item in result["operator_mode"]["actions"]) or "<li>No operator actions.</li>"
    commands = "".join(f"<li>{_escape(item)}</li>" for item in result["recommended_commands"])
    signals = "".join(f"<li>{_escape(item)}</li>" for item in result["deep_inspection"]["signals"])
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <style>
    :root {{ --bg:#f6efe5; --panel:rgba(255,255,255,0.94); --line:rgba(25,29,28,0.12); --ink:#191d1c; --muted:#59625d; --accent:#0f766e; --shadow:0 18px 60px rgba(25,29,28,0.12); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Aptos","Segoe UI Variable Text",sans-serif; color:var(--ink); background:linear-gradient(180deg,#fcf8f2 0%,var(--bg) 100%); }}
    main {{ max-width:1280px; margin:0 auto; padding:40px 24px 80px; }}
    .hero,.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:28px; box-shadow:var(--shadow); }}
    .hero {{ padding:32px; }}
    .kicker {{ text-transform:uppercase; letter-spacing:.16em; color:var(--accent); font-size:.75rem; font-weight:700; margin-bottom:14px; }}
    h1,h2 {{ margin:0; font-family:Georgia,serif; }}
    h1 {{ font-size:clamp(2.6rem,5vw,4.2rem); line-height:.95; max-width:9ch; }}
    .lede {{ margin-top:18px; color:var(--muted); max-width:76ch; line-height:1.72; }}
    .chips {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:20px; }}
    .chip {{ padding:10px 14px; border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,.82); color:var(--muted); }}
    .chip.accent {{ background:rgba(15,118,110,.12); color:var(--ink); font-weight:700; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px; margin-top:24px; }}
    .panel {{ padding:22px; }}
    ul {{ margin:12px 0 0; padding-left:18px; }}
    li {{ color:var(--muted); line-height:1.65; margin-bottom:10px; }}
    li strong {{ display:block; color:var(--ink); margin-bottom:4px; }}
    pre {{ margin-top:14px; white-space:pre-wrap; background:#171b19; color:#eef3ef; padding:16px; border-radius:18px; overflow:auto; font-family:"Cascadia Code",Consolas,monospace; }}
    .full {{ margin-top:20px; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="kicker">TruthKeep Command Center</div>
      <h1>{_escape(title)}</h1>
      <p class="lede">One dominant entry point that combines the daily path, current truth, correction workflow, transition history, and operator escape hatches.</p>
      <div class="chips">
        <span class="chip accent">{_escape(hero.get('readiness'))}</span>
        <span class="chip">{_escape(hero.get('health_state'))}</span>
        <span class="chip">{_escape(hero.get('truth_role'))}</span>
        <span class="chip">{_escape(hero.get('governance_status'))}</span>
      </div>
      <p class="lede">{_escape(hero.get('selected_memory'))}</p>
    </section>
    <section class="grid">
      <article class="panel"><h2>Ordinary Mode</h2><p>{_escape(result['ordinary_mode']['description'])}</p><ul>{ordinary}</ul></article>
      <article class="panel"><h2>Workflow Loop</h2><ul>{workflow}</ul></article>
      <article class="panel"><h2>Truth Timeline</h2><p>{_escape(result['truth_timeline']['story'])}</p><ul>{timeline}</ul></article>
      <article class="panel"><h2>Deep Inspection</h2><p>{_escape(result['deep_inspection']['summary'])}</p><ul>{signals}</ul></article>
      <article class="panel"><h2>Operator Mode</h2><p>{_escape(result['operator_mode']['description'])}</p><ul>{operator}</ul></article>
      <article class="panel"><h2>Recommended Commands</h2><ul>{commands}</ul></article>
    </section>
    <section class="panel full"><h2>Command Center Text</h2><pre>{_escape(payload['command_center_text'])}</pre></section>
  </main>
</body>
</html>'''
