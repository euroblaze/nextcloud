"""Per-company Nextcloud configuration.

V18 rewrite: real per-company stored fields (V15 read from
ir.config_parameter, defeating the multi-company claim). All WebDAV
calls now route through `env['nextcloud.client']`.
"""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    nextcloud_url = fields.Char(
        string="Nextcloud URL",
        groups="base.group_system",
        help="Base URL of the Nextcloud server, e.g. https://nc.example.com",
    )
    nextcloud_username = fields.Char(
        string="Nextcloud Username",
        groups="base.group_system",
    )
    nextcloud_password = fields.Char(
        string="Nextcloud App-Password",
        groups="base.group_system",
        help=(
            "Use an app-password generated under "
            "Nextcloud → Settings → Security → 'Devices & sessions'. "
            "Never store the user's main password here."
        ),
    )
    nextcloud_folder_id = fields.Many2one(
        "nextcloud.folder",
        string="Nextcloud Default Folder",
        groups="base.group_system",
    )
    nextcloud_folder = fields.Char(
        string="Nextcloud Default Folder Name",
        related="nextcloud_folder_id.name",
        groups="base.group_system",
    )
    nextcloud_folder_mapping_ids = fields.One2many(
        'nextcloud.folder.mapping', 'company_id',
        string='Nextcloud Folder Mapping',
    )
    nextcloud_last_sync = fields.Datetime()

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------

    def nextcloud_test_connection(self):
        self.ensure_one()
        ok, message = self.env['nextcloud.client'].test_connection(company=self)
        if ok:
            self.sudo().sync_nextcloud_folder()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success' if ok else 'danger',
                'sticky': False,
            },
        }

    def sync_nextcloud_folder(self):
        """Trigger a fresh PROPFIND-based sync of the NC tree into
        nextcloud.folder for this company.
        """
        self.ensure_one()
        return self.env['nextcloud.folder'].sudo().sync_for_company(self)

    # ------------------------------------------------------------------
    # Compatibility surface for legacy callers
    # ------------------------------------------------------------------

    def get_nextcloud_information(self, res_model=False, res_id=False, skip_check=False):
        """Backwards-compatible bag of credentials + folder mapping.

        New code should call `env['nextcloud.client']` directly. This
        method is kept for the V15 chatter/attachment integration that
        is being progressively rewritten.
        """
        self.ensure_one()
        company = self.sudo()
        nc_folder = company.nextcloud_folder_id
        username = company.nextcloud_username
        if not nc_folder:
            nc_folder = self.env['nextcloud.folder'].search([
                ('name', '=', '/'),
                ('username', '=', username),
            ], limit=1)
            if not nc_folder and not skip_check:
                from odoo.exceptions import UserError
                raise UserError(_('Please synchronize Nextcloud folder!'))
        values = {
            'nextcloud_url': company.nextcloud_url,
            'nextcloud_folder': nc_folder.name if nc_folder else '',
            'nextcloud_folder_id': nc_folder,
            'nextcloud_username': username,
            'nextcloud_password': company.nextcloud_password,
        }
        if res_model:
            mapping = company.nextcloud_folder_mapping_ids.filtered(
                lambda m: m.model_name == res_model and m.username == username
            )
            if not mapping:
                mapping = self.env['nextcloud.folder.mapping'].create({
                    'name': res_model,
                    'model_name': res_model,
                    'nextcloud_folder_id': nc_folder.id,
                    'company_id': company.id,
                    'username': username,
                })
            values['folder_mapping'] = mapping
            if res_id:
                for fm in mapping:
                    domain = fm.domain and api.safe_eval.safe_eval(fm.domain) or []
                    if self.env[res_model].search([('id', '=', res_id), *domain]):
                        values['nextcloud_folder'] = fm.nextcloud_folder_id.name
                        values['nextcloud_folder_id'] = fm.nextcloud_folder_id
                        break
        return values
