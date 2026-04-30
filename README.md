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

- `/api/v1/health`
- `/api/v1/predict`
- `/api/v1/history`
- `/docs`
- `/redoc`
- `/redocs`

O backend mantém aliases legados para `/health`, `/api/predict` e `/redocs`.

## Frontend

```powershell
cd web
bun install
bun run dev
```

O frontend conversa com a API local e exibe três áreas:

- Dashboard de saúde, histórico e gráficos
- Inferência com upload ou base64
- Documentação embutida com tabs para Swagger UI e ReDoc

Se precisar apontar para outro backend, use `VITE_API_URL`.

## Modelo

Coloque os artefatos treinados em `api/weights/`. O fine-tuning agora usa `prithivMLmods/Weather-Image-Classification` como base e salva o modelo local em `api/weights/aeris-weather-siglip2/`.

Para retreinar:

```powershell
uv run python api/train_cnn.py
```

Se houver um modelo local do SigLIP, a API o carrega primeiro; se não houver, ela ainda tenta o fallback antigo para não derrubar a inferência.
