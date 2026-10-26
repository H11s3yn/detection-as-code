"""
Sigma qaydalarını Kibana detection qaydalarına çevirir.

İstifadə:  python scripts/convert.py
Nəticə:    build/rules.ndjson  (deploy.py bu faylı Kibana-ya yükləyir)
"""
import json
from pathlib import Path

import yaml
from sigma.collection import SigmaCollection
from sigma.backends.elasticsearch import LuceneBackend
from sigma.pipelines.elasticsearch.windows import ecs_windows

# Sigma sahə adlarını Elastic (ECS) adlarına çevirən pipeline + Lucene dili
BACKEND = LuceneBackend(processing_pipeline=ecs_windows())

# Sigma "level" → Kibana "risk_score" (Elastic-in öz qaydalarındakı standart)
RISK = {"informational": 1, "low": 21, "medium": 47, "high": 73, "critical": 99}

# Qaydalar bu indekslərdə axtarış edəcək (Winlogbeat logları)
INDEX = ["winlogbeat-*"]

RULES_DIR = Path("rules")
OUT_FILE = Path("build") / "rules.ndjson"


def load(path):
    """YAML qayda faylını Python lüğətinə (dict) çevirir."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def to_query(path):
    """Sigma qaydası → Lucene sorğusu. Mahir (testlər) və Elmir (CI) də istifadə edir."""
    text = Path(path).read_text(encoding="utf-8")
    return BACKEND.convert(SigmaCollection.from_yaml(text))[0]


def to_kibana_rule(path):
    """Sigma qaydası → Kibana detection qaydası (JSON)."""
    m = load(path)
    level = m["level"]
    return {
        "rule_id": m["id"],  # Sigma ID = Kibana ID → deploy təkrarlananda dublikat olmur
        "name": m["title"],
        "description": m["description"],
        "severity": "low" if level == "informational" else level,
        "risk_score": RISK[level],
        "type": "query",
        "language": "lucene",
        "query": to_query(path),
        "index": INDEX,
        "interval": "5m",   # qayda 5 dəqiqədən bir işləyir
        "from": "now-6m",   # son 6 dəqiqəyə baxır (1 dəq üst-üstə düşmə)
        "enabled": m["status"] in ("test", "stable"),  # experimental → söndürülmüş
        "tags": ["detection-as-code"] + m.get("tags", []),
        "false_positives": m.get("falsepositives", []),
        "author": [m.get("author", "")],
        "references": m.get("references", []),
    }


def main():
    OUT_FILE.parent.mkdir(exist_ok=True)
    rules = []
    for path in sorted(RULES_DIR.rglob("*.yml")):
        if load(path)["status"] == "deprecated":
            print(f"atlandı (deprecated): {path}")
            continue
        rule = to_kibana_rule(path)
        rules.append(rule)
        print(f"çevrildi: {path}")
        print(f"   sorğu: {rule['query']}")

    OUT_FILE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rules) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(rules)} qayda → {OUT_FILE}")


if __name__ == "__main__":
    main()