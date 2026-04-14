# TODO - `app/routers/`

HTTP endpoint modules live here.

## How to add a new router
1. Create file (e.g. `orders.py`) and define `router = APIRouter()`.
2. Add endpoint functions with proper response models.
3. Use dependencies for auth/permissions (`Depends(...)`).
4. Keep handlers thin; call service layer.
5. Register router in `app/main.py` with prefix and tags.

## Good practices
- Use versioned paths (`/api/v1/...`).
- Return consistent error behavior (handled centrally).
- Add tests for each route path and failure mode.
