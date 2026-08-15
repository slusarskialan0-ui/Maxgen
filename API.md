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

### Pipeline, Stats, Analytics, Security, System — bez zmian
Patrz `/docs` dla pełnej listy.

## 📊 Statystyki — `/stats`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/stats` | Statystyki ogólne: klienci wg województwa, branży, źródła |

---

## 🔧 Przykłady integracji

### Python
```python
import requests

BASE = "http://localhost:8000"

# Uruchom pipeline
resp = requests.post(f"{BASE}/pipeline/run", json={
    "voivodeship": "mazowieckie",
    "industries": ["mechanik", "fryzjer"]
})
print(resp.json())

# Pobierz klientów
clients = requests.get(f"{BASE}/clients", params={
    "voivodeship": "mazowieckie",
    "industry": "mechanik",
    "limit": 100
}).json()
print(clients["total"], "klientów")
```

### JavaScript / Node.js
```js
const BASE = 'http://localhost:8000';

// Pobierz statystyki
const stats = await fetch(`${BASE}/stats`).then(r => r.json());
console.log(stats.total_clients, 'klientów');
```

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

---

## 🏗️ Roadmap — Developer Platform

- [ ] API Key per `project_id` (bez logowania użytkowników)
- [ ] Webhooks po zakończeniu pipeline
- [ ] Export CSV/XLSX klientów
- [ ] Rate limiting per project_id
- [ ] OpenAPI client SDK generator

## 📈 Analytics — `/analytics`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/analytics/revenue` | Przychody: total, wg miesiąca, avg |
| GET | `/analytics/growth` | Wzrost klientów i zleceń wg miesiąca |
| GET | `/analytics/churn` | Wskaźnik churn, klienci aktywni vs utraceni |
| GET | `/analytics/heatmap` | Mapa ciepła wg województwa (klienci, zlecenia, przychody) |
| GET | `/analytics/saas-dashboard` | Pełny dashboard SaaS — wszystkie metryki w jednym |

---

## 💰 Biznes — `/biznes`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/biznes/pricing` | Dynamiczne ceny wg poziomu popytu |
| GET | `/biznes/billing` | Faktury + abonament |
| GET | `/biznes/marketplace` | Marketplace top leadów |
| GET | `/biznes/agency-dashboard` | Panel dla agencji |
| GET | `/biznes/subscriptions` | Plany subskrypcji i aktywny plan |
| GET | `/biznes/usage` | Użycie API i limitów |

---

## 🛡️ Security — `/security`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/security/status` | Status systemu bezpieczeństwa |
| POST | `/security/block-ip` | Zablokuj IP (body: `{ip, reason}`) |
| GET | `/security/blocked-ips` | Lista zablokowanych IP |
| DELETE | `/security/blocked-ips/{ip}` | Odblokuj IP |
| GET | `/security/audit-trail` | Historia działań (param: `limit`) |
| GET | `/security/threats` | Ostatnie wykryte zagrożenia |
| POST | `/security/backup` | Uruchom backup bazy danych |

---

## 🧩 Developer Platform — `/dev`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/dev/analytics` | Statystyki API (requesty, response time) |
| GET | `/dev/limits` | Limity API dla aktywnego planu |
| GET | `/dev/sandbox` | Info o środowisku testowym |
| POST | `/dev/keys/rotate` | Rotacja klucza API |
| GET | `/dev/keys` | Lista aktywnych kluczy API |
| GET | `/dev/docs-url` | Linki do dokumentacji |

---

## 🔧 Zmienne środowiskowe — Railway (backend)

```env
DATABASE_URL=******host:5432/db  # Railway Postgres
CORS_ORIGINS=https://twoj-frontend.vercel.app
PORT=8000
```

## 🔧 Zmienne środowiskowe — Vercel (frontend)

```env
VITE_API_URL=https://twoj-backend.railway.app
```

---

## 🚀 Szybki start lokalnie

```bash
bash start_all.sh
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Docs: http://localhost:8000/docs
```
