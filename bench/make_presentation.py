#!/usr/bin/env python3
"""
Build a self-contained HTML presentation of the results (all plots inlined as
data URIs, so the file opens offline in any browser). Regenerate after re-running
the plots:  python bench/make_presentation.py  ->  report/presentation.html
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "results" / "figures"
OUT = ROOT / "report" / "presentation.html"


def data_uri(name):
    p = FIGS / name
    if not p.exists():
        return ""
    mt = "image/svg+xml" if name.endswith(".svg") else "image/png"
    return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()


CSS = r"""
<style>
:root{
  --ground:#f7f9fb; --surface:#ffffff; --frame:#ffffff;
  --text:#0f1b2d; --muted:#51617a; --border:#e3e9f0; --border-strong:#cfd8e3;
  --accent:#0d7d74; --accent-weak:#d6f2ee;
  --serial:#d13b3b; --p1:#2f74c0; --p2:#2f9256;
  --shadow:0 1px 2px rgba(16,27,45,.05),0 8px 24px rgba(16,27,45,.06);
  --maxw:940px;
}
@media (prefers-color-scheme:dark){
  :root{
    --ground:#0a1120; --surface:#111a2c; --frame:#f7f9fb;
    --text:#e6edf6; --muted:#93a3ba; --border:#1d2942; --border-strong:#2a3a58;
    --accent:#2dd4bf; --accent-weak:#0f3d3a;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
  }
}
:root[data-theme="light"]{
  --ground:#f7f9fb; --surface:#ffffff; --frame:#ffffff;
  --text:#0f1b2d; --muted:#51617a; --border:#e3e9f0; --border-strong:#cfd8e3;
  --accent:#0d7d74; --accent-weak:#d6f2ee; --shadow:0 1px 2px rgba(16,27,45,.05),0 8px 24px rgba(16,27,45,.06);
}
:root[data-theme="dark"]{
  --ground:#0a1120; --surface:#111a2c; --frame:#f7f9fb;
  --text:#e6edf6; --muted:#93a3ba; --border:#1d2942; --border-strong:#2a3a58;
  --accent:#2dd4bf; --accent-weak:#0f3d3a; --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--text);
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.6;-webkit-font-smoothing:antialiased;}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 20px 72px;}
code,.mono,.num{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums;}

/* header */
header{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--ground) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--border);}
.head{max-width:var(--maxw);margin:0 auto;padding:14px 20px;display:flex;flex-wrap:wrap;
  align-items:center;gap:10px 18px;}
.head h1{font-size:15px;margin:0;font-weight:650;letter-spacing:-.01em;}
.head .sub{color:var(--muted);font-size:12.5px;margin-right:auto;}
.legend{display:flex;gap:14px;font-size:12.5px;color:var(--muted);}
.legend span{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;}

/* hero */
.hero{padding:52px 0 28px;}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:650;}
.hero h2{font-size:clamp(28px,4.5vw,42px);line-height:1.08;margin:.35em 0 .3em;letter-spacing:-.02em;
  text-wrap:balance;font-weight:720;}
.hero p{font-size:17px;color:var(--muted);max-width:64ch;margin:0;}

/* stat row */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:30px 0 8px;}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px 16px 14px;box-shadow:var(--shadow);}
.stat .v{font-size:26px;font-weight:720;letter-spacing:-.02em;}
.stat .k{font-size:12.5px;color:var(--muted);margin-top:3px;}
.stat.accent .v{color:var(--accent);}

/* setup note */
.note{border:1px solid var(--border);border-left:3px solid var(--accent);background:var(--surface);
  border-radius:10px;padding:13px 16px;font-size:13.5px;color:var(--muted);margin:26px 0;}
.note b{color:var(--text);}

/* sections */
section.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;
  padding:26px 26px 24px;margin:22px 0;box-shadow:var(--shadow);}
.card .eyebrow{font-size:11.5px;}
.card h3{font-size:21px;margin:.3em 0 .5em;letter-spacing:-.01em;font-weight:680;text-wrap:balance;}
.card .lead{color:var(--muted);margin:0 0 18px;font-size:14.5px;max-width:70ch;}
.frame{background:var(--frame);border:1px solid var(--border-strong);border-radius:12px;padding:12px;
  overflow-x:auto;}
.frame img{display:block;width:100%;height:auto;border-radius:6px;}
.grid{display:grid;grid-template-columns:1.35fr 1fr;gap:22px;align-items:start;}
@media(max-width:760px){.grid{grid-template-columns:1fr;}.stats{grid-template-columns:repeat(2,1fr);}}

/* tables */
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:2px 0 0;}
caption{caption-side:top;text-align:left;font-size:12px;color:var(--muted);padding-bottom:8px;}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--border);}
th:first-child,td:first-child{text-align:left;}
thead th{color:var(--muted);font-weight:600;font-size:11.5px;letter-spacing:.03em;text-transform:uppercase;border-bottom:1px solid var(--border-strong);}
tbody td{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums;}
tbody tr:last-child td{border-bottom:none;}
.best{color:var(--accent);font-weight:700;}
.s-serial{color:var(--serial);} .s-p1{color:var(--p1);} .s-p2{color:var(--p2);}

/* takeaway */
.takeaway{margin-top:18px;border-radius:10px;background:var(--accent-weak);
  border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);padding:13px 16px;font-size:14px;}
.takeaway b{color:var(--text);}
.takeaway .lbl{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700;display:block;margin-bottom:3px;}
@media (prefers-color-scheme:dark){ .takeaway{color:var(--text);} }

footer{margin-top:34px;padding-top:22px;border-top:1px solid var(--border);color:var(--muted);font-size:13px;}
footer a{color:var(--accent);}
a{color:var(--accent);}
@media (prefers-reduced-motion:no-preference){
  section.card,.stat{animation:rise .5s cubic-bezier(.2,.7,.2,1) both;}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
}
</style>
"""


def section(eyebrow, title, lead, img_name, table_html, takeaway_html, dark_frame=False):
    uri = data_uri(img_name)
    frame_style = ' style="background:#0b0e14"' if dark_frame else ""
    return f"""
<section class="card">
  <div class="eyebrow">{eyebrow}</div>
  <h3>{title}</h3>
  <p class="lead">{lead}</p>
  <div class="grid">
    <div class="frame"{frame_style}><img alt="{title}" src="{uri}"></div>
    <div>{table_html}</div>
  </div>
  <div class="takeaway"><span class="lbl">Takeaway</span>{takeaway_html}</div>
</section>"""


speedup_tbl = """
<table><caption>Equal work, uniform-500, R=8 (serial baseline 4.44 s)</caption>
<thead><tr><th>threads</th><th class="s-p1">P1 speedup</th><th class="s-p2">P2 speedup</th></tr></thead>
<tbody>
<tr><td>2</td><td>1.80×</td><td>1.75×</td></tr>
<tr><td>4</td><td>2.17×</td><td>2.14×</td></tr>
<tr><td>6</td><td>2.29×</td><td class="best">2.43×</td></tr>
<tr><td>8</td><td class="best">2.52×</td><td>2.30×</td></tr>
</tbody></table>"""

eff_tbl = """
<table><caption>Parallel efficiency = speedup ÷ threads</caption>
<thead><tr><th>threads</th><th class="s-p1">P1</th><th class="s-p2">P2</th></tr></thead>
<tbody>
<tr><td>2</td><td class="best">0.90</td><td>0.87</td></tr>
<tr><td>4</td><td>0.54</td><td>0.53</td></tr>
<tr><td>6</td><td>0.38</td><td>0.40</td></tr>
<tr><td>8</td><td>0.31</td><td>0.29</td></tr>
</tbody></table>"""

quality_tbl = """
<table><caption>Gap to optimum at equal work (serial = 9.35%)</caption>
<thead><tr><th>threads</th><th class="s-p1">P1 gap</th><th class="s-p2">P2 gap</th></tr></thead>
<tbody>
<tr><td>2</td><td>6.35%</td><td>7.11%</td></tr>
<tr><td>4</td><td class="best">5.98%</td><td>6.53%</td></tr>
<tr><td>6</td><td>6.65%</td><td>6.30%</td></tr>
<tr><td>8</td><td>6.83%</td><td>6.45%</td></tr>
</tbody></table>"""

conv_tbl = """
<table><caption>Final gap after a 3 s budget (mean of 8 seeds)</caption>
<thead><tr><th>approach</th><th>final gap</th><th>best</th></tr></thead>
<tbody>
<tr><td class="s-serial">Serial</td><td>9.94%</td><td>6.51%</td></tr>
<tr><td class="s-p1">P1 fixed</td><td class="best">6.03%</td><td>2.74%</td></tr>
<tr><td class="s-p2">P2 DTAM</td><td>6.11%</td><td>4.03%</td></tr>
</tbody></table>"""

policy_tbl = """
<table><caption>Mean tour length; % vs serial and P2 vs P1</caption>
<thead><tr><th>landscape</th><th>parallel<br>vs serial</th><th>P2<br>vs P1</th></tr></thead>
<tbody>
<tr><td>uniform, no 2-opt</td><td class="best">−67.4%</td><td>+1.9%</td></tr>
<tr><td>clustered, no 2-opt</td><td class="best">−60.7%</td><td>+1.7%</td></tr>
<tr><td>clustered, 2-opt</td><td>−1.4%</td><td>+0.1%</td></tr>
</tbody></table>"""

div_note = """
<table><caption>Population diversity (mean edge distance)</caption>
<thead><tr><th>approach</th><th>trend</th></tr></thead>
<tbody>
<tr><td class="s-serial">Serial</td><td>stays higher*</td></tr>
<tr><td class="s-p1">P1 fixed</td><td>→ 0</td></tr>
<tr><td class="s-p2">P2 DTAM</td><td>→ 0 (overlaps P1)</td></tr>
</tbody></table>
<p style="font-size:12px;color:var(--muted);margin:10px 2px 0">*single large population over
fewer generations — not a like-for-like comparison with the 30-individual islands.</p>"""

sections = [
    section("01 · Validation", "The engine is correct",
            "On the <code>circle</code> instance the optimal tour length is known exactly; all three "
            "engines reach it (gap = 0.00%). Below is a real optimized route on 300 clustered cities — "
            "the tour enters each cluster, optimizes locally, and links clusters efficiently.",
            "route_clustered300.svg",
            '<table><caption>Correctness</caption><thead><tr><th>approach</th><th>circle gap</th></tr></thead>'
            '<tbody><tr><td class="s-serial">Serial</td><td class="best">0.00%</td></tr>'
            '<tr><td class="s-p1">P1</td><td class="best">0.00%</td></tr>'
            '<tr><td class="s-p2">P2</td><td class="best">0.00%</td></tr></tbody></table>',
            "The GA operators, distance metric, and parallel bookkeeping are all verified against a "
            "known optimum before we trust any benchmark number.",
            dark_frame=True),
    section("02 · Speed", "Speedup vs threads",
            "Wall-clock speedup at identical total work. Both parallel engines scale together and peak "
            "around 2.3–2.5×; the dashed line is ideal linear scaling.",
            "speedup_uniform500.png", speedup_tbl,
            "Real, repeatable speedup — but <b>sublinear</b>. The gap to ideal is explained next."),
    section("03 · Scaling", "Parallel efficiency",
            "Efficiency (speedup ÷ threads) shows how much of each added core we actually use.",
            "efficiency_uniform500.png", eff_tbl,
            "≈<b>90% at 2 threads</b>, falling to ~30% at 8. This M3 has 4 performance + 4 efficiency "
            "cores, so threads past ~4 recruit slower cores that lag at each barrier — Amdahl's law plus "
            "hardware. A homogeneous i5 should hold efficiency better through its physical cores."),
    section("04 · Quality", "Solution quality at equal work",
            "For the same computation, how good is the tour? Lower gap is better; the serial baseline "
            "is 9.35%.",
            "quality_uniform500.png", quality_tbl,
            "The island <b>structure</b> itself improves quality (≈6% vs serial's 9.35%), not just "
            "speed. P1 and P2 trade the lead and stay within ~1% of each other in tour length."),
    section("05 · Quality vs time", "Better tours in the same wall-clock",
            "Everyone gets the same 3-second budget; the curve is best-tour gap over time.",
            "convergence.png", conv_tbl,
            "In equal wall-clock the parallel engines reach <b>~4 percentage points less gap</b> than "
            "serial. P1 and P2 track each other throughout."),
    section("06 · Dynamics", "Population diversity over time",
            "Diversity = mean edge distance within a population. It explains the P1≈P2 result.",
            "diversity.png", div_note,
            "<b>P1 and P2 overlap</b> — DTAM's diversity-triggered pulls do not durably keep it more "
            "diverse than fixed migration on this landscape, which is exactly why their quality matches."),
    section("07 · Policy study", "When parallelism helps — and that P1 ≈ P2",
            "The same comparison across three landscape / local-search settings (8 seeds each), as a "
            "fraction of serial tour length (lower = better).",
            "policy.png", policy_tbl,
            "Two findings. <b>Without local search, islands find 60–67% shorter tours</b> in the same "
            "time; with 2-opt the gap shrinks to ~1.4% (2-opt keeps serial competitive). And <b>P2 ≈ P1 "
            "within ~2% everywhere</b> — migration policy is second-order once local search and island "
            "diversity are present."),
]

HTML = CSS + f"""
<header><div class="head">
  <h1>ParallelRoute</h1>
  <span class="sub">Serial vs P1 vs P2 — results &amp; statistics</span>
  <span class="legend">
    <span><i class="dot" style="background:var(--serial)"></i>Serial</span>
    <span><i class="dot" style="background:var(--p1)"></i>P1 island-fixed</span>
    <span><i class="dot" style="background:var(--p2)"></i>P2 island-DTAM</span>
  </span>
</div></header>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">HPC · parallel computing · Travelling-Salesman</div>
    <h2>Parallelising a route optimizer, measured three ways</h2>
    <p>An island-model genetic algorithm in C++/OpenMP. We compare a serial baseline, the textbook
    fixed-migration island model (P1), and a diversity-triggered variant we designed (P2/DTAM) — on
    speed, efficiency, and solution quality. The numbers below are reported exactly as measured.</p>
  </div>

  <div class="stats">
    <div class="stat accent"><div class="v">2.5×</div><div class="k">peak speedup (8 threads)</div></div>
    <div class="stat accent"><div class="v">6.0%</div><div class="k">gap vs serial's 9.9% (equal time)</div></div>
    <div class="stat accent"><div class="v">−67%</div><div class="k">shorter tours vs serial (no local search)</div></div>
    <div class="stat"><div class="v">&lt;1%</div><div class="k">P2 vs P1 — a statistical tie</div></div>
  </div>

  <div class="note"><b>Setup.</b> Apple M3 (4 performance + 4 efficiency cores), macOS. Instance
  uniform-500; population 240 split across islands; 400 generations (equal-work) or a 3 s budget
  (equal-time); 2-opt on unless noted; <b>R = 8 seeds</b>, means shown. Regenerate on the i5 per
  <code>HOW-TO-RUN-ON-i5.md</code>.</div>

  {''.join(sections)}

  <section class="card">
    <div class="eyebrow">Conclusion</div>
    <h3>What the statistics say</h3>
    <p class="lead" style="max-width:72ch">Parallelising the GA via the island model cuts wall-clock
    time up to ~2.5× and, at equal wall-clock, finds substantially shorter tours than the serial GA
    (dramatically so without local search). Our DTAM migration policy performs within ~1% of standard
    fixed migration across every landscape tested — neither is consistently better. With strong 2-opt
    and the diversity the island structure already provides, the migration policy is a second-order
    factor; DTAM's practical benefit is that it is self-tuning. We present these as measured rather
    than claiming an improvement the data does not support.</p>
  </section>

  <footer>
    Source, full report, and raw data:
    <a href="https://github.com/Navaneeth-H-K/parallel-route-optimizer">github.com/Navaneeth-H-K/parallel-route-optimizer</a>.
    Figures regenerated by <code>bench/plot_results.py</code>; this page by <code>bench/make_presentation.py</code>.
  </footer>
</div>
"""

OUT.write_text(HTML, encoding="utf-8")
kb = OUT.stat().st_size / 1024
print(f"wrote {OUT}  ({kb:.0f} KB)")
