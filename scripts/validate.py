import json, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

CHECK_TESTS = True

schema = json.loads(Path("schema/rule.schema.json").read_text(encoding="utf-8"))
v = Draft202012Validator(schema)
errors, seen = [], {}

for p in sorted(Path("rules").rglob("*.yml")):
    try:
        rule = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        errors.append(f"{p}: YAML sintaksis xətası ({e})")
        continue
    if not isinstance(rule, dict):
        errors.append(f"{p}: fayl boşdur və ya YAML qayda deyil")
        continue
    for e in v.iter_errors(rule):
        errors.append(f"{p}: {e.message}")
    rid = rule.get("id")
    if rid in seen:
        errors.append(f"{p}: ID təkrarlanır ({seen[rid]} ilə)")
    seen[rid] = p
    if CHECK_TESTS:
        for kind in ("positive.json", "negative.json"):
            if not (Path("tests") / str(rid) / kind).exists():
                errors.append(f"{p}: tests/{rid}/{kind} yoxdur")

print("\n".join(errors) if errors else f"✅ {len(seen)} qayda yoxlamadan keçdi")
sys.exit(1 if errors else 0)