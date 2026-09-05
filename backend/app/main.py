from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, uploads, dashboard, receivables, payables, notifications, ceo

app = FastAPI(
    title="Textile Business Intelligence API",
    version="0.1.0",
    description="Backend for the textile/garment BI platform -- see /docs for endpoints.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # Every Vercel deployment gets its own unique URL
    # (cloth-analyst-<hash>-bizzarooo.vercel.app) in addition to the stable
    # production alias (cloth-analyst.vercel.app). Testing a fresh
    # deployment before it's promoted to production hits the unique URL,
    # which allow_origins alone won't match. This regex covers both.
    allow_origin_regex=r"https://cloth-analyst.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(dashboard.router)
app.include_router(receivables.router)
app.include_router(payables.router)
app.include_router(notifications.router)
app.include_router(ceo.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}