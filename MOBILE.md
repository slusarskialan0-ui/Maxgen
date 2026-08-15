# 📱 Instrukcja uruchomienia na telefonie

System działa jako **PWA (Progressive Web App)** — otwierasz w przeglądarce, dodajesz do ekranu głównego.

---

## Krok 1: Uruchom system na komputerze/serwerze

```bash
bash start_all.sh
```

## Krok 2: Znajdź adres IP komputera w sieci lokalnej

**Linux/Mac:**
```bash
ip a | grep "inet " | grep -v 127
# lub
hostname -I
```

**Windows:**
```cmd
ipconfig
```

Przykład: `192.168.1.100`

## Krok 3: Ustaw VITE_API_URL

W pliku `frontend/.env`:
```
VITE_API_URL=http://192.168.1.100:8000
```

Przebuduj frontend:
```bash
cd frontend && npm run build && npm run preview -- --host 0.0.0.0 --port 3000
```

## Krok 4: Otwórz na telefonie

W przeglądarce mobilnej (Chrome, Safari) wejdź na:
```
http://192.168.1.100:3000
```

## Krok 5: Dodaj do ekranu głównego (PWA)

**Android (Chrome):**
1. Menu (⋮) → "Dodaj do ekranu głównego"
2. Potwierdź

**iOS (Safari):**
1. Przycisk "Udostępnij" (kwadrat ze strzałką)
2. "Dodaj do ekranu głównego"

---

## Dostęp z dowolnego miejsca (opcjonalnie)

### Railway + Vercel (produkcja)

Backend → [railway.app](https://railway.app):
```
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://twoj-app.vercel.app
PORT=8000
```

Frontend → [vercel.com](https://vercel.com):
```
VITE_API_URL=https://twoj-backend.railway.app
```

### GitHub Codespaces (bez instalacji)

1. Otwórz repo na GitHub
2. Kliknij **Code → Codespaces → New codespace**
3. System uruchamia się automatycznie (`.devcontainer`)
4. Codespaces automatycznie udostępnia port 3000 i 8000
5. Wejdź na link Codespaces (działa też na telefonie!)

---

## Funkcje mobilne

- ✅ Responsywny interfejs (mobile-first)
- ✅ Hamburger menu na małych ekranach
- ✅ Touch-friendly przyciski
- ✅ Dashboard z wykresami
- ✅ Leads, Kampanie, Automatyzacje
- ✅ Eksport CSV/JSON
- ✅ Backup jednym kliknięciem
