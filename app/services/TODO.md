# TODO - `app/services/`

Business logic belongs here.

## How to add a service
1. Create/extend a service module (e.g. `order_service.py`).
2. Keep database operations and business rules here.
3. Return domain entities or schema-ready data.
4. Call service methods from routers.

## Rules
- Services should be framework-light (easy to test).
- Avoid direct HTTP concerns (status codes/response formatting) in services.
