"""
Project service — shows how to integrate audit log, webhooks, and OTel spans
into a real business service built on top of fastapi-production-starter.
"""

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.services.webhook_service import dispatch_event
from examples.project_tracker.models.project import Project
from examples.project_tracker.schemas.project import ProjectCreate, ProjectRead

tracer = trace.get_tracer(__name__)


async def create_project(
    db: AsyncSession,
    payload: ProjectCreate,
    *,
    tenant_id: str,
    owner_id: int,
) -> Project:
    with tracer.start_as_current_span("project.create"):
        project = Project(
            tenant_id=tenant_id,
            owner_id=owner_id,
            **payload.model_dump(),
        )
        db.add(project)
        await db.flush()
        await log_event(
            db,
            actor_id=owner_id,
            action="project.created",
            resource_type="project",
            resource_id=str(project.id),
            metadata={"name": project.name, "tenant_id": tenant_id},
        )
        await db.commit()
        await db.refresh(project)
        return project


async def get_projects(
    db: AsyncSession,
    *,
    tenant_id: str,
    skip: int = 0,
    limit: int = 50,
) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_project_status(
    db: AsyncSession,
    project_id: int,
    new_status: str,
    *,
    tenant_id: str,
    actor_id: int,
) -> Project | None:
    with tracer.start_as_current_span("project.status_change"):
        result = await db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_id == tenant_id,
                Project.deleted_at.is_(None),
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            return None

        old_status = project.status
        project.status = new_status
        await db.flush()

        await log_event(
            db,
            actor_id=actor_id,
            action="project.status_changed",
            resource_type="project",
            resource_id=str(project_id),
            metadata={"old_status": old_status, "new_status": new_status},
        )

        # Dispatch webhook so subscribers can react to status transitions
        await dispatch_event(
            db,
            event="project.status_changed",
            payload={
                "project_id": project_id,
                "tenant_id": tenant_id,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        await db.commit()
        await db.refresh(project)
        return project
