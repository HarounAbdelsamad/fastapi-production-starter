from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.pagination import PaginatedResponse, PaginationParams


async def paginate(
    db: AsyncSession,
    query: Select,
    params: PaginationParams,
) -> PaginatedResponse:
    count_query = select(func.count()).select_from(query.subquery())
    total = int(await db.scalar(count_query) or 0)
    result = await db.execute(query.offset(params.skip).limit(params.limit))
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        skip=params.skip,
        limit=params.limit,
        has_more=(params.skip + params.limit) < total,
    )
