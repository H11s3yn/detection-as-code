import json, sys
from pathlib import Path

data = json.load(open(sys.argv[1], encoding="utf-8"))
ok = lambda o: not o.get("revoked") and not o.get("x_mitre_deprecated")
ids = set()
for o in data["objects"]:
    if o.get("type") == "attack-pattern" and ok(o):
        for r in o.get("external_references", []):
            if r.get("source_name") == "mitre-attack":
                ids.add(r["external_id"].lower())
tactics = {o["x_mitre_shortname"] for o in data["objects"] if o.get("type") == "x-mitre-tactic" and ok(o)}

Path("schema/attack_techniques.txt").write_text("\n".join(sorted(ids)) + "\n", encoding="utf-8")
Path("schema/attack_tactics.txt").write_text("\n".join(sorted(tactics)) + "\n", encoding="utf-8")
print(len(ids), "texnika,", len(tactics), "taktika yazıldı")