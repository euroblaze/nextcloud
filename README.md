# NextCloud Integration for Odoo

## What is NextCloud?

- NextCloud allows filesharing via links.
- https://nextcloud.com/
- It's Opensource and made in Germany.

## What does this module do?

- Allow file links to be stored/shown on Odoo, while the actual files are stored on NextCloud.

## How does it fit into Odoo?

- Attachments can be uploaded to NextCloud, and links are posted on OdooChatter. This keeps the Odoo ERP lean.

## Where is NextCloud installed?

- NC is installed on a separate machine, recommendably in the same datacenter/cluster.
- Odoo and NC communicate via NC's API, including filetransfer.

## What new developments are foreseen?

1. Better file organisation on each Attachment.
2. Central overview of all NC attachments uploaded.
3. Improve config UI.
4. Improve overall UX and fix edge-case bugs.

## Versions

- Code is available for Odoo v15 and v16
