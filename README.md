# Aeris

Análise e previsão atmosférica em tempo real via modelo de cnn.

## Requisitos
- [uv](https://docs.astral.sh/uv/)
- [bun](https://bun.com/) ou [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)

## Estrutura

```text
pyproject.toml
.venv/
api/
  app.py
  core/
  routes/
  schemas/
  weights/
web/
  src/
  public/
```

## Backend

```powershell
uv sync
uv run uvicorn api.app:app --reload
```

Endpoints principais:

- `/health`
- `/api/predict`
- `/docs`
- `/redoc`

## Frontend

```powershell
cd web
bun install
bun run dev
```

O frontend conversa com a API local via proxy do Vite. Se precisar apontar para outro backend, use `VITE_API_URL`.

## Modelo

Coloque os artefatos treinados em `api/weights/`. O endpoint de predição já está preparado para trocar o cálculo base por um modelo real depois.
