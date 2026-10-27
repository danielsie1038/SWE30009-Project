import json
import os
import platform
from datetime import datetime, timezone
from html import escape
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results.json"
REPORT_FILE = BASE_DIR / "report.html"
COLORS = {"PASS": "#1a7f4b", "FAIL": "#c62828", "ERROR": "#b45309"}

CSS = """
body{font-family:"Segoe UI",Roboto,Arial,sans-serif;margin:0;background:#f4f6f3;color:#17232b;line-height:1.5}
header{background:#17232b;color:#fff;padding:24px 32px}
header h1{margin:0 0 4px;font-size:1.6rem}
header p{margin:0;color:#b9c6cc;font-size:.95rem}
main{max-width:1000px;margin:0 auto;padding:24px}
section{background:#fff;border:1px solid #d9dfdb;border-radius:10px;padding:20px 24px;margin-bottom:20px}
h2{margin:0 0 14px;font-size:1.1rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.card{border:1px solid #d9dfdb;border-radius:8px;padding:12px 14px}
.card b{display:block;font-size:1.6rem}
.card span{color:#5d6b73;font-size:.85rem}
.bar{display:flex;height:18px;border-radius:9px;overflow:hidden;margin-top:16px;background:#e5e9e6}
table{width:100%;border-collapse:collapse;font-size:.92rem}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #e5e9e6;vertical-align:top}
th{color:#5d6b73;font-size:.82rem}
.badge{color:#fff;border-radius:4px;padding:2px 8px;font-weight:600;font-size:.82rem}
.fail-item{border-left:4px solid #c62828;background:#fbeceb;padding:10px 14px;margin-bottom:10px;border-radius:4px}
.ok{border-left:4px solid #1a7f4b;background:#e8f5ee;padding:10px 14px;border-radius:4px}
.chart{overflow-x:auto}
a{color:#0f6b62}
"""


def load_results():
    if not RESULTS_FILE.exists():
        return []
    return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))


def failure_reason(r):
    if r["status"] == "ERROR":
        return f"The test could not finish: {r['actual']}"
    return f"Expected {r['expected']} but the page showed: {r['actual']}"


def time_chart(results):
    """Horizontal SVG bar chart of execution time, coloured by status."""
    longest = max(r["duration_s"] for r in results) or 1
    row_h, left, width = 28, 70, 560
    svg = [f'<svg viewBox="0 0 {left + width + 80} {row_h * len(results) + 8}" '
           'width="100%" role="img" aria-label="Execution time per test case">']
    for i, r in enumerate(results):
        y = i * row_h + 4
        w = max(2, r["duration_s"] / longest * width)
        svg.append(f'<text x="{left - 8}" y="{y + 16}" text-anchor="end" font-size="13" fill="#17232b">'
                   f'{escape(r["test_id"])}</text>')
        svg.append(f'<rect x="{left}" y="{y + 3}" width="{w:.1f}" height="18" rx="3" '
                   f'fill="{COLORS.get(r["status"], "#666")}"/>')
        svg.append(f'<text x="{left + w + 6:.1f}" y="{y + 16}" font-size="13" fill="#17232b">'
                   f'{r["duration_s"]}s</text>')
    svg.append("</svg>")
    return "".join(svg)


def build_html(results):
    total = len(results)
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    errors = sum(r["status"] == "ERROR" for r in results)
    total_time = round(sum(r["duration_s"] for r in results), 2)
    avg_time = round(total_time / total, 2) if total else 0
    rate = round(100 * passed / total) if total else 0

    runner = os.getenv("RUNNER_OS") or platform.system()
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_id = os.getenv("GITHUB_RUN_ID")
    run_info = f" | GitHub run #{escape(run_id)}" if run_id else " | local run"

    segments = "".join(
        f'<div style="width:{100 * n / total:.1f}%;background:{COLORS[s]}" title="{s}: {n}"></div>'
        for s, n in (("PASS", passed), ("FAIL", failed), ("ERROR", errors)) if n and total)

    bad = [r for r in results if r["status"] != "PASS"]
    if bad:
        failures = "".join(
            f'<div class="fail-item"><b>{escape(r["test_id"])}</b> - {escape(r["description"])}<br>'
            f'{escape(failure_reason(r))}</div>' for r in bad)
    else:
        failures = '<div class="ok">All test cases passed. No failures to report.</div>'

    rows = "".join(
        f'<tr><td>{escape(r["test_id"])}</td><td>{escape(r["description"])}</td>'
        f'<td><span class="badge" style="background:{COLORS.get(r["status"], "#666")}">{r["status"]}</span></td>'
        f'<td>{escape(str(r["expected"]))}</td><td>{escape(str(r["actual"]))}</td>'
        f'<td>{r["duration_s"]}s</td>'
        f'<td><a href="screenshots/{escape(r["screenshot"])}">view</a></td></tr>' for r in results)

    cards = (f'<div class="card"><b>{total}</b><span>Total tests</span></div>'
             f'<div class="card"><b style="color:{COLORS["PASS"]}">{passed}</b><span>Passed</span></div>'
             f'<div class="card"><b style="color:{COLORS["FAIL"]}">{failed + errors}</b><span>Failed / errors</span></div>'
             f'<div class="card"><b>{rate}%</b><span>Pass rate</span></div>'
             f'<div class="card"><b>{total_time}s</b><span>Total execution time</span></div>'
             f'<div class="card"><b>{avg_time}s</b><span>Average per test</span></div>')

    body = (f'<section><h2>Summary</h2><div class="cards">{cards}</div>'
            f'<div class="bar" aria-label="Pass/fail proportion">{segments}</div></section>'
            f'<section><h2>Failed test cases</h2>{failures}</section>'
            f'<section><h2>Execution time per test case</h2><div class="chart">'
            f'{time_chart(results) if results else "<p>No results available.</p>"}</div></section>'
            f'<section><h2>All test cases</h2><table><thead><tr><th>ID</th><th>Description</th>'
            f'<th>Status</th><th>Expected</th><th>Actual</th><th>Time</th><th>Screenshot</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></section>')

    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>AI Gateway Test Report</title><style>{CSS}</style></head><body>'
            f'<header><h1>AI Gateway Dashboard - Test Report</h1>'
            f'<p>Runner: {escape(runner)} | Python {platform.python_version()} | {when}{run_info}</p></header>'
            f'<main>{body}</main></body></html>')


def write_job_summary(results):
    """Shows a short table on the GitHub run page (no download needed)."""
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if not path:
        return
    passed = sum(r["status"] == "PASS" for r in results)
    lines = [f"## Test results: {passed}/{len(results)} passed", "",
             "| ID | Status | Time |", "|---|---|---|"]
    lines += [f"| {r['test_id']} | {r['status']} | {r['duration_s']}s |" for r in results]
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    data = load_results()
    REPORT_FILE.write_text(build_html(data), encoding="utf-8")
    write_job_summary(data)
    print(f"Report written to {REPORT_FILE.name} ({len(data)} results)")
