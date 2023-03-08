# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class DocumentShare(models.Model):
    _inherit = 'documents.share'

    @api.onchange('access_token')
    def _compute_full_url(self):
        for record in self:
            nextcloud_attachment = False
            if record.document_ids:
                if record.document_ids[0].nextcloud_attachment:
                    nextcloud_attachment = True
            if not nextcloud_attachment:
                record.full_url = "%s/document/share/%s/%s" % (record.get_base_url(), record.id, record.access_token)
            else:
                record.full_url = record.document_ids[0].nextcloud_share_link
