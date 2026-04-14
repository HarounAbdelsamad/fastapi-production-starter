# TODO - `app/events/`

Domain event handlers are registered here.

## How to use
1. Define event emitters in business flow via `emit("event.name", ...)`.
2. Register handlers with `@on("event.name")` in this folder.
3. Keep handlers idempotent and side-effect focused (email, audit, cache invalidation).

## Rule
- Do not place core business decisions in event handlers.
