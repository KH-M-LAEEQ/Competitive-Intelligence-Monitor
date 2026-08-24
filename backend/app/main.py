from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import competitor
from app.core.config import settings
from app.routers import auth
from app.routers import change_log
from app.routers import workspace
from app.routers import surfaces
from app.routers import insights
from app.routers import briefings
from app.routers import approvals
from app.routers import audit
from app.routers import battlecards
from app.routers import response_library
from app.routers import integrations
from app.routers import company_profiles
from app.routers import exports
from app.routers import gdpr
from app.routers import budget
from app.routers import traffic
from app.routers import own_site
from app.routers import site_summary
from app.routers import category_price
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspace.router)
app.include_router(competitor.router)
app.include_router(surfaces.router)
app.include_router(change_log.router)
app.include_router(insights.router)
app.include_router(briefings.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(battlecards.router)
app.include_router(response_library.router)
app.include_router(integrations.router)
app.include_router(company_profiles.router)
app.include_router(exports.router)
app.include_router(gdpr.router)
app.include_router(budget.router)
app.include_router(traffic.router)
app.include_router(own_site.router)
app.include_router(site_summary.router)
app.include_router(category_price.router)
@app.get("/")
def home():
    return {
        "status": "running"
    }
