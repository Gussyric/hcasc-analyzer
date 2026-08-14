# routers/upload.py
# Handles PDF upload and ingestion for both scoresheets and summary docs.

import os
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from parsers.scoresheet_parser import parse_scoresheet
from parsers.summary_parser import (
    parse_player_stats,
    parse_results_by_team,
    parse_round_robin,
    parse_playoff_results,
)

router = APIRouter(prefix="/upload", tags=["upload"])

SUMMARY_DOC_NAMES = {
    "asuplayerstats": "player_stats",
    "asuresultsbyteam": "results_by_team",
    "asuroundrobinresults": "round_robin",
    "asuplayoffresults": "playoff",
}


def _detect_doc_type(filename: str) -> str:
    """
    Detect whether the PDF is a scoresheet or one of the 4 summary docs.
    Returns: 'scoresheet' | 'player_stats' | 'results_by_team' | 'round_robin' | 'playoff'
    """
    normalized = filename.lower().replace(" ", "").replace("_", "").replace("-", "")
    for key, doc_type in SUMMARY_DOC_NAMES.items():
        if key in normalized:
            return doc_type
    return "scoresheet"


@router.post("/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a single HCASC PDF (scoresheet or summary doc)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    doc_type = _detect_doc_type(file.filename)

    # Write to a temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if doc_type == "scoresheet":
            result = parse_scoresheet(tmp_path)
            return JSONResponse(content={
                "status": "skipped" if result.get("skipped") else "ok",
                "type": "scoresheet",
                "result": result,
            })
        elif doc_type == "player_stats":
            result = parse_player_stats(tmp_path)
            return JSONResponse(content={"status": "skipped" if result["skipped"] else "ok",
                                          "type": "player_stats", "rows": result["rows_inserted"]})
        elif doc_type == "results_by_team":
            result = parse_results_by_team(tmp_path)
            return JSONResponse(content={"status": "skipped" if result["skipped"] else "ok",
                                          "type": "results_by_team", "rows": result["rows_inserted"]})
        elif doc_type == "round_robin":
            result = parse_round_robin(tmp_path)
            return JSONResponse(content={"status": "skipped" if result["skipped"] else "ok",
                                          "type": "round_robin", "rows": result["rows_inserted"]})
        elif doc_type == "playoff":
            result = parse_playoff_results(tmp_path)
            return JSONResponse(content={"status": "skipped" if result["skipped"] else "ok",
                                          "type": "playoff", "rows": result["rows_inserted"]})
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parse error: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.post("/batch-scoresheets")
async def batch_upload_scoresheets(files: list[UploadFile] = File(...)):
    """Upload multiple scoresheet PDFs at once."""
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"file": file.filename, "error": "Not a PDF"})
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            result = parse_scoresheet(tmp_path)
            results.append({"file": file.filename, "status": "ok", "result": result})
        except Exception as e:
            results.append({"file": file.filename, "error": str(e)})
        finally:
            os.unlink(tmp_path)

    return JSONResponse(content={"status": "ok", "results": results})
