"""
build/rules.ndjson faylındakı qaydaları Kibana-ya yükləyir.

0) Gözləmə: Kibana tam hazır olana qədər gözləyir (VM yeni açılanda lazımdır).
1) Yükləmə: eyni rule_id varsa yeniləyir, yoxdursa yaradır (idempotent).
2) Sinxron: Kibana-da "detection-as-code" teqli, amma repoda olmayan qaydaları silir.

Lazımi mühit dəyişənləri: KIBANA_URL, KIBANA_USER, KIBANA_PASS
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

KIBANA = os.environ["KIBANA_URL"].rstrip("/")
AUTH = (os.environ["KIBANA_USER"], os.environ["KIBANA_PASS"])
HEADERS = {"kbn-xsrf": "true"}  # Kibana API hər dəyişiklik sorğusunda bunu tələb edir
NDJSON = Path("build") / "rules.ndjson"
TIMEOUT = 60          # bir sorğu üçün maksimum gözləmə (saniyə)
WAIT_TOTAL = 300      # Kibana-nın hazır olmasını ən çox 5 dəqiqə gözlə
WAIT_STEP = 10        # hər 10 saniyədən bir yoxla


def wait_for_kibana():
    """Kibana /api/status 'available' deyənə qədər gözləyir.

    Səbəb: VM açılanda runner Kibana-dan tez oyanır. Port açıq olur,
    amma Kibana bağlantını cavabsız bağlayır (RemoteDisconnected).
    """
    deadline = time.time() + WAIT_TOTAL
    while True:
        try:
            r = requests.get(f"{KIBANA}/api/status", auth=AUTH, timeout=TIMEOUT)
            level = r.json()["status"]["overall"]["level"] if r.ok else f"HTTP {r.status_code}"
        except (requests.RequestException, ValueError, KeyError) as e:
            level = type(e).__name__
        if level == "available":
            print("Kibana hazırdır")
            return
        if time.time() > deadline:
            sys.exit(f"Kibana {WAIT_TOTAL} saniyə ərzində hazır olmadı (son vəziyyət: {level})")
        print(f"Kibana hələ hazır deyil ({level}), {WAIT_STEP} saniyə gözləyirəm...", flush=True)
        time.sleep(WAIT_STEP)


def deploy():
    """Bütün qaydaları bir sorğu ilə import edir (overwrite=true → yeniləyir)."""
    r = requests.post(
        f"{KIBANA}/api/detection_engine/rules/_import",
        params={"overwrite": "true"},
        headers=HEADERS,
        auth=AUTH,
        files={"file": ("rules.ndjson", NDJSON.read_bytes())},
        timeout=TIMEOUT,
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
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    for rule in r.json()["data"]:
        if rule["rule_id"] not in wanted:
            requests.delete(
                f"{KIBANA}/api/detection_engine/rules",
                headers=HEADERS,
                auth=AUTH,
                params={"rule_id": rule["rule_id"]},
                timeout=TIMEOUT,
            ).raise_for_status()
            print(f"silindi: {rule['name']}")


if __name__ == "__main__":
    wait_for_kibana()
    deploy()
    sync_deleted()