import requests
import logging

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class NextCloudFolderMapping(models.Model):
    _name = 'nextcloud.folder.mapping'
    _description = 'NextCloud Folder Mapping'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    nextcloud_folder_id = fields.Many2one(
        'nextcloud.folder', string='NextCloud Folder',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', required=True)
    username = fields.Char()
    domain = fields.Text(default='[]', required=True)
    model_name = fields.Selection(selection='_list_all_models',
                                  string='Model', required=True)
    sequence = fields.Integer(default=10)

    @api.model
    def _list_all_models(self):
        self._cr.execute('SELECT model, name FROM ir_model ORDER BY name')
        return self._cr.fetchall()

    # @api.constrains('name')
    # def _constrains_folder_name(self):
    #     special_characters = "!@#$%^&*()-+?_=,<>/"
    #     for rec in self:
    #         if rec.name and rec.name[0] in special_characters:
    #             raise ValidationError(_('The first character must be alphanumberic!'))
