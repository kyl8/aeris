import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import APP_DESCRIPTION, APP_NAME, APP_VERSION, REPOSITORY_ROOT, get_settings
from .core.logging import configure_logging
from .routes.climate import router as climate_router
from .routes.detect import router as detect_router
from .routes.history import router as history_router
from .routes.health import router as health_router
from .routes.predict import router as predict_router
from .routes.research import router as research_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("aeris.api")

tags_metadata = [
	{
		"name": "health",
		"description": "Verificações básicas da API.",
	},
	{
		"name": "history",
		"description": "Histórico de predições registradas.",
	},
	{
		"name": "prediction",
		"description": "Endpoints de inferência do projeto.",
	},
	{
		"name": "detection",
		"description": "Detecção de objetos climáticos (sol, nuvens, chuva) com bounding boxes via OWL-ViT.",
	},
	{
		"name": "research",
		"description": "Pipelines de dataset histórico, satélite e fusão multimodal.",
	},
	{
		"name": "climate",
		"description": "Analise temporal de aquecimento local, anomalias e extremos climaticos.",
	},
]

app = FastAPI(
	title=APP_NAME,
	version=APP_VERSION,
	description=APP_DESCRIPTION,
	openapi_tags=tags_metadata,
	docs_url="/docs",
	redoc_url="/redoc",
	swagger_ui_parameters={
		"displayRequestDuration": True,
		"deepLinking": True,
		"docExpansion": "none",
		"filter": True,
		"persistAuthorization": True,
		"defaultModelsExpandDepth": 0,
	},
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.allowed_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
	start_time = perf_counter()
	response = await call_next(request)
	duration_ms = round((perf_counter() - start_time) * 1000, 2)
	logger.info(
		"request_completed",
		extra={
			"method": request.method,
			"path": request.url.path,
			"status_code": response.status_code,
			"duration_ms": duration_ms,
			"client_ip": request.client.host if request.client else None,
		},
	)
	return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
	return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail), "code": exc.status_code})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	logger.warning("request_validation_failed", extra={"path": request.url.path})
	return JSONResponse(status_code=422, content={"error": "Dados de entrada inválidos.", "code": 422})


app.include_router(health_router)
app.include_router(history_router)
app.include_router(predict_router)
app.include_router(detect_router)
app.include_router(research_router)
app.include_router(climate_router)
app.mount(
	"/outputs",
	StaticFiles(directory=REPOSITORY_ROOT / "outputs", check_dir=False),
	name="outputs",
)


@app.get("/redocs", include_in_schema=False)
def legacy_redoc_redirect() -> RedirectResponse:
	return RedirectResponse(url="/redoc", status_code=307)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
	return {
		"service": APP_NAME,
		"version": APP_VERSION,
		"health": "/api/v1/health",
		"docs": "/docs",
		"redoc": "/redoc",
		"redocs": "/redocs",
		"predict": "/api/v1/predict",
		"detect": "/api/v1/detect",
		"history": "/api/v1/history",
		"research": "/api/v1/research/status",
		"climate": "/api/v1/climate/analyze",
	}
