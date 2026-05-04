"""Nextcloud folder mirror in Odoo.

Each `nextcloud.folder` is a row representing a remote path. Sync is
triggered manually (settings or test-connection action) or via the
`sync_for_company` API.

V18 rewrite: WebDAV through `env['nextcloud.client']` (webdav4),
real per-company config, no plaintext credentials in `ir.config_parameter`.
The legacy `download_folder_from_nextcloud` chatter-integration helper
is preserved with V18-safe references; the heavy `document.folder` flow
stays gated on the chatter rewrite.
"""
import base64
import logging
from urllib.parse import unquote, urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NextCloudFolder(models.Model):
    _name = 'nextcloud.folder'
    _description = 'NextCloud Folder'
    _order = 'folder desc, name'

    name = fields.Char(string='Full Path', required=True, index=True)
    folder_name = fields.Char(
        string='Folder/File Name',
        compute='_compute_parent_id', store=True,
    )
    etag = fields.Char(string='ETag')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    parent_id = fields.Many2one(
        'nextcloud.folder', string='Parent Folder',
        compute='_compute_parent_id', store=True,
    )
    child_ids = fields.One2many('nextcloud.folder', 'parent_id', string='Children')
    sequence = fields.Integer(default=10)
    folder = fields.Boolean()
    file_type = fields.Char()
    username = fields.Char(index=True)
    active = fields.Boolean(default=True)
    nextcloud_public_link = fields.Char(string="Nextcloud Public Link", readonly=True)

    _sql_constraints = [
        ('uniq_path_per_user',
         'UNIQUE(name, username)',
         'A NextCloud path must be unique per user.'),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('name')
    def _compute_parent_id(self):
        for rec in self:
            parent_id, folder_name = False, False
            username = rec.username or rec.company_id.sudo().nextcloud_username
            if rec.name == '/':
                folder_name = '/'
            elif rec.name:
                parts = rec.name.split('/')
                if len(parts) > 1:
                    parent_path = '/'.join(parts[:-1]) or '/'
                    parent = self.search([
                        ('name', '=', parent_path),
                        ('username', '=', username),
                    ], limit=1)
                    if parent:
                        parent_id = parent.id
                    folder_name = parts[-1]
                else:
                    folder_name = rec.name
                    root = self.search([
                        ('name', '=', '/'),
                        ('username', '=', username),
                    ], limit=1)
                    parent_id = root.id if root else False
            rec.parent_id = parent_id
            rec.folder_name = folder_name

    # ------------------------------------------------------------------
    # Public sync API
    # ------------------------------------------------------------------

    @api.model
    def sync_for_company(self, company):
        """Walk the NC tree for *company* and upsert nextcloud.folder rows."""
        company = company.sudo()
        client = self.env['nextcloud.client']
        username = company.nextcloud_username
        if not username:
            raise UserError(_("Configure Nextcloud credentials first."))
        existing = self.search([('username', '=', username)])
        keep_etags = set()
        synced = []
        for entry in self._iter_remote_tree(client, company, '/'):
            keep_etags.add(entry['etag'])
            existing_rec = existing.filtered(lambda r: r.etag == entry['etag'])[:1]
            if existing_rec:
                existing_rec.with_context(sync_nextcloud=True).write(entry)
            else:
                self.with_context(sync_nextcloud=True).create({
                    **entry,
                    'username': username,
                    'company_id': company.id,
                })
            synced.append(entry)
        # Drop rows for paths that vanished server-side.
        stale = existing.filtered(lambda r: r.etag and r.etag not in keep_etags)
        if stale:
            stale.unlink()
        company.nextcloud_last_sync = fields.Datetime.now()
        return synced

    @api.model
    def _iter_remote_tree(self, client, company, root_path):
        """Yield {name, folder, etag, file_type} dicts for every entry."""
        try:
            entries = client.ls(root_path, company=company)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Failed to list NC %s: %s", root_path, exc)
            return
        # webdav4.client.ls returns metadata dicts for each entry.
        for entry in entries:
            href = entry.get('name') or entry.get('href') or ''
            href = unquote(urlparse(href).path) if '://' in href else unquote(href)
            relative = self._strip_dav_prefix(href, company)
            is_dir = entry.get('type') == 'directory' or entry.get('is_dir', False)
            etag = entry.get('etag') or entry.get('e_tag') or ''
            content_type = entry.get('content_type') or entry.get('mime_type') or ''
            if is_dir:
                yield {
                    'name': relative or '/',
                    'folder': True,
                    'etag': etag,
                }
                # Recurse one level deeper. webdav4 ls is non-recursive.
                if relative and relative != '/':
                    yield from self._iter_remote_tree(client, company, relative)
            else:
                yield {
                    'name': relative,
                    'folder': False,
                    'etag': etag,
                    'file_type': content_type.split('/')[-1] if content_type else '',
                }

    @staticmethod
    def _strip_dav_prefix(href, company):
        prefix = f"/remote.php/dav/files/{company.nextcloud_username}/"
        if href.startswith(prefix):
            return href[len(prefix):].rstrip('/') or '/'
        return href.rstrip('/') or '/'

    # ------------------------------------------------------------------
    # JS-RPC helpers (used by the file-picker dialog)
    # ------------------------------------------------------------------

    @api.model
    def get_master_data(self, domain, **kwargs):
        res_model = kwargs.get('res_model')
        res_id = kwargs.get('res_id')
        company = self.env.company.sudo()
        username = company.nextcloud_username
        domain = domain + [('username', '=', username)]
        data = self.search_read(
            domain, fields=[],
            order="folder, id, parent_id, folder_name",
        )
        folder_data = self.search_read(
            domain + [('folder', '=', True)], fields=[],
            order="id asc, parent_id, folder_name",
        )
        nc_params = company.get_nextcloud_information(
            res_model=res_model, res_id=res_id,
        )
        default_folder_record = nc_params.get('nextcloud_folder_id')
        if default_folder_record:
            default_folder = default_folder_record.read()[0]
        else:
            default_folder = folder_data[0] if folder_data else []
        return {
            'data': data,
            'folder_data': folder_data,
            'default_folder': default_folder,
        }

    # ------------------------------------------------------------------
    # File operations triggered from the chatter / attachment widget
    # ------------------------------------------------------------------

    @api.model
    def download_file_from_nextcloud(self, files, res_model, res_id, **kwargs):
        """Pull *files* from NC into ir.attachment records bound to
        (res_model, res_id).
        """
        client = self.env['nextcloud.client']
        attachments = self.env['ir.attachment']
        for file in files:
            company_id = file.get('company_id')[0] if file.get('company_id') else self.env.company.id
            company = self.env['res.company'].sudo().browse(company_id)
            filename = file['name']
            try:
                content = client.download(filename, company=company)
            except Exception as exc:  # noqa: BLE001
                _logger.error("NC download failed for %s: %s", filename, exc)
                continue
            attachments |= self.env['ir.attachment'].create({
                'name': filename.rsplit('/', 1)[-1],
                'nextcloud_attachment': True,
                'res_id': res_id,
                'res_model': res_model,
                'company_id': company_id,
                'nextcloud_share_link': f"{company.nextcloud_url}"
                                        f"/remote.php/dav/files/"
                                        f"{company.nextcloud_username}/{filename}",
                'nextcloud_folder_id': file['id'],
                'datas': base64.b64encode(content),
            })
        return attachments.ids

    def get_public_link(self, src_path, res_id, res_model):
        """Return (and cache) a public share link for *src_path*."""
        self.ensure_one()
        company = self.env.company.sudo()
        client = self.env['nextcloud.client']
        # Strip the dav prefix if a full URL was passed.
        prefix = f"{company.nextcloud_url}/remote.php/dav/files/{company.nextcloud_username}/"
        if src_path.startswith(prefix):
            src_path = src_path[len(prefix):]
        label = f"{src_path.rsplit('/', 1)[-1]}_{res_model}_{res_id}"
        url = client.create_public_share(src_path, company=company, label=label)
        if url and self.id:
            self.write({'nextcloud_public_link': url})
        return url
