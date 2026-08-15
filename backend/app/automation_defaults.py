from sqlalchemy import or_

from app.models.models import Automation

DEFAULT_AUTOMATIONS = [
    {"name": "Auto-przypisz nowego leada", "trigger": "new_lead", "action": "assign", "condition_json": "{}"},
    {"name": "Auto-follow-up po 24h", "trigger": "new_lead", "action": "follow_up", "condition_json": "{}"},
    {"name": "Priorytetyzuj wysokie score", "trigger": "score_above", "action": "assign", "condition_json": '{"threshold": 70}'},
    {"name": "Auto-oferta dla gorącego leada", "trigger": "score_above", "action": "offer", "condition_json": '{"threshold": 60}'},
    {"name": "Auto-zamknięcie premium", "trigger": "score_above", "action": "close", "condition_json": '{"threshold": 90}'},
    {"name": "Auto-predykcja konwersji", "trigger": "new_lead", "action": "predict", "condition_json": "{}"},
]

def ensure_default_automation_rules(db) -> None:
    rule_rows = (
        db.query(Automation)
        .filter(or_(Automation.automation_type.is_(None), Automation.automation_type == ""))
        .order_by(Automation.id.asc())
        .all()
    )
    if not rule_rows:
        for row in DEFAULT_AUTOMATIONS:
            db.add(Automation(enabled=True, automation_type="", **row))
        db.commit()
        return

    repaired = 0
    used_names = {(row.name or "").strip() for row in rule_rows if (row.name or "").strip()}
    defaults_by_pair = {}
    for item in DEFAULT_AUTOMATIONS:
        defaults_by_pair.setdefault((item["trigger"], item["action"]), []).append(item)

    unnamed = [row for row in rule_rows if not (row.name or "").strip()]
    for auto in unnamed:
        seed = None
        pair = (auto.trigger or "new_lead", auto.action or "assign")
        for candidate in defaults_by_pair.get(pair, []):
            if candidate["name"] not in used_names:
                seed = candidate
                break
        if seed is None:
            for candidate in DEFAULT_AUTOMATIONS:
                if candidate["name"] not in used_names:
                    seed = candidate
                    break
        if seed is None:
            continue
        auto.name = seed["name"]
        auto.trigger = seed["trigger"]
        auto.action = seed["action"]
        auto.condition_json = seed.get("condition_json", "{}")
        auto.enabled = True
        used_names.add(seed["name"])
        repaired += 1

    existing_names = set(used_names)
    added = 0
    for seed in DEFAULT_AUTOMATIONS:
        if seed["name"] not in existing_names:
            db.add(Automation(enabled=True, automation_type="", **seed))
            added += 1

    if repaired or added:
        db.commit()
