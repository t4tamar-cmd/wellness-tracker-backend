import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

from database import create_tables, get_db, Company, ScanLog
from scheduler import start_scheduler, run_scan
from report import generate_weekly_report_pdf


# ── Pydantic response schemas ──────────────────────────────────────────────────

class CompanyOut(BaseModel):
    id: int
    name: str
    url: str
    description: Optional[str]
    business_model: Optional[str]
    ai_usage: bool
    ai_details: Optional[str]
    location: str
    scan_date: datetime

    class Config:
        from_attributes = True


class ScanLogOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    results_found: int
    status: str
    error: Optional[str]

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total: int
    ai_count: int
    business_models: dict
    latest_scan: Optional[datetime]


# ── App lifecycle ──────────────────────────────────────────────────────────────

scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    create_tables()
    scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="Wellness Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://wellness-tracker-tawny.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/companies", response_model=List[CompanyOut])
def list_companies(
    business_model: Optional[str] = None,
    ai_usage: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Company)
    if business_model:
        query = query.filter(Company.business_model == business_model)
    if ai_usage is not None:
        query = query.filter(Company.ai_usage == ai_usage)
    return query.order_by(Company.scan_date.desc()).all()


@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    models: dict = {}
    for c in companies:
        key = c.business_model or "unknown"
        models[key] = models.get(key, 0) + 1

    latest_log = (
        db.query(ScanLog)
        .filter(ScanLog.status == "completed")
        .order_by(ScanLog.finished_at.desc())
        .first()
    )

    return StatsOut(
        total=len(companies),
        ai_count=sum(1 for c in companies if c.ai_usage),
        business_models=models,
        latest_scan=latest_log.finished_at if latest_log else None,
    )


@app.post("/api/scan")
def trigger_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scan)
    return {"message": "Scan started in background"}


@app.get("/api/scans", response_model=List[ScanLogOut])
def list_scans(db: Session = Depends(get_db)):
    return db.query(ScanLog).order_by(ScanLog.started_at.desc()).limit(20).all()


@app.get("/api/report/weekly")
def download_weekly_report():
    pdf_bytes = generate_weekly_report_pdf()
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="No companies found in the last 7 days.")
    filename = f"wellness_report_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
