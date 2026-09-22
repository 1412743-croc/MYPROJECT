"""Protected administrator page and risk reporting APIs."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.schemas.admin import RiskCaseResponse, RiskReportResponse
from app.services.admin import AdminReportService

router = APIRouter()
admin_page = Path(__file__).resolve().parents[1] / "pages" / "admin.html"


@router.get("/admin.html", include_in_schema=False)
def admin_html(_: Annotated[User, Depends(require_admin)]) -> FileResponse:
    return FileResponse(admin_page)


@router.get("/api/admin/cases", response_model=list[RiskCaseResponse], tags=["admin"])
def list_risk_cases(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RiskCaseResponse]:
    return [RiskCaseResponse.model_validate(item) for item in AdminReportService(db).cases()]


@router.get("/api/admin/reports", response_model=list[RiskReportResponse], tags=["admin"])
def list_risk_reports(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RiskReportResponse]:
    return [RiskReportResponse.model_validate(item) for item in AdminReportService(db).reports()]
