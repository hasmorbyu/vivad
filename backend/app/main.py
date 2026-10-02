from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import auth as auth_api
from .api import cases as cases_api
from .api import dashboard as dashboard_api
from .api import decisions as decisions_api
from .api import evidence as evidence_api
from .api import graph as graph_api
from .api import health as health_api
from .api import hearings as hearings_api
from .api import intel as intel_api
from .api import journey as journey_api
from .api import meta as meta_api
from .api import notifications as notifications_api
from .api import parties as parties_api
from .api import reports as reports_api
from .api import reviews as reviews_api
from .api import search as search_api
from .api import statements as statements_api
from .config import get_settings
from .db import init_db
from .seed import seed_demo_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if get_settings().seed_demo_users:
        seed_demo_users()
    yield


app = FastAPI(title="VIVAD", description="Verified Intake & Validation for Assisted Dispute-resolution", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_api.router)
app.include_router(auth_api.router)
app.include_router(cases_api.router)
app.include_router(dashboard_api.router)
app.include_router(meta_api.router)
app.include_router(parties_api.router)
app.include_router(statements_api.router)
app.include_router(evidence_api.router)
app.include_router(intel_api.router)
app.include_router(graph_api.router)
app.include_router(journey_api.router)
app.include_router(reviews_api.router)
app.include_router(hearings_api.case_router)
app.include_router(hearings_api.hearing_router)
app.include_router(notifications_api.router)
app.include_router(decisions_api.router)
app.include_router(reports_api.router)
app.include_router(search_api.router)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    # Never leak raw stack traces; the frontend shows a plain-language message.
    return JSONResponse({"detail": f"INTERNAL ERROR: {type(exc).__name__}: {exc}"}, status_code=500)
