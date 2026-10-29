"""
build/rules.ndjson faylındakı qaydaları Kibana-ya yükləyir.

0) Gözləmə: Kibana tam hazır olana qədər gözləyir (VM yeni açılanda lazımdır).
1) Tip dəyişikliyi: tipi dəyişən qaydaları (məs. query → eql) silir, import yenidən yaradır.
2) Yükləmə: eyni rule_id varsa yeniləyir, yoxdursa yaradır (idempotent).
3) Sinxron: Kibana-da "detection-as-code" teqli, amma repoda olmayan qaydaları silir.

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


def wanted_rules():
    """Repodakı qaydalar: rule_id → qayda (build/rules.ndjson-dan)."""
    return {
        r["rule_id"]: r
        for r in (json.loads(line) for line in NDJSON.read_text(encoding="utf-8").splitlines() if line.strip())
    }


def find_ours():
    """Kibana-dakı bizim qaydalar ("detection-as-code" teqli)."""
    r = requests.get(
        f"{KIBANA}/api/detection_engine/rules/_find",
        headers=HEADERS,
        auth=AUTH,
        params={"filter": 'alert.attributes.tags:"detection-as-code"', "per_page": 500},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["data"]


def delete_rule(rule_id):
    requests.delete(
        f"{KIBANA}/api/detection_engine/rules",
        headers=HEADERS,
        auth=AUTH,
        params={"rule_id": rule_id},
        timeout=TIMEOUT,
    ).raise_for_status()


def recreate_type_changed(wanted):
    """Kibana mövcud qaydanın tipini import ilə dəyişməyə icazə vermir
    (query → eql: "params invalid", 400). Belə qaydaları əvvəlcə silirik,
    import onları yeni tiplə yaradır. Köhnə alertlər silinmir."""
    for rule in find_ours():
        new = wanted.get(rule["rule_id"])
        if new and rule["type"] != new["type"]:
            delete_rule(rule["rule_id"])
            print(f"tip dəyişdi ({rule['type']} → {new['type']}), yenidən yaradılır: {rule['name']}")


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


def sync_deleted(wanted):
    """Repoda olmayan, amma Kibana-da qalan bizim qaydaları silir."""
    for rule in find_ours():
        if rule["rule_id"] not in wanted:
            delete_rule(rule["rule_id"])
            print(f"silindi: {rule['name']}")


if __name__ == "__main__":
    wait_for_kibana()
    wanted = wanted_rules()
    recreate_type_changed(wanted)
    deploy()
    sync_deleted(wanted)