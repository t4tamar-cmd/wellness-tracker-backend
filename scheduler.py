import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from database import SessionLocal, Company, ScanLog
from scraper import run_all_searches
from analyzer import analyze_company
from report import generate_and_email_report


def run_scan():
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not tavily_key or not anthropic_key:
        print("[scheduler] Missing API keys — skipping scan.")
        return

    db = SessionLocal()
    log = ScanLog(started_at=datetime.utcnow(), status="running")
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        print("[scheduler] Starting weekly scan...")
        raw_results = run_all_searches(tavily_key)
        count = 0

        for item in raw_results:
            url = item["url"]
            # Skip if already in DB
            existing = db.query(Company).filter(Company.url == url).first()
            if existing:
                continue

            try:
                analysis = analyze_company(
                    title=item["title"],
                    url=url,
                    content=item["content"],
                    api_key=anthropic_key,
                )
                company = Company(
                    name=analysis.get("name", item["title"]),
                    url=url,
                    description=analysis.get("description", ""),
                    business_model=analysis.get("business_model", "unknown"),
                    ai_usage=analysis.get("ai_usage", False),
                    ai_details=analysis.get("ai_details"),
                    raw_snippet=item["content"][:500],
                )
                db.add(company)
                db.commit()
                count += 1
                print(f"[scheduler] Added: {company.name}")
            except Exception as e:
                print(f"[scheduler] Failed to analyze {url}: {e}")

        log.finished_at = datetime.utcnow()
        log.status = "completed"
        log.results_found = count
        db.commit()
        print(f"[scheduler] Scan complete. {count} new companies added.")

    except Exception as e:
        log.status = "failed"
        log.error = str(e)
        log.finished_at = datetime.utcnow()
        db.commit()
        print(f"[scheduler] Scan failed: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_scan,
        trigger=IntervalTrigger(weeks=1),
        id="weekly_scan",
        name="Weekly wellness app scan",
        replace_existing=True,
    )
    scheduler.add_job(
        generate_and_email_report,
        trigger=CronTrigger(day_of_week="sun", hour=9, minute=0),
        id="weekly_report_email",
        name="Weekly report email (Sunday 9am)",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
