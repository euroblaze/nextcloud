"""ir.attachment NC integration.

Two flows:

1. **Push to NC** — `attachment.action_upload_to_nextcloud(folder_id=...)`
   uploads bytes via `env['nextcloud.client']`, stores share link, sets
   `nextcloud_attachment=True`. Optionally clears the local `datas`
   payload to keep the Odoo DB lean.

2. **Pull from NC** — `IrAttachment.create_from_nextcloud_path(...)`
   creates a fresh ir.attachment whose payload is downloaded from NC
   and bound to a (res_model, res_id) target.

Public-share creation reuses `nextcloud.client.create_public_share`.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    nextcloud_attachment = fields.Boolean(
        string="Nextcloud Attachment",
        readonly=True,
        copy=False,
    )
    nextcloud_view_link = fields.Char(string="Nextcloud View Link")
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link")
    nextcloud_folder_id = fields.Many2one("nextcloud.folder", string="Nextcloud Folder")

    # ------------------------------------------------------------------
    # Push to NC
    # ------------------------------------------------------------------

    def action_upload_to_nextcloud(self, folder_id=False, clear_local=False):
        """Upload this attachment's bytes to Nextcloud.

        :param folder_id: optional `nextcloud.folder` id to target.
            Falls back to the company's default folder.
        :param clear_local: if True, clear `datas` after upload to
            keep the Odoo DB lean. The `nextcloud_share_link` becomes
            the only authoritative copy.
        :return: dict with `share_link` (and `error` on failure).
        """
        self.ensure_one()
        if self.nextcloud_attachment:
            return {'share_link': self.nextcloud_share_link, 'already_uploaded': True}
        if not self.raw:
            raise UserError(_("Attachment %s has no payload to upload.") % self.name)

        company = (self.company_id or self.env.company).sudo()
        client = self.env['nextcloud.client']
        folder = self.env['nextcloud.folder'].browse(folder_id) if folder_id else False
        if not folder:
            folder = company.nextcloud_folder_id
        folder_path = (folder.name or '').strip('/') if folder else ''
        target = self._next_unique_nc_path(client, folder_path, self.name, company)

        try:
            client.upload(target, bytes(self.raw), company=company)
        except Exception as exc:  # noqa: BLE001
            _logger.exception("NC upload failed for attachment %s", self.id)
            return {'error': str(exc)}

        share_url = (
            f"{company.nextcloud_url.rstrip('/')}"
            f"/remote.php/dav/files/{company.nextcloud_username}/{target}"
        )
        vals = {
            'nextcloud_attachment': True,
            'nextcloud_share_link': share_url,
            'nextcloud_view_link': share_url,
        }
        if folder:
            vals['nextcloud_folder_id'] = folder.id
        if clear_local:
            vals['raw'] = False
        self.write(vals)

        return {'share_link': share_url, 'attachment_id': self.id}

    def action_create_public_share(self):
        """Generate a public-share URL on NC for this attachment."""
        self.ensure_one()
        if not self.nextcloud_attachment or not self.nextcloud_share_link:
            raise UserError(_(
                "This attachment is not on Nextcloud. Upload it first."
            ))
        company = (self.company_id or self.env.company).sudo()
        prefix = (
            f"{company.nextcloud_url.rstrip('/')}"
            f"/remote.php/dav/files/{company.nextcloud_username}/"
        )
        path = self.nextcloud_share_link
        if path.startswith(prefix):
            path = path[len(prefix):]
        url = self.env['nextcloud.client'].create_public_share(
            path, company=company, label=f'{self.name}-{self.id}',
        )
        if not url:
            raise UserError(_("Could not create a public share link on Nextcloud."))
        self.write({'nextcloud_view_link': url})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Public link created"),
                'message': url,
                'type': 'success',
                'sticky': True,
            },
        }

    # ------------------------------------------------------------------
    # Pull from NC
    # ------------------------------------------------------------------

    @api.model
    def create_from_nextcloud_path(self, nc_path, res_model, res_id):
        """Create an ir.attachment whose bytes come from NC at *nc_path*.

        Returns the created attachment record.
        """
        if not nc_path:
            raise UserError(_("No Nextcloud path supplied."))
        company = self.env.company.sudo()
        client = self.env['nextcloud.client']
        try:
            payload = client.download(nc_path, company=company)
        except Exception as exc:  # noqa: BLE001
            raise UserError(_("Failed to fetch %s from Nextcloud: %s") % (nc_path, exc))
        share_url = (
            f"{company.nextcloud_url.rstrip('/')}"
            f"/remote.php/dav/files/{company.nextcloud_username}/"
            f"{nc_path.lstrip('/')}"
        )
        nc_folder = self.env['nextcloud.folder'].search([
            ('name', '=', nc_path),
            ('username', '=', company.nextcloud_username),
        ], limit=1)
        return self.create({
            'name': nc_path.rsplit('/', 1)[-1],
            'raw': payload,
            'res_model': res_model,
            'res_id': int(res_id) if res_id else 0,
            'company_id': company.id,
            'nextcloud_attachment': True,
            'nextcloud_share_link': share_url,
            'nextcloud_view_link': share_url,
            'nextcloud_folder_id': nc_folder.id or False,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _next_unique_nc_path(client, folder_path, filename, company):
        """Pick a path on NC that doesn't already exist.

        Appends `(1).`, `(2).` etc. before the extension on collision.
        """
        base = f"{folder_path}/{filename}" if folder_path else filename
        candidate = base
        attempt = 0
        while client.exists(candidate, company=company):
            attempt += 1
            if '.' in filename:
                stem, dot, ext = filename.rpartition('.')
                candidate_name = f"{stem}({attempt}){dot}{ext}"
            else:
                candidate_name = f"{filename}({attempt})"
            candidate = (
                f"{folder_path}/{candidate_name}" if folder_path else candidate_name
            )
        return candidate
