from odoo import models, fields


class SelectNextcloudFolderWizard(models.TransientModel):
    _name = 'select.nextcloud.folder.wizard'
    _description = 'Wizard select folder Nextcloud upload'

    attachment_id = fields.Many2one("ir.attachment")
    res_id = fields.Integer()
    res_model = fields.Char()
    company_id = fields.Many2one("res.company")

    def confirm(self):
        company = self.company_id
        nextcloud_params = company.sudo().get_nextcloud_information()
        url = nextcloud_params.get('nextcloud_url')
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        folder = nextcloud_params.get('nextcloud_folder')
        return self.quant_id.update_value_ventor(self.qty, self.virtual_location_id.id)