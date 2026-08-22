from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, uploads, dashboard

app = FastAPI(
    title="Textile Business Intelligence API",
    version="0.1.0",
    description="Backend for the textile/garment BI platform -- see /docs for endpoints.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(dashboard.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
