# OPERATIONS — Zero-Touch Runbook

## 1) Definicja „0 wklepywania”
- Użytkownik końcowy: działa bez ręcznego wpisywania kodów i restartów.
- Operator: nie uruchamia ręcznie pipeline, backupów i czyszczenia.
- Deploy: po merge do `main` uruchamia się automatyczny deploy + health gate.

## 2) Automatyzacja operacyjna
- Background engine (backend) działa cyklicznie:
  - bootstrap danych,
  - generowanie leadów,
  - automatyzacja sprzedaży,
  - generowanie kampanii,
  - symulacja płatności.
- Maintenance co `AUTO_BACKUP_EVERY_CYCLES`:
  - backup snapshotu JSON,
  - retencja do `AUTO_BACKUP_KEEP_LATEST`,
  - auto-heal statusów pipeline (jeśli włączone),
  - normalizacja follow-up dla nowych leadów.

## 3) Monitoring i alerty
- `GET /system/liveness` — czy proces API żyje.
- `GET /system/readiness` — gotowość DB + background engine.
- `GET /system/ops-status` — zbiorczy status operacyjny:
  - ostatni backup i jego świeżość,
  - błędy engine/maintenance,
  - zawieszone rekordy pipeline.

## 4) Auto-deploy i rollback
- Backend: `.github/workflows/fly-backend-deploy.yml`
  - deploy na Fly,
  - pętla health-check `/system/readiness`,
  - rollback do poprzedniego stabilnego release przy błędzie.
- Frontend: `.github/workflows/frontend-deploy.yml`
  - deploy przez `VERCEL_DEPLOY_HOOK_URL`,
  - walidacja `index`, `manifest.json`, `sw.js`,
  - opcjonalny rollback hook `VERCEL_ROLLBACK_HOOK_URL`.

## 5) Mobile „na stałe” (PWA)
- Service Worker:
  - kolejkuje requesty offline,
  - automatycznie próbuje flush kolejki po odzyskaniu połączenia i sync triggerze.
- Frontend:
  - cyklicznie sprawdza zdrowie API,
  - przy problemach wyzwala `SYNC_REQUEST` do SW.

## 6) Wymagane sekrety CI/CD
- `FLY_API_TOKEN`
- `BACKEND_HEALTHCHECK_URL` (np. `https://twoj-backend.fly.dev`)
- `VERCEL_DEPLOY_HOOK_URL`
- `FRONTEND_HEALTHCHECK_URL` (np. `https://twoj-app.vercel.app`)
- opcjonalnie: `VERCEL_ROLLBACK_HOOK_URL`

## 7) Procedura utrzymaniowa (SLA operacyjne)
- Sprawdzaj `/system/ops-status` minimum co 15 min.
- Dla alertu `stale_backup`:
  1. sprawdź czy background engine działa (`/system/readiness`),
  2. uruchom ręczny backup (`POST /sync/auto-backup`),
  3. zweryfikuj retencję (`GET /sync/backups`).
- Dla alertu `pipeline_stalled`:
  1. uruchom `POST /system/fix-pipeline-stall`,
  2. zweryfikuj `GET /system/ops-status`.
