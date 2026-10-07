from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.activities import router as activities_router
from app.api.activity_options import router as activity_options_router
from app.api.admin import router as admin_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.goals import router as goals_router
from app.api.insights import router as insights_router
from app.api.routes import router as routes_router
from app.core.config import settings

app = FastAPI(title="EcoTrack API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(activities_router)
app.include_router(activity_options_router)
app.include_router(analytics_router)
app.include_router(goals_router)
app.include_router(insights_router)
app.include_router(routes_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "EcoTrack API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}