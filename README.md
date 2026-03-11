# Lodě – REST API + GUI + CLI

Tento projekt implementuje take-home zadání hry **Lodě** pro 2 hráče. Projekt je dostupný jednak přes selfhosting (návod níže) druhak na https://warships.tengler.app/game/ v GUI, případně instrukce pro REST API ovládání jsou dostupné na https://warships.tengler.app/docs/.

## Rychlý start

```bash
docker compose up -d --build
```

Po spuštění je aplikace dostupná na:

* `http://127.0.0.1:18000/game/` – GUI
* `http://127.0.0.1:18000/docs` – API dokumentace
* `http://127.0.0.1:18000/health` – healthcheck

Zastavení aplikace:

```bash
docker compose down
```

## Splnění zadání vs. rozšíření

**Požadovaný rozsah zadání (REST API):**

* vytvoření nové hry,
* připojení hráče pomocí invite kódu,
* provedení tahu,
* získání stavu hry.

**Nad rámec zadání:**

* webové GUI (`/game`),
* CLI klient,
* Docker konfigurace pro snadné spuštění a deployment.
* Implementace JWT token

## Proč je zde víc než jen API

Cílem nebylo pouze splnit požadované endpointy, ale ukázat i end-to-end řešení:

* API vrstvu jako základ zadání,
* dva různé klienty nad stejným API (prohlížeč + terminál),
* reprodukovatelné spuštění pomocí Dockeru,
* implementace JWT autentizace je zvolena místo OAuth kvůli menší komplexitě a dostatečnosti pro tento projekt, zároveň s ohledem na to, že JWT je explicitně požadováno v požadavcích na pozici.

Docker je zde záměrně i jako ukázka práce s kontejnerizací a konzistentním během napříč prostředími.

## Proč FastAPI (a ne Flask)

Flask mám osobně rád pro jeho flexibilitu, ale pro tento úkol jsem zvolil FastAPI, protože:

* má velmi dobrou podporu type hintingu,
* schémata request/response modelů jsou přímo součástí kódu,
* automaticky generuje OpenAPI dokumentaci,
* poskytuje interaktivní API rozhraní na `/docs`,
* umožňuje vyhnout se zbytečnému boilerplate.

Pro menší API-first službu jde podle mě o praktičtější volbu.

## Z čeho se aplikace skládá

* `app/main.py` – FastAPI aplikace a endpointy
* `app/engine.py` – herní logika (generování flotily, pravidla tahu, výhra)
* `app/store.py` – in-memory úložiště her
* `app/models.py` – request/response modely
* `app/security.py` – bezpečnostní vrstva (hashování hesel, JWT access/refresh tokeny)
* `app/static/` – webové GUI (`/game`, `/ui`)
* `app/cli.py` – CLI klient
* `tests/` – testy API, enginu, store a CLI
* `Dockerfile`, `docker-compose.yml` – kontejnerizace a runtime konfigurace

## Spuštění

### Varianta A: Docker (doporučeno)

```bash
docker compose up -d --build
```

Užitečné příkazy:

```bash
docker compose logs -f
docker compose ps
docker compose down
```

### Varianta B: Lokální běh bez Dockeru (Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Poté je aplikace dostupná na:

* `http://127.0.0.1:8000/game/`
* `http://127.0.0.1:8000/docs`

## Spuštění testů

```bash
python -m pytest tests --import-mode=importlib
```

## API, GUI a CLI

* API dokumentace: `/docs`
* GUI verze hry: `/game`
* Root `/` přesměrovává na `/login`

Použití CLI:

```text
cli.py [-h] [--base-url BASE_URL] {register,login,logout,me,create,join,state,turn,play}
```

Příklad:

```bash
python app/cli.py --base-url http://127.0.0.1:18000 register --username alice
python app/cli.py --base-url http://127.0.0.1:18000 create --opponent Bob --size 10
```

## Konfigurace

V `docker-compose.yml` lze upravit:

* `MAX_ACTIVE_GAMES` (výchozí hodnota `50`)
* `IDLE_TIMEOUT_HOURS` (výchozí hodnota `24`)

Pro JWT lze navíc nastavit (doporučeno hlavně pro produkci):

* `JWT_SECRET` (povinné v produkci, silný náhodný secret)
* `JWT_ISSUER`
* `JWT_AUDIENCE`
* `JWT_ACCESS_TOKEN_TTL_MINUTES`
* `JWT_REFRESH_TOKEN_TTL_DAYS`

## Deployment na Debian server (stručně)

1. Nainstalovat Docker a Docker Compose plugin.
2. Nakopírovat repozitář na server.
3. Spustit `docker compose up -d --build`.
4. Před kontejner umístit reverse proxy (Nginx/Caddy) pro TLS a doménu.

## Limity a edge cases

* hra používá pouze in-memory úložiště (bez perzistence),
* po restartu procesu se stav her ztratí,
* autentizace je řešena JWT (access/refresh) tokeny navázanými na uživatelský účet,
* endpointy jsou navrženy pro 2 hráče,
* dokončené nebo dlouhodobě neaktivní hry se uklízejí ze store podle timeoutu,
* chybí server-side revokace/rotace refresh tokenů (po úniku tokenu platí do expirace),
* v GUI jsou tokeny ukládány do `localStorage` (pro produkci vhodnější HttpOnly cookie přístup),
* chybí rate limiting pro login/register/join (ochrana proti brute-force),
* Docker image běží defaultně jako root uživatel.

Při produkčním nasazení by dávalo smysl doplnit databázi, revokaci tokenů, audit log, rate limiting, běh pod non-root uživatelem a robustnější lifecycle management her.

Bezpečnostní poznámka: produkční nasazení předpokládá provoz za TLS reverse proxy (HTTPS).

## Cross-platform

* REST API je platformně nezávislé.
* Webové GUI běží v moderních prohlížečích na všech běžných OS.
* CLI klient běží všude, kde je dostupný Python 3.12+.
