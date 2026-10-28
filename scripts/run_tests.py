"""
Hər qayda üçün tests/<id>/positive.json və negative.json fayllarını yoxlayır.

İş prinsipi: test logunu boş indeksə yükləyir → qaydanın EQL sorğusunu
işlədir → nəticə sayını yoxlayır. Positive: >0 olmalı, negative: 0 olmalı.

İstifadə:  python scripts/run_tests.py
Mühit:     ES_URL (default http://localhost:9200), ES_USER, ES_PASS
Nəticə:    build/test-results.json; xəta varsa exit code 1
"""
import json
import os
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from convert import to_query  # Hüseynin çevirmə funksiyası

ES = os.environ.get("ES_URL", "http://localhost:9200").rstrip("/")
AUTH = (os.environ["ES_USER"], os.environ["ES_PASS"]) if os.environ.get("ES_USER") else None

# Mətn sahələri real Winlogbeat indeksindəki kimi "keyword" olsun
# (böyük/kiçik hərfə həssas) — testlər real davranışı təkrarlamalıdır.
MAPPING = {"mappings": {"dynamic_templates": [
    {"strings": {"match_mapping_type": "string", "mapping": {"type": "keyword"}}}
]}}


def count_hits(index, events, query):
    """Hadisələri təmiz indeksə yazır və EQL sorğusunun neçə nəticə tapdığını qaytarır."""
    requests.delete(f"{ES}/{index}", auth=AUTH)
    requests.put(f"{ES}/{index}", json=MAPPING, auth=AUTH).raise_for_status()
    for ev in events:
        ev.setdefault("@timestamp", "2026-01-01T00:00:00Z")  # EQL @timestamp tələb edir
        requests.post(f"{ES}/{index}/_doc", json=ev, auth=AUTH).raise_for_status()
    requests.post(f"{ES}/{index}/_refresh", auth=AUTH).raise_for_status()
    r = requests.post(f"{ES}/{index}/_eql/search", auth=AUTH,
                      json={"query": query, "size": 1000})
    r.raise_for_status()
    return len(r.json()["hits"].get("events", []))


def main():
    results = []
    for path in sorted(Path("rules").rglob("*.yml")):
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        if rule.get("status") == "deprecated":
            continue
        rid, query = rule["id"], to_query(path)
        for kind, must_hit in (("positive", True), ("negative", False)):
            test_file = Path("tests") / rid / f"{kind}.json"
            if not test_file.exists():
                print("❌", path.stem, kind, "— fayl yoxdur:", test_file)
                results.append({"rule": path.stem, "id": rid, "test": kind,
                                "hits": None, "passed": False})
                continue
            # utf-8-sig: Windows-da BOM ilə yazılmış fayllar da oxunsun
            events = json.loads(test_file.read_text(encoding="utf-8-sig"))
            n = count_hits(f"dac-test-{kind}", events, query)
            ok = (n > 0) == must_hit
            results.append({"rule": path.stem, "id": rid, "test": kind,
                            "hits": n, "passed": ok})
            print("✅" if ok else "❌", path.stem, kind, "nəticə:", n)

    for kind in ("positive", "negative"):  # müvəqqəti indeksləri təmizlə
        requests.delete(f"{ES}/dac-test-{kind}", auth=AUTH)

    Path("build").mkdir(exist_ok=True)
    Path("build/test-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} test keçdi")
    sys.exit(0 if results and passed == len(results) else 1)


if __name__ == "__main__":
    main()