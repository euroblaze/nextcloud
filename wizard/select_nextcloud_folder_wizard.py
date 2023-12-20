from odoo import models, fields


class SelectNextcloudFolderWizard(models.TransientModel):
    _name = 'select.nextcloud.folder.wizard'
    _description = 'Wizard select folder Nextcloud upload'

    attachment_id = fields.Many2one("ir.attachment")
    # res_id = fields.Integer(related='attachment_id.res_id', store=True)
    res_model = fields.Char(related='attachment_id.res_model', store=True)
    company_id = fields.Many2one("res.company", related='attachment_id.company_id')
    folder_id = fields.Many2one('nextcloud.folder', required=True)

    def button_upload(self):
        self.attachment_id.request_upload_file_nextcloud()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
