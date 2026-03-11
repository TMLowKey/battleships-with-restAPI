# Lodě – REST API + GUI + CLI

Tento projekt implementuje take-home zadání hry **Lodě** pro 2 hráče.

## Rychlý start (60 sekund)

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
* provedení tahu,
* získání stavu hry.

**Nad rámec zadání:**

* webové GUI (`/game`),
* CLI klient,
* Docker konfigurace pro snadné spuštění a deployment.

## Proč je zde víc než jen API

Cílem nebylo pouze splnit požadované endpointy, ale ukázat i end-to-end řešení:

* API vrstvu jako základ zadání,
* dva různé klienty nad stejným API (prohlížeč + terminál),
* reprodukovatelné spuštění pomocí Dockeru.

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
python -m pytest
```

## API, GUI a CLI

* API dokumentace: `/docs`
* GUI verze hry: `/game`
* Root `/` přesměrovává na `/game/`

Použití CLI:

```text
cli.py [-h] [--base-url BASE_URL] {create,state,turn,play}
```

Příklad:

```bash
python app/cli.py --base-url http://127.0.0.1:18000 create --player1 Alice --player2 Bob --size 10
```

## Konfigurace

V `docker-compose.yml` lze upravit:

* `MAX_ACTIVE_GAMES` (výchozí hodnota `50`)
* `IDLE_TIMEOUT_HOURS` (výchozí hodnota `24`)

## Deployment na Debian server (stručně)

1. Nainstalovat Docker a Docker Compose plugin.
2. Nakopírovat repozitář na server.
3. Spustit `docker compose up -d --build`.
4. Před kontejner umístit reverse proxy (Nginx/Caddy) pro TLS a doménu.

## Limity a edge cases

Aktuální implementace je záměrně jednoduchá a odpovídá rozsahu take-home zadání:

* hra používá pouze in-memory úložiště (bez perzistence),
* po restartu procesu se stav her ztratí,
* není řešena autentizace ani autorizace,
* endpointy jsou navrženy pro 2 hráče,
* dokončené nebo dlouhodobě neaktivní hry se uklízejí ze store podle timeoutu.

Při produkčním nasazení by dávalo smysl doplnit databázi, autentizaci, audit log a robustnější lifecycle management her.

## Cross-platform

* REST API je platformně nezávislé.
* Webové GUI běží v moderních prohlížečích na všech běžných OS.
* CLI klient běží všude, kde je dostupný Python 3.12+.
