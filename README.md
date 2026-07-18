# job-agent

Agente que lee las alertas de trabajo que te llegan por mail (LinkedIn, etc.),
las clasifica con Claude según tus preferencias, detecta avisos que parecen
falsos, y te manda un resumen diario por mail. Corre solo, una vez al día, vía
GitHub Actions.

No aplica a los trabajos automáticamente — solo triage y resumen.

## Setup

### 1. Requisitos

- Python 3.12+
- Una cuenta de Anthropic con API key ([console.anthropic.com](https://console.anthropic.com))
- Una cuenta de Google (la misma donde te llegan las alertas de LinkedIn)
- Un repo de GitHub (para el cron de GitHub Actions)

### 2. Habilitar la Gmail API

1. Andá a [Google Cloud Console](https://console.cloud.google.com/) y creá un proyecto nuevo (o usá uno existente).
2. En "APIs & Services" → "Library", buscá **Gmail API** y habilitala.
3. En "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID".
   - Tipo de aplicación: **Desktop app**.
4. Descargá el JSON de credenciales y guardalo como `credentials.json` en la raíz de este proyecto (no se sube a git — está en `.gitignore`).
5. Si tu proyecto de Google Cloud está en modo "Testing", agregá tu propio mail como usuario de prueba en "OAuth consent screen" → "Test users".

### 3. Instalar dependencias

```sh
pip install -r requirements.txt
```

### 4. Primera corrida (local) — autoriza el acceso a Gmail

```sh
cp .env.example .env
# completá ANTHROPIC_API_KEY y DIGEST_TO_EMAIL en .env

python -m src.main --dry-run
```

Esto abre el navegador para el consentimiento de OAuth (una sola vez) y genera
`token.json` en la raíz del proyecto. Con `--dry-run` el resumen se imprime en
la consola en vez de mandarse por mail — usalo para revisar que el parseo y la
clasificación funcionen antes de programar el cron.

### 5. Sacar el refresh token para GitHub Actions

Después del paso anterior, `token.json` tiene un campo `refresh_token`. Ese
valor, junto con el `client_id` y `client_secret` de `credentials.json`, son
los que necesita el workflow para correr sin que abras el navegador cada vez.

### 6. Configurar el repo en GitHub

1. Creá un repo en GitHub y pusheá este proyecto (asegurate de que `data/jobs.db` se suba — es el único archivo con estado que persiste entre corridas).
2. En "Settings" → "Secrets and variables" → "Actions", agregá:
   - `ANTHROPIC_API_KEY`
   - `GMAIL_CLIENT_ID` (de `credentials.json`)
   - `GMAIL_CLIENT_SECRET` (de `credentials.json`)
   - `GMAIL_REFRESH_TOKEN` (de `token.json`, paso 5)
   - `DIGEST_TO_EMAIL` (tu mail, donde querés recibir el resumen)
3. El workflow `.github/workflows/daily-digest.yml` corre todos los días a las 21:00 UTC (18:00 ARG — ajustá el cron si tu zona horaria es otra).
4. Probalo manualmente antes de confiar en el cron: pestaña "Actions" → "Daily job digest" → "Run workflow".

## Editar qué buscás

Editá `preferences.md` en texto libre — no hace falta tocar código. Se manda
tal cual al clasificador en cada corrida.

## Estructura

```
src/
  models.py        JobPosting, Classification
  gmail_client.py  OAuth + fetch de mails de alerta
  parsers/         HTML de cada fuente -> list[JobPosting]
  storage.py       SQLite: dedupe + historial + último timestamp corrido
  classifier.py    Clasificación con Claude Haiku 4.5 (structured output)
  digest.py        Arma el HTML del resumen
  mailer.py        Envía el resumen por Gmail
  main.py          Orquesta el pipeline completo
```

## Notas

- El parser de LinkedIn (`src/parsers/linkedin.py`) es heurístico porque
  LinkedIn no publica la plantilla de sus mails de alerta. Si con el tiempo
  deja de encontrar avisos, revisá el HTML de un mail real (Gmail → abrir
  mensaje → "Mostrar original") y ajustá los selectores.
- Para sumar otra fuente (Indeed, Computrabajo, etc.), agregá el remitente a
  `ALERT_SENDERS` en `gmail_client.py` y un parser nuevo en `src/parsers/`.
