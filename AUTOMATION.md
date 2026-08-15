# ⚡ Dokumentacja Automatyzacji — Polska Auto Leads Engine

---

## Jak działają automatyzacje

Automatyzacje uruchamiają się **w tle** po każdym utworzeniu lub aktualizacji leada.

### Wyzwalacze (trigger)

| Wyzwalacz | Kiedy |
|-----------|-------|
| `new_lead` | Przy każdym nowym leadzie |
| `stage_change` | Po zmianie etapu lejka |
| `score_above` | Gdy score AI przekroczy próg |
| `follow_up_due` | Gdy termin follow-up minął |

### Akcje (action)

| Akcja | Co robi |
|-------|---------|
| `assign` | Auto-przypisuje leada do agenta (round-robin) |
| `follow_up` | Planuje follow-up na +24h od teraz |
| `close` | Zamknięcie leada (bez zmiany etapu — do implementacji) |
| `notify` | Placeholder na powiadomienie (webhook/email) |

---

## Scoring AI

Algorytm heurystyczny oblicza score 0–100:

| Czynnik | Punkty |
|---------|--------|
| Baza (zawsze) | +20 |
| Ma email | +20 |
| Ma telefon | +15 |
| Ma firmę | +10 |
| Ma branżę | +10 |
| Ma województwo | +5 |
| Ma notatki (>20 znaków) | +10 |
| Powiązany z kampanią | +10 |
| Wariancja losowa | ±5 |

**Predykcja konwersji** = `etap_bazowy * 0.6 + (score/100) * 0.4`

| Etap | Bazowe prawdopodobieństwo |
|------|--------------------------|
| nowy | 5% |
| kontakt | 20% |
| negocjacje | 50% |
| wygrany | 100% |
| przegrany | 0% |

---

## Auto-przypisanie (round-robin)

Przy tworzeniu leada bez przypisanego agenta, system:
1. Pobiera wszystkich aktywnych użytkowników z rolą `agent` lub `manager`
2. Liczy aktywne leady per agent (nie wygrany/przegrany)
3. Przypisuje do agenta z najmniejszą liczbą aktywnych leadów

---

## Domyślne automatyzacje (seed)

1. **Auto-przypisz nowego leada** — trigger: `new_lead`, action: `assign`
2. **Auto-follow-up po 24h** — trigger: `new_lead`, action: `follow_up`
3. **Priorytetyzuj wysokie score** — trigger: `score_above` (próg: 70), action: `assign`

---

## Zarządzanie przez API

```bash
# Lista automatyzacji
GET /automations

# Utwórz nową
POST /automations
{
  "name": "Follow-up dla VIP",
  "trigger": "score_above",
  "action": "follow_up",
  "condition_json": "{\"threshold\": 80}",
  "enabled": true
}

# Włącz/wyłącz
PATCH /automations/{id}
{"enabled": false}

# Uruchom manualnie
POST /automations/{id}/run
```

---

## Auto-scaling i self-healing

| Endpoint | Opis |
|----------|------|
| `GET /system/self-healing` | Status napraw |
| `GET /system/load-forecast` | Prognoza obciążenia |
| `POST /system/fix-pipeline-stall` | Napraw zawieszony pipeline |
| `POST /system/fix-slow-queries` | ANALYZE + VACUUM SQLite |
| `GET /system/resource-optimizer` | Rekomendacje optymalizacji |

Pipeline ma auto-retry (3 próby, sleep 2s) przy błędach.

---

## Lejek sprzedażowy — etapy

```
nowy → kontakt → negocjacje → wygrany
                             ↘ przegrany
```

Zmiana etapu przez API:
```bash
PATCH /leads/{id}
{"stage": "kontakt"}
```

Przy zmianie na `wygrany` lub `przegrany`:
- Automatycznie ustawia `closed_at`
- Aktualizuje `conversion_probability` do 1.0 lub 0.0
