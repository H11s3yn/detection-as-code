"""
Detection-as-Code hesabatı.

Yaradır:
  reports/index.html           — ATT&CK coverage, test nəticələri, son dəyişikliklər
  reports/navigator-layer.json — MITRE ATT&CK Navigator üçün layer

Mənbələr:
  rules/**/*.yml               — qaydaların tags sahəsi (attack.<tactic>, attack.tXXXX)
  build/test-results.json      — scripts/run_tests.py-nin nəticəsi (yoxdursa, bölmə boş qalır)
  git log                      — rules/ və tests/ üzrə son dəyişikliklər

İstifadə:  python scripts/report.py
"""
import html
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

RULES_DIR = Path("rules")
RESULTS = Path("build") / "test-results.json"
OUT_DIR = Path("reports")

TECH_RE = re.compile(r"^attack\.t\d{4}(\.\d{3})?$")


def esc(s):
    return html.escape(str(s))


def load_rules():
    rules = []
    for p in sorted(RULES_DIR.rglob("*.yml")):
        r = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(r, dict) or r.get("status") == "deprecated":
            continue
        tags = r.get("tags") or []
        tactics = [t.split(".", 1)[1] for t in tags if t.startswith("attack.") and not TECH_RE.match(t)]
        techniques = [t.split(".", 1)[1].upper() for t in tags if TECH_RE.match(t)]
        rules.append({
            "file": p.stem, "id": r.get("id"), "title": r.get("title", p.stem),
            "level": r.get("level", ""), "status": r.get("status", ""),
            "tactics": tactics, "techniques": techniques,
        })
    return rules


def load_results():
    if not RESULTS.exists():
        return None
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def git_log():
    """Son 20 dəyişiklik. Eyni email = eyni müəllif (məs. '2maahir3' və 'Mahir Ağayev')."""
    try:
        out = subprocess.run(
            ["git", "log", "-n", "20", "--date=short",
             "--pretty=format:%h|%ae|%an|%ad|%s", "--no-merges", "--", "rules/", "tests/"],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    rows = [line.split("|", 4) for line in out.splitlines() if line.count("|") >= 4]
    # hər email üçün ən uzun adı göstər (adətən tam ad)
    names = {}
    for _, email, name, _, _ in rows:
        if len(name) > len(names.get(email, "")):
            names[email] = name
    return [{"commit": c, "author": names[e], "date": d, "msg": m.strip()} for c, e, _, d, m in rows]


def build_html(rules, results, log):
    by_tactic = defaultdict(list)
    for r in rules:
        for t in r["tactics"] or ["(tactic yoxdur)"]:
            by_tactic[t].append(r)
    techniques = sorted({t for r in rules for t in r["techniques"]})

    # 1. Coverage
    cov_rows = "".join(
        f"<tr><td>{esc(t)}</td><td class=num>{len(rs)}</td>"
        f"<td>{esc(', '.join(sorted({x for r in rs for x in r['techniques']})))}</td></tr>"
        for t, rs in sorted(by_tactic.items()))

    # 2. Testlər
    if results is None:
        test_summary = "<p class=muted>build/test-results.json tapılmadı — əvvəl <code>python scripts/run_tests.py</code> işlət.</p>"
        test_rows = ""
    else:
        passed = sum(1 for x in results if x.get("passed"))
        pct = round(100 * passed / len(results)) if results else 0
        state = "ok" if passed == len(results) else "bad"
        test_summary = f"<p class='big {state}'>{passed}/{len(results)} test keçdi ({pct}%)</p>"
        per_rule = defaultdict(dict)
        for x in results:
            per_rule[x["rule"]][x["test"]] = x
        def cell(x):
            if not x:
                return "<td class=bad>yoxdur</td>"
            mark = "✅" if x.get("passed") else "❌"
            return f"<td>{mark} {esc(x.get('hits'))}</td>"
        test_rows = "".join(
            f"<tr><td>{esc(name)}</td>{cell(t.get('positive'))}{cell(t.get('negative'))}</tr>"
            for name, t in sorted(per_rule.items()))
        test_rows = ("<table><tr><th>Qayda</th><th>Positive (nəticə)</th><th>Negative (nəticə)</th></tr>"
                     + test_rows + "</table>")

    # 3. Qaydalar
    rule_rows = "".join(
        f"<tr><td>{esc(r['title'])}</td><td>{esc(', '.join(r['techniques']))}</td>"
        f"<td>{esc(r['level'])}</td><td>{esc(r['status'])}</td></tr>" for r in rules)

    # 4. Dəyişikliklər
    log_rows = "".join(
        f"<tr><td><code>{esc(x['commit'])}</code></td><td>{esc(x['date'])}</td>"
        f"<td>{esc(x['author'])}</td><td>{esc(x['msg'])}</td></tr>" for x in log)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="az"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Detection-as-Code hesabatı</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:960px;margin:0 auto;padding:16px;color:#1f2328;background:#fff}}
h1{{font-size:1.6rem}} h2{{margin-top:2rem;border-bottom:1px solid #d0d7de;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}
th,td{{border:1px solid #d0d7de;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#f6f8fa}} .num{{text-align:right}} .muted{{color:#656d76}}
.big{{font-size:1.4rem;font-weight:600}} .ok{{color:#1a7f37}} .bad{{color:#cf222e}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}} .card{{border:1px solid #d0d7de;border-radius:8px;padding:12px 16px;min-width:140px}}
.card b{{display:block;font-size:1.6rem}}
</style></head><body>
<h1>Detection-as-Code hesabatı</h1>
<p class=muted>Yaradılıb: {now}</p>
<div class=cards>
  <div class=card><b>{len(rules)}</b>qayda</div>
  <div class=card><b>{len([t for t in by_tactic if not t.startswith('(')])}</b>tactic</div>
  <div class=card><b>{len(techniques)}</b>technique</div>
</div>

<h2>1. ATT&amp;CK coverage</h2>
<table><tr><th>Tactic</th><th class=num>Qayda</th><th>Technique-lər</th></tr>{cov_rows}</table>

<h2>2. Test nəticələri</h2>
{test_summary}
{test_rows}

<h2>3. Qaydalar</h2>
<table><tr><th>Ad</th><th>Technique</th><th>Level</th><th>Status</th></tr>{rule_rows}</table>

<h2>4. Son dəyişikliklər (rules/, tests/)</h2>
<table><tr><th>Commit</th><th>Tarix</th><th>Müəllif</th><th>Mesaj</th></tr>{log_rows}</table>
</body></html>
"""


def build_layer(rules):
    tech = defaultdict(list)
    for r in rules:
        for t in r["techniques"]:
            tech[t].append(r["file"])
    return {
        "name": "Detection-as-Code coverage",
        "versions": {"layer": "4.5"},
        "domain": "enterprise-attack",
        "description": f"{len(rules)} Sigma qaydası",
        "gradient": {"colors": ["#ffffff", "#66b1ff"], "minValue": 0, "maxValue": 2},
        "techniques": [
            {"techniqueID": t, "score": len(files), "comment": ", ".join(files)}
            for t, files in sorted(tech.items())
        ],
    }


def main():
    rules = load_rules()
    results = load_results()
    log = git_log()
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(build_html(rules, results, log), encoding="utf-8")
    (OUT_DIR / "navigator-layer.json").write_text(
        json.dumps(build_layer(rules), indent=2, ensure_ascii=False), encoding="utf-8")
    tests = "yoxdur" if results is None else f"{sum(x['passed'] for x in results)}/{len(results)}"
    print(f"hesabat: {OUT_DIR / 'index.html'}  |  {len(rules)} qayda, testlər: {tests}")
    print(f"navigator: {OUT_DIR / 'navigator-layer.json'}")


if __name__ == "__main__":
    main()
