# Nextcloud Integration for Odoo

## What is Nextcloud?

[Nextcloud](https://nextcloud.com/) is an open-source file-sharing platform
made in Germany. Self-hosted, GDPR-friendly, and a sensible alternative to
storing every attachment inside the Odoo database.

## What does this module do?

- Provides a programmatic Nextcloud client (`env['nextcloud.client']`) for
  any Odoo module to talk to a Nextcloud server over WebDAV: `mkdir`,
  `upload`, `ls`, `download`, `delete`, `create_public_share`.
- Maintains a mirror of the remote tree as `nextcloud.folder` rows so
  pickers, mappings, and rules can target NC paths from Odoo.
- Offers per-company configuration (URL, username, app-password,
  default folder) and a "Test Connection & Sync" button.

## What's new in 18.0

- **Real per-company config**: V15 stored credentials in
  `ir.config_parameter` (global), defeating the multi-company claim.
  Nextcloud V18 stores them per `res.company`.
- **App-password by default**: the password field now expects an NC
  app-password (revocable, scoped). Generate one under
  Nextcloud → Personal Settings → Security → "Devices & sessions".
- **Modern WebDAV client**: `webdav4` replaces hand-rolled XML parsing
  and raw `requests` calls. Retry-on-5xx with exponential backoff
  built into the client wrapper.
- **`queue_job` ready**: long uploads can run via
  `env['nextcloud.client'].with_delay().upload(...)`.
- **V18 view syntax**: `<list>`, no `attrs/states`, modern `<setting>`
  blocks, etc.

## Setup

1. `pip install webdav4` in your Odoo environment.
2. In Nextcloud → Personal Settings → Security, generate an
   app-password; copy it.
3. In Odoo → Settings → Nextcloud (or Settings → Companies →
   {Company} → Nextcloud), fill in URL, username and the app-password.
4. Click "Test Connection & Sync" — green toast confirms WebDAV reach
   and triggers an initial folder mirror.

## Public API

```python
client = env['nextcloud.client']
client.test_connection()                      # → (ok: bool, message)
client.mkdir('Marketing/2026-04-30-spring')   # idempotent
client.upload('Marketing/2026-04-30-spring/letter-001.pdf', pdf_bytes)
client.create_public_share('Marketing/2026-04-30-spring/letter-001.pdf')
```

All methods accept an optional `company=` recordset; defaults to
`env.company`.

## Roadmap (not yet ported from V15)

- Chatter-side attachment offload UI (V15 OWL widgets need a V18
  OWL 2.x rewrite). Tracked in a separate issue.
- Folder-mapping-driven attachment routing on `ir.attachment`.

## Versions

- 15.0 / 16.0 — `main` branch (legacy)
- 18.0 — `18.0` branch (this code)

## License

LGPL-3
