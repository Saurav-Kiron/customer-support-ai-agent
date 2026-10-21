import os
import time
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from agent import ModelFailure, Ollama, POLICIES, analyze
from store import Conflict, Missing, Store

ROOT = Path(__file__).parent
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TicketInput(BaseModel):
    subject: Text = Field(max_length=160)
    body: Text = Field(max_length=6000)


class ActionInput(BaseModel):
    revision: int = Field(ge=1)


class ApprovalInput(ActionInput):
    reply: Text = Field(max_length=2500)


class RejectInput(ActionInput):
    note: Text = Field(max_length=500)


def create_app(db_path=None, model=None):
    store = Store(db_path or Path(os.getenv("SUPPORT_DATA_DIR", ROOT / "data")) / "support.db")
    provider = model or Ollama()
    app = FastAPI(title="Support Studio", version="1.0.0")
    app.state.store = store

    @app.middleware("http")
    async def local_write_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin writes are disabled."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Missing)
    async def missing_handler(request, exc):
        return JSONResponse({"detail": "Ticket not found."}, status_code=404)

    @app.exception_handler(Conflict)
    async def conflict_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ModelFailure)
    async def model_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.get("/")
    def home():
        return FileResponse(ROOT / "static/index.html")

    @app.get("/health")
    def health():
        return {"status": "running", "delivery": "simulation-only", "mode": "local-single-user"}

    @app.get("/policies")
    def policies():
        return POLICIES

    @app.get("/tickets")
    def list_tickets():
        return store.list()

    @app.post("/tickets", status_code=201)
    def create_ticket(data: TicketInput):
        return store.create(data.subject, data.body)

    @app.get("/tickets/{ticket_id}")
    def get_ticket(ticket_id: UUID):
        return store.get(str(ticket_id))

    @app.post("/tickets/{ticket_id}/analyze")
    def analyze_ticket(ticket_id: UUID, data: ActionInput):
        ticket = store.get(str(ticket_id))
        if ticket["revision"] != data.revision or ticket["status"] not in {"new", "rejected"}:
            raise Conflict("Only a current new or rejected ticket can be analyzed.")
        start = time.monotonic()
        result = analyze(ticket, provider)
        result["elapsed_seconds"] = round(time.monotonic() - start, 2)
        # Revision is checked again after the model call to reject concurrent/stale results.
        return store.transition(str(ticket_id), data.revision, {"new", "rejected"},
                                "escalated" if result["escalate"] else "review",
                                "analyzed", analysis=result, reply=result["draft"])

    @app.post("/tickets/{ticket_id}/approve")
    def approve(ticket_id: UUID, data: ApprovalInput):
        return store.transition(str(ticket_id), data.revision, {"review"}, "approved", "approved", reply=data.reply)

    @app.post("/tickets/{ticket_id}/reject")
    def reject(ticket_id: UUID, data: RejectInput):
        return store.transition(str(ticket_id), data.revision, {"review", "approved"},
                                "rejected", "rejected", note=data.note)

    @app.post("/tickets/{ticket_id}/simulate-send")
    def send(ticket_id: UUID, data: ActionInput):
        return store.transition(str(ticket_id), data.revision, {"approved"},
                                "sent", "simulated_delivery", deliver=True)

    @app.post("/tickets/{ticket_id}/resolve")
    def resolve(ticket_id: UUID, data: RejectInput):
        return store.transition(str(ticket_id), data.revision, {"escalated"},
                                "resolved", "specialist_resolution", note=data.note)

    return app


app = create_app()
