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
- `/api/v1/research/status`
- `/api/v1/climate/analyze`
- `/api/v1/climate/baixada-santista/analyze`
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
- Tempo real com webcam, captura periódica de frames e `persist=false` para não poluir o histórico
- Explicabilidade da IA com ranking de classes, perfil visual, heatmap e alertas de confiabilidade
- Pipeline de pesquisa, geração de CSV e análise climática regional
- Documentação embutida com tabs para Swagger UI e ReDoc

Se precisar apontar para outro backend, use `VITE_API_URL`.

## Modelo

Coloque os artefatos treinados em `api/weights/`. O fine-tuning agora usa `prithivMLmods/Weather-Image-Classification` como base e salva o modelo local em `api/weights/aeris-weather-siglip2/`.

Para retreinar:

```powershell
uv run python api/train_cnn.py
```

Se houver um modelo local do SigLIP, a API o carrega primeiro; se não houver, ela ainda tenta o fallback antigo para não derrubar a inferência.

## Pipeline escalavel de dados

O pacote `aeris/` contem a nova arquitetura de longo prazo para dataset multimodal:

```text
datasets/
  raw/
    sentinel2/
    landsat/
    weather/
    metadata/
  processed/
    images/
    thumbnails/
    tiles/
    normalized/
    augmented/
  labels/
    automatic/
    manual/
    verified/
  parquet/
  cache/
  exports/
```

ERA5/Open-Meteo entram somente como contexto meteorologico, reanalysis e features tabulares. Eles nao sao tratados como imagens.

Para criar a estrutura:

```powershell
uv run python -m aeris.cli init-dirs --dataset-root datasets
```

## Analise climatica da Baixada Santista

A analise historica usa Open-Meteo Historical Weather API com ERA5/ERA5-Land, agregando dados horarios por cidade e por regiao. Ela gera CSV, Parquet quando `pyarrow` esta instalado, JSON, graficos e relatorios Markdown/HTML.

Execucao completa:

```powershell
uv run python -m aeris.cli analyze-baixada `
  --dataset-root datasets `
  --output-root outputs `
  --start-date 1940-01-01 `
  --end-date 2026-05-18 `
  --source-model era5
```

Smoke test sem baixar tudo:

```powershell
uv run python -m aeris.cli analyze-baixada --max-batches 2
```

Saidas principais:

```text
outputs/baixada_santista/
  climate_timeseries.csv
  climate_timeseries.parquet
  annual_summary.csv
  monthly_summary.csv
  trend_analysis.json
  report.md
  report.html
  plots/
```

A conclusao do relatorio usa valores reais calculados: slope em C/decada, intervalo de confianca, p-value, R2 e cobertura dos dados. A linguagem diferencia tendencia regional, aquecimento global, urbanizacao/ilha de calor, variabilidade natural e limitacoes de reanalysis.

Tambem ha endpoint:

- `POST /api/v1/climate/baixada-santista/analyze`
