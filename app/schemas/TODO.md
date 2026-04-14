# TODO - `app/schemas/`

Pydantic request/response contracts live here.

## How to add schemas
- Add input schema(s) for validation (`Create`, `Update`, etc.).
- Add output schema(s) for API responses.
- Use `ConfigDict(from_attributes=True)` for ORM-backed responses.

## Naming convention
- `<Entity>Create`, `<Entity>Update`, `<Entity>Response`
- Keep transport shape separate from DB model shape.

## Rule
- Never return ORM objects directly from endpoints without response schemas.
