from odoo import _, fields, models
from odoo.exceptions import UserError


class SelectNextcloudFolderWizard(models.TransientModel):
    _name = 'select.nextcloud.folder.wizard'
    _description = 'Wizard select folder Nextcloud upload'

    attachment_id = fields.Many2one("ir.attachment")
    res_model = fields.Char(related='attachment_id.res_model', store=False)
    company_id = fields.Many2one(
        "res.company",
        related='attachment_id.company_id',
    )
    folder_id = fields.Many2one(
        'nextcloud.folder',
        string='Target Folder',
        required=True,
        domain="[('folder', '=', True)]",
    )

    def button_upload(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("No attachment to upload."))
        if hasattr(self.attachment_id, 'request_upload_file_nextcloud'):
            self.attachment_id.request_upload_file_nextcloud()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
