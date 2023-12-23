import requests
import logging
import xml.etree.ElementTree as ET
from urllib.parse import unquote

from odoo import _, fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    nextcloud_url = fields.Char(string="Nextcloud URL", groups="base.group_system")
    nextcloud_folder_id = fields.Many2one("nextcloud.folder", string="Nextcloud Default Folder",
                                          groups="base.group_system")
    nextcloud_folder = fields.Char(string="Nextcloud Default Folder Name",
                                   related="nextcloud_folder_id.name", groups="base.group_system")
    nextcloud_username = fields.Char(string="Nextcloud Username", groups="base.group_system")
    nextcloud_password = fields.Char(string="Nextcloud Password", groups="base.group_system",
                                     password="True")
    nextcloud_folder_mapping_ids = fields.One2many('nextcloud.folder.mapping', 'company_id',
                                                   'NextCloud Folder Mapping')
    nextcloud_last_sync = fields.Integer()

    def get_nextcloud_information(self, res_model=False, res_id=False, skip_check=False):
        self.ensure_one()
        nextcloud_folder = self.nextcloud_folder_id
        nextcloud_username = self.nextcloud_username
        if not nextcloud_folder:
            nextcloud_folder = self.env['nextcloud.folder'].search([
                ('name', '=', '/'), ('username', '=', nextcloud_username)], limit=1)
            if not nextcloud_folder and not skip_check:
                raise UserError(_('Please synchronize Nextcloud folder!'))
        values = {
            'nextcloud_url': self.nextcloud_url,
            'nextcloud_folder': nextcloud_folder.name if nextcloud_folder else '',
            'nextcloud_folder_id': nextcloud_folder,
            'nextcloud_username': nextcloud_username,
            'nextcloud_password': self.nextcloud_password
        }
        if res_model:
            folder_mapping = self.nextcloud_folder_mapping_ids.filtered(
                lambda x: x.model_name == res_model and x.username == nextcloud_username)
            if not folder_mapping:
                folder_mapping = self.env['nextcloud.folder.mapping'].create({
                    'name': res_model,
                    'model_name': res_model,
                    'nextcloud_folder_id': nextcloud_folder.id,
                    'company_id': self.id,
                    'username': nextcloud_username
                })
            values.update({'folder_mapping': folder_mapping})
            if res_id:
                for f_mapping in folder_mapping:
                    mapping_domain = eval(f_mapping.domain)
                    filter_domain = [('id', '=', res_id)] + mapping_domain
                    check_match_domain = self.env[res_model].search(filter_domain)
                    if check_match_domain:
                        values.update({
                            'nextcloud_folder': f_mapping.nextcloud_folder_id.name,
                            'nextcloud_folder_id': f_mapping.nextcloud_folder_id
                        })
                        break
        return values

    def nextcloud_test_connection(self):
        self.ensure_one()
        request_header = {'OCS-APIRequest': 'true'}
        url = self.sudo().nextcloud_url
        username = self.sudo().nextcloud_username
        password = self.sudo().nextcloud_password
        check_url = url + '/remote.php/dav/files/%s' % username
        check_response = requests.get(check_url, headers=request_header, auth=(username, password))
        status_code = check_response.status_code
        if status_code == 200:
            message = _("Connection Test Successful!")
            type_toast = 'success'
            self.sync_nextcloud_folder()
        else:
            message = _("Connection Test Unsuccessful!")
            type_toast = 'danger'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': type_toast,
                'sticky': False,
            }
        }

    # Action sync all nextcloud folder of root folder
    def sync_nextcloud_folder(self):
        self.ensure_one()
        nextcloud_params = self.sudo().get_nextcloud_information(skip_check=True)
        url = nextcloud_params.get('nextcloud_url')
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        folder = nextcloud_params.get('nextcloud_folder')
        if not url or not username or not password:
            raise ValueError(_('NextCloud account is invalid! Please set up NextCloud account!'))
        url += '/remote.php/dav/files/%s/' % username
        nextcloud_folder = []
        self.send_request_get_folder(url, folder, username, password)
        return nextcloud_folder

    @api.model
    def send_request_get_folder(self, request_url, folder_path, username, password):
        _logger.info("Sync NextCloud folder of %s to Odoo" % folder_path)
        NCFolder = self.env['nextcloud.folder']
        extra_path = '/remote.php/dav/files/%s/' % username
        # Nextcloud WEB DAV payload
        payload = '''<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
<d:prop xmlns:oc="http://owncloud.org/ns">
    <d:resourcetype/>
    <d:getcontenttype/>
    <oc:fileid/>
</d:prop>
</d:propfind>'''
        request_header = {
            'OCS-APIRequest': 'true',
            'Depth': '10000'
        }
        get_folder_response = requests.request("PROPFIND", request_url + folder_path, headers=request_header,
                                               data=payload, auth=(username, password))
        xml_data = get_folder_response.content.decode("utf-8")
        root = ET.fromstring(xml_data)
        for response in root.findall('.//{DAV:}response'):
            href = unquote(response.find('{DAV:}href').text)
            # Handle etag to identify NextCloud folder existed or not
            etag = response.find('.//oc:fileid', namespaces={'oc': 'http://owncloud.org/ns'}).text
            nextcloud_filepath = href.replace(extra_path, '')
            odoo_nc_record = NCFolder.search([('etag', '=', etag),
                                              ('username', '=', username)], limit=1)
            if response.find('{DAV:}propstat/{DAV:}prop/{DAV:}resourcetype/{DAV:}collection') is not None:
                nextcloud_folder = '/' if not nextcloud_filepath else nextcloud_filepath[:-1] 
                if odoo_nc_record:
                    odoo_nc_record.with_context(sync_nextcloud=True).write({
                        'name': nextcloud_folder,
                        'folder': True
                    })
                else:
                    NCFolder.with_context(sync_nextcloud=True).create({
                        'name': nextcloud_folder,
                        'etag': etag,
                        'folder': True,
                        'username': username
                    })
                # NOTE: no need to run recursive based on depth params
                # if nextcloud_folder != folder_path:
                #     self.send_request_get_folder(request_url, nextcloud_folder, username, password)
            else:
                contenttype = response.find('{DAV:}propstat/{DAV:}prop/{DAV:}getcontenttype').text or ''
                if odoo_nc_record:
                    odoo_nc_record.with_context(sync_nextcloud=True).write({
                        'name': nextcloud_filepath,
                        'file_type': contenttype.split('/')[-1]
                        })
                else:
                    NCFolder.with_context(sync_nextcloud=True).create({
                        'name': nextcloud_filepath,
                        'etag': etag,
                        'username': username,
                        'file_type': contenttype.split('/')[-1]
                    })
