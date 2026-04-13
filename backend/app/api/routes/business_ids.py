from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import AppContainer, get_container
from app.api.security import require_retry_operator, require_retry_view

router = APIRouter(prefix="/business-ids", tags=["Business IDs"])


class BusinessIdResolutionResponse(BaseModel):
    business_id: str
    entity_type: str
    scope: str
    table: str
    key_column: str
    key_value: str | int | None
    record: dict


class BusinessIdMigrationSummary(BaseModel):
    total_rows_checked: int
    rows_missing_business_id: int
    duplicate_business_id_groups: int
    orphan_link_count: int
    status: str


class BusinessIdMigrationTableStatus(BaseModel):
    table: str
    entity_type: str
    key_column: str
    total_rows: int
    rows_with_business_id: int
    rows_missing_business_id: int
    duplicate_business_id_groups: int
    sample_missing_keys: list[str]


class BusinessIdMigrationLinkStatus(BaseModel):
    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    orphan_count: int
    status: str


class BusinessIdMigrationRollbackStatus(BaseModel):
    strategy: str
    database_path: str
    rollback_ready: bool


class BusinessIdMigrationStatusResponse(BaseModel):
    generated_at: str
    summary: BusinessIdMigrationSummary
    tables: list[BusinessIdMigrationTableStatus]
    links: list[BusinessIdMigrationLinkStatus]
    rollback: BusinessIdMigrationRollbackStatus


class BusinessIdMigrationRepairRequest(BaseModel):
    actor: str = "operator"


class BusinessIdMigrationRepairAction(BaseModel):
    name: str
    strategy: str
    repaired_count: int


class BusinessIdMigrationRepairResponse(BaseModel):
    actor: str
    repaired_at: str
    total_repaired: int
    deleted_orphan_rows: list[BusinessIdMigrationRepairAction]
    nullified_optional_links: list[BusinessIdMigrationRepairAction]
    status_after: BusinessIdMigrationStatusResponse


@router.get("/{business_id}", response_model=BusinessIdResolutionResponse)
def resolve_business_id(
    business_id: str,
    container: AppContainer = Depends(get_container),
    _: None = Depends(require_retry_view),
) -> BusinessIdResolutionResponse:
    resolved = container.store.resolve_business_id(business_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Business ID not found")
    return BusinessIdResolutionResponse(**resolved)


@router.get("/migration/status", response_model=BusinessIdMigrationStatusResponse)
def get_business_id_migration_status(
    container: AppContainer = Depends(get_container),
    _: None = Depends(require_retry_view),
) -> BusinessIdMigrationStatusResponse:
    payload = container.store.get_business_id_migration_status()
    return BusinessIdMigrationStatusResponse(**payload)


@router.post("/migration/repair", response_model=BusinessIdMigrationRepairResponse)
def repair_business_id_migration_links(
    request: BusinessIdMigrationRepairRequest,
    container: AppContainer = Depends(get_container),
    _: None = Depends(require_retry_operator),
) -> BusinessIdMigrationRepairResponse:
    payload = container.store.repair_business_id_links(actor=request.actor)
    return BusinessIdMigrationRepairResponse(**payload)
