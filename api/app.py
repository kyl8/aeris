from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import ALLOWED_ORIGINS, API_PREFIX, APP_DESCRIPTION, APP_NAME, APP_VERSION
from .routes.health import router as health_router
from .routes.predict import router as predict_router

tags_metadata = [
	{
		"name": "health",
		"description": "Verificações básicas da API.",
	},
	{
		"name": "prediction",
		"description": "Endpoints de inferência do projeto.",
	},
]

app = FastAPI(
	title=APP_NAME,
	version=APP_VERSION,
	description=APP_DESCRIPTION,
	openapi_tags=tags_metadata,
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(predict_router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
	return {
		"service": APP_NAME,
		"version": APP_VERSION,
		"health": "/health",
		"docs": "/docs",
		"redoc": "/redoc",
		"predict": f"{API_PREFIX}/predict",
	}
