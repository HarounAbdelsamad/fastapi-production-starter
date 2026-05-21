"""
Projects router — shows RBAC guards, feature flag gates, and pagination
using fastapi-production-starter patterns.
"""

from app.core.rbac import require_role
from examples.project_tracker.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from examples.project_tracker.services.project_service import (
    create_project,
    get_projects,
    update_project_status,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.user import User
from app.services.feature_service import is_enabled

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("member")),
) -> ProjectRead:
    project = await create_project(
        db,
        payload,
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
    )
    return ProjectRead.model_validate(project)


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("member")),
) -> list[ProjectRead]:
    # Feature flag gate: new project list UI is behind "projects_v2"
    use_v2 = await is_enabled(db, "projects_v2", user_id=str(current_user.id))
    if use_v2:
        # Future: return enhanced response with extra fields
        pass

    projects = await get_projects(
        db,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=min(limit, 200),
    )
    return [ProjectRead.model_validate(p) for p in projects]


@router.patch("/{project_id}/status", response_model=ProjectRead)
async def change_status(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("member")),
) -> ProjectRead:
    if payload.status is None:
        raise HTTPException(status_code=400, detail="status field required")

    project = await update_project_status(
        db,
        project_id,
        payload.status,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead.model_validate(project)
