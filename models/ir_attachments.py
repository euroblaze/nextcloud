# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrAttachments(models.Model):
    _inherit = ['ir.attachment']

    nextcloud_attachment = fields.Boolean(string="Nextcloud Attachment", readonly="True")
    nextcloud_view_link = fields.Char(string="Nextcloud View Link")
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link")


class Document(models.Model):
    _inherit = 'documents.document'

    nextcloud_attachment = fields.Boolean(string="Nextcloud Attachment", related='attachment_id.nextcloud_attachment')
    nextcloud_view_link = fields.Char(string="Nextcloud View Link", related='attachment_id.nextcloud_view_link')
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link", related='attachment_id.nextcloud_share_link')
