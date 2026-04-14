# TODO - `app/templates/email/`

Email HTML templates live here.

## How to add a new email template
1. Create `<template_name>.html`.
2. Reference it from sender code (`send_email(..., template_name="...")`).
3. Pass all required template variables via `context`.

## Good practice
- Keep markup simple and client-compatible.
- Include plain fallback text where possible.
