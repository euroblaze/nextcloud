import base64
import logging
import requests

from odoo import fields, models, _


class IrAttachments(models.Model):
    _inherit = 'ir.attachment'

    nextcloud_attachment = fields.Boolean(string="Nextcloud Attachment", readonly="True")
    nextcloud_view_link = fields.Char(string="Nextcloud View Link")
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link")
    nextcloud_folder_id = fields.Many2one("nextcloud.folder", string="Nextcloud Folder")

    # NOTE: not delete nextcloud file when delete ir.attachment
    # def unlink(self):
    #     nextcloud_attachments = self.filtered(lambda l: l.nextcloud_attachment)
    #     if nextcloud_attachments:
    #         head = {'OCS-APIRequest': 'true'}
    #         for record in nextcloud_attachments:
    #             nextcloud_params = record.company_id.sudo().get_nextcloud_information()
    #             username = nextcloud_params.get('nextcloud_username')
    #             password = nextcloud_params.get('nextcloud_password')
    #             url = record.nextcloud_share_link
    #             delete_file = requests.delete(
    #                 url,
    #                 headers=head,
    #                 auth=(username, password)
    #             )
    #             logging.info("Delete NextCloud: %s Status %s " % (url, delete_file))
    #     return super().unlink()

    def request_upload_file_nextcloud(self, folder_id=False):
        self.ensure_one()
        NextcloudEnv = self.env['nextcloud.folder']
        company = self.company_id.sudo()
        nextcloud_params = company.get_nextcloud_information(
            res_model=self.res_model, res_id=self.res_id)
        url = nextcloud_params.get('nextcloud_url')
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        folder_mapping = nextcloud_params.get('folder_mapping')
        origin_url = url + f'/remote.php/dav/files/{username}/'
        path_arr = [self.name]
        if not folder_id:
            folder = nextcloud_params.get('nextcloud_folder_id')
            folder_id = folder.id
        else:
            folder_id = int(folder_id)
            folder = NextcloudEnv.browse(folder_id).name
        if folder:
            path_arr.insert(0, folder)
        file_path = '/'.join(path_arr)
        head = {'OCS-APIRequest': 'true'}
        exist, index = False, 1

        while not exist:
            get_url = origin_url + file_path
            get_call = requests.get(get_url, headers=head, auth=(username, password))
            if get_call.status_code == 200:
                file_path = '(%s).'.join(file_path.rsplit('.', 1)) % str(index)
                index += 1
            else:
                exist = True
        share_url = origin_url + file_path
        file_data = base64.b64decode(self.datas)
        response = requests.put(share_url, headers=head, auth=(username, password), data=file_data)
        if response.status_code == 201:
            attachmentData = {
                'nextcloud_attachment': True,
                'nextcloud_share_link': share_url,
                'nextcloud_folder_id': folder_id
            }
            self.write(attachmentData)
            del attachmentData['nextcloud_folder_id']
            company.send_request_get_folder(origin_url, file_path, username, password)
            folder_mapping.write({'nextcloud_folder_id': folder_id})
        else:
            attachmentData = {'error': _("Cannot upload file to NextCloud.")}
        return attachmentData
