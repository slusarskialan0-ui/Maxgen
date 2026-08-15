# 📖 API Documentation — Polska Auto Leads Engine v3.0.0

Interaktywna dokumentacja Swagger: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## 🔌 Endpointy

### System
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/` | Info + linki |
| GET | `/health` | Status serwera |
| GET | `/metrics` | Metryki pipeline |
| GET | `/api-config` | URL API (auto-connect frontend) |

### Klienci (`/clients`)
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/clients` | Lista klientów (filtry: voivodeship, industry, source_type, status, skip, limit) |
| GET | `/clients/{id}` | Szczegóły klienta + zlecenia |
| PATCH | `/clients/{id}/status` | Zmiana statusu |

### Leads (`/leads`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/leads` | Lista leadów (filtry: stage, source, assigned_to, campaign_id, voivodeship, min_score) |
| POST | `/leads` | Utwórz lead (auto-scoring + auto-assign + auto-follow-up) |
| GET | `/leads/funnel` | Statystyki lejka sprzedażowego |
| GET | `/leads/due-follow-ups` | Leady wymagające follow-up |
| GET | `/leads/ai-prediction` | Predykcja konwersji AI + top leady |
| GET | `/leads/{id}` | Szczegóły leada |
| PATCH | `/leads/{id}` | Aktualizuj leada |
| DELETE | `/leads/{id}` | Usuń leada |
| POST | `/leads/webhook` | Webhook — przyjmuje leady z zewnętrznych źródeł |

**Przykład tworzenia leada:**
```json
POST /leads
{
  "full_name": "Jan Kowalski",
  "email": "jan@firma.pl",
  "company": "Firma Sp. z o.o.",
  "industry": "Budowlana",
  "source": "form"
}
```

**Odpowiedź (z auto-scoringiem):**
```json
{
  "id": 1, "stage": "nowy", "score": 75.0,
  "conversion_probability": 0.320,
  "assigned_to": "agent1",
  "follow_up_at": "2026-08-13T06:07:00"
}
```

**Webhook:**
```bash
curl -X POST http://localhost:8000/leads/webhook \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Anna","email":"anna@test.pl","source":"webhook"}'
```

### Kampanie (`/campaigns`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/campaigns` | Lista kampanii z metrykami konwersji |
| POST | `/campaigns` | Utwórz kampanię |
| GET | `/campaigns/{id}` | Szczegóły |
| PATCH | `/campaigns/{id}` | Aktualizuj (status, budżet) |
| DELETE | `/campaigns/{id}` | Usuń |

### Automatyzacje (`/automations`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/automations` | Lista reguł automatyzacji |
| POST | `/automations` | Utwórz regułę |
| PATCH | `/automations/{id}` | Aktualizuj/włącz/wyłącz |
| DELETE | `/automations/{id}` | Usuń |
| POST | `/automations/{id}/run` | Uruchom manualnie |

Wyzwalacze: `new_lead`, `stage_change`, `score_above`, `follow_up_due`  
Akcje: `assign`, `follow_up`, `close`, `notify`

### Użytkownicy (`/users`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/users` | Lista użytkowników (agenci/managerowie) |
| POST | `/users` | Utwórz |
| PATCH | `/users/{id}` | Aktualizuj rolę/status |
| DELETE | `/users/{id}` | Usuń |

### Synchronizacja (`/sync`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/sync/export/leads/csv` | Eksport CSV |
| GET | `/sync/export/leads/json` | Eksport JSON |
| POST | `/sync/import/leads/json` | Import JSON (multipart) |
| POST | `/sync/backup` | Utwórz backup |
| GET | `/sync/backups` | Historia backupów |
| POST | `/sync/recovery` | Odtwórz z ostatniego backupu |



### Oferty (`/offers`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/offers` | Lista ofert (opcjonalnie filtr `lead_id`) |
| POST | `/offers` | Generowanie oferty offline dla leada |
| PATCH | `/offers/{id}` | Aktualizacja statusu/treści |

### Płatności (`/payments`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/payments` | Lista płatności (opcjonalnie filtr `lead_id`) |
| POST | `/payments/simulate` | Symulacja płatności offline |
| PATCH | `/payments/{id}` | Aktualizacja statusu/logu |

### Silnik offline (`/engine`) — NOWE
| Metoda | URL | Opis |
|--------|-----|------|
| POST | `/engine/generate` | Generator kampanii + leadów + automatyzacji |
| GET | `/engine/marketing-content` | Generator CTA/opisów reklam |
| GET | `/engine/traffic-dashboard` | Dashboard ruchu leadów |
| GET | `/engine/conversion-dashboard` | Dashboard konwersji |
| GET | `/engine/revenue-dashboard` | Dashboard przychodów |
| POST | `/engine/self-heal` | Auto-naprawa otwartych leadów |
| GET | `/engine/events` | Zdarzenia systemowe offline |
| GET | `/engine/logs` | Logi operacyjne silnika |

### Pipeline, Stats, Analytics, Security, System — bez zmian
Patrz `/docs` dla pełnej listy.

---

## 📊 Kody odpowiedzi
| Kod | Opis |
|-----|------|
| 200 | OK |
| 201 | Utworzono |
| 204 | Usunięto |
| 400 | Błędne dane |
| 404 | Nie znaleziono |
| 409 | Konflikt |
| 429 | Rate limit (100 req/min/IP) |
| 500 | Błąd serwera |
