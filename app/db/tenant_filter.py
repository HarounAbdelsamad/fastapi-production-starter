from sqlalchemy import Select


def tenant_query(query: Select, model, tenant_id: str) -> Select:
    return query.where(model.tenant_id == tenant_id)
