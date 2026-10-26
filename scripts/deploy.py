"""
build/rules.ndjson faylındakı qaydaları Kibana-ya yükləyir.

1) Yükləmə: eyni rule_id varsa yeniləyir, yoxdursa yaradır (idempotent).
2) Sinxron: Kibana-da "detection-as-code" teqli, amma repoda olmayan qaydaları silir.

Lazımi mühit dəyişənləri: KIBANA_URL, KIBANA_USER, KIBANA_PASS
"""
import json
import os
import sys
from pathlib import Path

import requests

KIBANA = os.environ["KIBANA_URL"].rstrip("/")
AUTH = (os.environ["KIBANA_USER"], os.environ["KIBANA_PASS"])
HEADERS = {"kbn-xsrf": "true"}  # Kibana API hər dəyişiklik sorğusunda bunu tələb edir
NDJSON = Path("build") / "rules.ndjson"


def deploy():
    """Bütün qaydaları bir sorğu ilə import edir (overwrite=true → yeniləyir)."""
    r = requests.post(
        f"{KIBANA}/api/detection_engine/rules/_import",
        params={"overwrite": "true"},
        headers=HEADERS,
        auth=AUTH,
        files={"file": ("rules.ndjson", NDJSON.read_bytes())},
    )
    r.raise_for_status()
    res = r.json()
    print(f"yükləndi: {res.get('success_count')} qayda")
    if res.get("errors"):
        print("xətalar:", json.dumps(res["errors"], ensure_ascii=False, indent=2))
    if not res.get("success"):
        sys.exit(1)


def sync_deleted():
    """Repoda olmayan, amma Kibana-da qalan bizim qaydaları silir."""
    wanted = {
        json.loads(line)["rule_id"]
        for line in NDJSON.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    r = requests.get(
        f"{KIBANA}/api/detection_engine/rules/_find",
        headers=HEADERS,
        auth=AUTH,
        params={"filter": 'alert.attributes.tags:"detection-as-code"', "per_page": 500},
    )
    r.raise_for_status()
    for rule in r.json()["data"]:
        if rule["rule_id"] not in wanted:
            requests.delete(
                f"{KIBANA}/api/detection_engine/rules",
                headers=HEADERS,
                auth=AUTH,
                params={"rule_id": rule["rule_id"]},
            ).raise_for_status()
            print(f"silindi: {rule['name']}")


if __name__ == "__main__":
    deploy()
    sync_deleted()