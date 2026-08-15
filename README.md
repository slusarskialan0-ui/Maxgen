# 🇵🇱 Polska Auto Leads Engine — v3.0.0

**FINALNY, kompletny, w pełni automatyczny produkt SaaS** — system pozyskiwania klientów dla całej Polski.  
AUTO-SYSTEM + AUTO-SKALOWANIE + AUTO-DEPLOY + AUTO-SECURITY + AUTO-ANALYTICS + AUTO-BIZNES + AUTO-MOBILE + PWA + Developer Platform.  
**Bez logowania użytkowników. Gotowy do wdrożenia.**

---

## 🚀 Szybki start (lokalnie)

### Wymagania
- Python 3.9+
- Node.js 18+

### Uruchomienie jedną komendą

```bash
bash start_all.sh
```

| Usługa | URL |
|--------|-----|
| 📊 Panel web | http://localhost:3000 |
| 🔌 Backend API | http://localhost:8000 |
| 📖 API Docs (Swagger) | http://localhost:8000/docs |
| 📖 API Docs (ReDoc) | http://localhost:8000/redoc |
| ❤️ Health check | http://localhost:8000/health |
| 📈 Metryki | http://localhost:8000/metrics |

---

## 🌐 Deploy — Railway (backend)

1. Utwórz nowy projekt na [Railway](https://railway.app)
2. Podłącz to repo (folder `backend/`)
3. Railway auto-wykryje `Procfile` i uruchomi backend
4. Ustaw zmienne środowiskowe:
   ```
   DATABASE_URL=postgresql://...   # Railway Postgres plugin
   CORS_ORIGINS=https://twoj-frontend.vercel.app
   PORT=8000
   ```
5. Skopiuj URL backendu (np. `https://api.railway.app`)

---

## 🌐 Deploy — Vercel (frontend)

1. Utwórz nowy projekt na [Vercel](https://vercel.com)
2. Podłącz to repo, ustaw **Root Directory = `frontend`**
3. Ustaw zmienne środowiskowe w Vercel:
   ```
   VITE_API_URL=https://twoj-backend.railway.app
   ```
4. Build command: `npm run build` | Output: `dist`
5. Vercel automatycznie doda SPA rewriting (vercel.json już skonfigurowany)

---

## 📱 Wersja mobilna + PWA

Aplikacja jest w pełni **mobile-first** i działa jako **Progressive Web App (PWA)**:
- Responsywny layout z hamburger menu na mobile
- Instalowalna na telefonie (Add to Home Screen)
- Service worker — działa offline (app shell) + background sync
- `manifest.json` z ikonami i splash screen
- Meta tagi dla iOS i Android
- Auto-update PWA bez pytania użytkownika

Aby zainstalować na telefonie:
1. Otwórz aplikację w przeglądarce mobilnej
2. Kliknij "Dodaj do ekranu głównego"

---

## 🤖 Offline Growth OS

Nowy moduł `AUTO-CONTROL` dostarcza kompletny lokalny system:
- generowanie leadów offline, lokalnego ruchu i scoringu AI bez API,
- automatyzację sprzedaży (kwalifikacja, lejek, auto-assignment, follow-up, auto-close),
- kampanie marketingowe offline z CTA i treściami reklamowymi,
- oferty oraz symulacje płatności offline z potwierdzeniami,
- eksport/import, backup i recovery SQLite,
- dashboard konwersji i dashboard przychodów.

Główne endpointy AUTO:
- `POST /auto/bootstrap`
- `POST /auto/leads/generate`
- `POST /auto/sales/run`
- `POST /auto/campaigns/generate`
- `POST /auto/payments/simulate`
- `POST /auto/sync/export` / `backup` / `recovery`
- `GET /auto/overview`

Nowe tabele SQLite: `leads`, `users`, `campaigns`, `offers`, `payments`, `logs`, `automations`.
Backupi offline są domyślnie zapisywane w `backend/runtime_backups` lub w ścieżce wskazanej przez `AUTO_BACKUP_DIR`.

## 📊 Widoki aplikacji

| Widok | Ścieżka | Opis |
|-------|---------|------|
| Dashboard | `/` | Statystyki, wykresy wg województwa/branży/źródła |
| Mapa Województw | `/mapa` | Status skanowania 16 województw |
| Klienci | `/klienci` | Lista z filtrami |
| Szczegóły klienta | `/klienci/:id` | Profil firmy + zlecenia |
| Zlecenia | `/zlecenia` | Lista zleceń z wartościami |
| Szczegóły zlecenia | `/zlecenia/:id` | Szczegóły + historia |
| AUTO-LEADS | `/auto-leads` | Uruchomienie pipeline pozyskiwania |
| AUTO-STATUS | `/auto-status` | Live monitoring systemu + metryki |
| AUTO-CONTROL | `/auto-control` | Leady, sprzedaż, kampanie, oferty, płatności, backupy |
| AUTO-KONTAKT | `/auto-kontakt` | Generator wiadomości do klientów |
| AUTO-SECURITY | `/auto-security` | Bezpieczeństwo: IP blocking, audit trail, backup |
| AUTO-ANALYTICS | `/auto-analytics` | Revenue, growth, churn, heatmaps |
| AUTO-BIZNES | `/auto-biznes` | Pricing AI, billing, marketplace, usage |
| DEV PLATFORM | `/auto-dev` | API analytics, limits, key rotation, sandbox |
| Marketplace | `/marketplace` | Lead marketplace — top 20 leadów |
| Agencja | `/agencja` | Panel dla agencji |
| Landing | `/landing` | Landing page + cennik + CTA |
| AUTO-ROZWÓJ | `/auto-rozwoj` | Roadmap AI, feature suggestions, priority AI |

---

## 🏗️ Architektura

```
polska-auto-leads-engine/
├── backend/                    # FastAPI backend (Railway)
│   ├── main.py                 # App + middleware + health + metrics + version
│   ├── config.py               # ENV-based config
│   ├── database.py             # SQLAlchemy (SQLite / Postgres)
│   ├── requirements.txt
│   ├── start.sh
│   └── app/
│       ├── models/models.py    # All DB models
│       ├── routers/
│       │   ├── clients.py      # /clients
│       │   ├── orders.py       # /orders
│       │   ├── voivodeships.py # /voivodeships
│       │   ├── industries.py   # /industries
│       │   ├── pipeline.py     # /pipeline (auto-resume, retries)
│       │   ├── stats.py        # /stats
│       │   ├── analytics.py    # /analytics (revenue, growth, churn, heatmap)
│       │   ├── biznes.py       # /biznes (pricing AI, billing, marketplace)
│       │   ├── security.py     # /security (IP blocking, audit trail, backup)
│       │   ├── devplatform.py  # /dev (API analytics, limits, key rotation)
│       │   └── system.py       # /system (self-healing, load forecast, optimizer)
│       ├── pipeline/pipeline.py # Auto-pipeline (concurrent sources, dedup)
│       ├── sources/            # Data sources (katalog, mapa, rejestr, social, ogloszenia)
│       └── data/geography.py   # 16 voivodeships + cities + order templates
├── frontend/                   # React + Vite + Tailwind (Vercel)
│   ├── src/
│   │   ├── App.jsx             # Router + Sidebar + mobile menu
│   │   ├── api/api.js          # Axios (AUTO-CONNECT via VITE_API_URL)
│   │   ├── main.jsx            # PWA install prompt + SW registration
│   │   └── pages/             # 17 pages
│   └── public/
│       ├── manifest.json       # PWA manifest
│       └── sw.js               # Service worker (offline + background sync)
├── .github/workflows/ci.yml    # CI/CD: lint + build + deploy check
├── start_all.sh                # Auto-start script (backend + frontend)
├── Procfile                    # Railway entry point
├── railway.json                # Railway config
├── API.md                      # Full API documentation
└── README.md                   # This file
```

---

## 🧩 AUTO-SYSTEM — moduły

### 🔄 AUTO-SELF-HEALING
- Pipeline auto-restartuje się przy błędach (3 próby)
- `/system/self-healing` — status naprawiania
- `/system/fix-pipeline-stall` — naprawia zawieszone pipeline'y
- `/system/fix-slow-queries` — optymalizuje bazę danych

### 📈 AUTO-PREDICTIVE
- `/system/forecast` — predykcja problemów
- `/system/load-forecast` — prognoza obciążenia
- `/analytics/growth` — trend wzrostu

### ⚡ AUTO-HOT-CACHE
- In-process TTL cache (30s) dla statystyk i metryk
- Redukcja zapytań DB przy wysokim ruchu

### 🛡️ AUTO-SECURITY
- IP blocklist (in-memory + REST API)
- Rate limiting: 100 req/min per IP
- Audit trail w DB (każdy request)
- Threat detection (automatyczne)
- Backup on-demand

### 📊 AUTO-ANALYTICS
- Revenue tracking (wg miesiąca)
- Growth tracking (klienci + zlecenia)
- Churn tracking (aktywni vs utraceni)
- Usage heatmap (wg województwa)
- SaaS dashboard — wszystko w jednym

### 💰 AUTO-BIZNES
- Pricing AI — ceny dynamiczne wg popytu
- Billing — faktury + abonament
- Lead Marketplace — top 20 leadów
- Agency Dashboard — panel dla agencji
- Usage tracking — requesty API

### 🧩 AUTO-DEV PLATFORM
- API analytics w czasie rzeczywistym
- Dynamiczne limity wg planu
- Sandbox environment
- API key rotation
- Dokumentacja auto-generowana (/docs, /redoc)

### 🧠 AUTO-ROZWÓJ
- Roadmap generowana automatycznie
- Feature suggestions
- Priority AI — priorytety wg wartości biznesowej

---

## 📋 Zmienne środowiskowe

### Backend / kontener offline
| Zmienna | Opis | Domyślnie |
|---------|------|-----------|
| `DATABASE_URL` | PostgreSQL URL | `sqlite:///./polska_leads.db` |
| `CORS_ORIGINS` | Frontend URL (Vercel) | `http://localhost:3000` |
| `PORT` | Port backendu | `8000` |
| `AUTO_BACKGROUND_ENABLED` | Włącza automatyczny silnik leadów w tle | `true` |
| `AUTO_BACKGROUND_INTERVAL_SECONDS` | Interwał cykli automatycznych | `300` |
| `AUTO_BACKGROUND_LEADS_LIMIT` | Liczba leadów generowanych w cyklu | `12` |
| `AUTO_BACKUP_EVERY_CYCLES` | Co ile cykli engine robi automatyczny backup | `6` |
| `AUTO_BACKUP_KEEP_LATEST` | Liczba najnowszych backupów utrzymywanych automatycznie | `20` |
| `AUTO_SELF_HEAL_STALLED_PIPELINE` | Auto-reset zablokowanych statusów pipeline | `true` |

### Frontend (Vercel)
| Zmienna | Opis | Domyślnie |
|---------|------|-----------|
| `VITE_API_URL` | Backend URL (Railway) | `http://localhost:8000` |

---

## 🔌 Kluczowe endpointy

```
GET  /health              → {"status":"ok","version":"3.0.0"}
GET  /system/liveness     → szybki status procesu (live)
GET  /system/readiness    → gotowość DB + background engine
GET  /system/startup-status → one-click readiness + integration queue
GET  /system/ops-status   → alerty operacyjne + świeżość backupów
GET  /metrics             → metryki pipeline
GET  /stats               → statystyki klientów/zleceń
GET  /analytics/saas-dashboard → pełny SaaS dashboard
GET  /biznes/pricing      → dynamiczne ceny
GET  /security/status     → status bezpieczeństwa
GET  /dev/analytics       → statystyki API
GET  /system/self-healing → status auto-naprawiania
GET  /auto/engine-status  → status autonomicznego silnika tła
POST /pipeline/run        → uruchom pipeline
POST /automations/run-full-cycle → pełny cykl lead→offer→follow-up→close
GET  /biznes/plan-upgrade-preview → rekomendacje planu i usage
GET  /biznes/segments     → segmentacja klientów (branża/region/projekt)
GET  /sync/connectors     → status konektorów plug-and-run
POST /sync/connectors/{connector}/enqueue → dodaj zadanie integracyjne
POST /sync/connectors/run-pending → retry/fallback kolejki integracyjnej
```

---

## 🔧 Komendy startowe

```bash
# Lokalnie (wszystko)
bash start_all.sh

# Kontenery offline
docker compose up --build

# Tylko backend
cd backend && pip install -r requirements.txt && python main.py

# Tylko frontend
cd frontend && npm install && npm run dev

# Build frontendu (produkcja)
cd frontend && npm run build

# Testy importów backendu
cd backend && python -c "import main; print('OK')"
```

---

## ⚙️ Operacje zero-touch (wdrożenie stałe)

- Po starcie backend uruchamia autonomiczny silnik (bootstrap + leady + sprzedaż + kampanie + płatności).
- Co `AUTO_BACKUP_EVERY_CYCLES` cykli wykonywany jest automatyczny backup snapshotu danych.
- System trzyma tylko `AUTO_BACKUP_KEEP_LATEST` ostatnich backupów i usuwa starsze.
- `AUTO_SELF_HEAL_STALLED_PIPELINE=true` automatycznie resetuje zawieszone statusy pipeline.
- Workflow `.github/workflows/fly-backend-deploy.yml` wdraża backend i wykonuje health gate z rollbackiem.
- Workflow `.github/workflows/frontend-deploy.yml` uruchamia deploy frontendu przez Vercel hook + walidację PWA.

Szczegółowe procedury produkcyjne: `OPERATIONS.md`.

---

*Polska Auto Leads Engine v3.0.0 — Finalny produkt premium AUTO-SYSTEM*
