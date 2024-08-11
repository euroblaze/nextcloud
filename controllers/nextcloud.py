import functools
import logging
import json
import xml.etree.ElementTree as ET
import requests
import base64
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

from odoo import http, _
from odoo.http import request, serialize_exception as _serialize_exception

_logger = logging.getLogger(__name__)

CONTENT_MAXAGE = http.STATIC_CACHE_LONG  # menus, translations, static qweb

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

COMMENT_PATTERN = r'Modified by [\s\w\-.]+ from [\s\w\-.]+'


def clean(name):
    return name.replace('\x3c', '')

def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            _logger.exception("An exception occurred during an http request")
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(json.dumps(error))

    return wrap


class BinaryNextCloud(http.Controller):

    @http.route(['/web/binary/upload_attachment_nextcloud/<string:res_model>/<string:res_id>'],
                type='http', auth="user")
    @serialize_exception
    def upload_attachment_nextcloud(self, res_id=None, res_model=None):
        if not res_id or not res_model:
            return json.dumps({})
        record = request.env[res_model].browse(int(res_id))
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        # Check record has field company_id or not
        company = 'company_id' in record and record.company_id or request.env.company
        nextcloud_params = company.sudo().get_nextcloud_information()
        url = nextcloud_params.get('nextcloud_url')
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        folder = nextcloud_params.get('nextcloud_folder')
        head = {'OCS-APIRequest': 'true'}
        for ufile in files:
            filename = ufile.filename
            mydata = ufile.read()
            exist, index = False, 1
            path_arr = [filename]
            if folder:
                path_arr.insert(0, folder)
            file_path = '/'.join(path_arr)
            while not exist:
                get_url = url + f'/remote.php/dav/files/{username}/{file_path}'
                get_call = requests.get(get_url, headers=head, auth=(username, password))
                if get_call.status_code == 200:
                    file_path = '(%s).'.join(file_path.rsplit('.', 1)) % str(index)
                    index += 1
                else:
                    exist = True
            put_url = url + f'/remote.php/dav/files/{username}/{file_path}'
            requests.put(put_url, headers=head, auth=(username, password), data=mydata)
            params = {'shareType': 3, 'publicUpload': True, 'path': file_path}
            post_url = url + '/ocs/v2.php/apps/files_sharing/api/v1/shares'
            post_share_link = requests.post(url=post_url, params=params, headers=head, auth=(username, password))
            xml_data = post_share_link.content.decode("utf-8")
            root = ET.fromstring(xml_data)
            share_url = ""
            for node in root.iter('data'):
                for elem in node.iter():
                    if not elem.tag == node.tag:
                        if elem.tag == 'url':
                            share_url = elem.text
            values = {
                'name': filename,
                'nextcloud_attachment': True,
                'nextcloud_share_link': share_url,
                'nextcloud_view_link': share_url,
                'res_id': res_id,
                'res_model': res_model,
                'company_id': company.id
            }
            attachment = Model.create(values)
            attachment._post_add_create()

    @http.route('/mail/attachment/uploadnextcloud', methods=['POST'], type='http', auth='public')
    def mail_attachment_upload(self, attachment_id, folder_id=False, **kwargs):
        attachment = request.env['ir.attachment'].browse(int(attachment_id))
        if not attachment:
            attachmentData = {'error': _("Missing attachment ID.")}
        if not attachment.x_is_folder:
            attachmentData = attachment.request_upload_file_nextcloud(folder_id)
        else:
            attachmentData = attachment.send_request_create_folder_nextcloud(folder_id)
        # COMMENT: use it when share file to public
        # params = {'shareType': 3, 'publicUpload': True, 'path': file_path}
        # post_url = url + '/ocs/v2.php/apps/files_sharing/api/v1/shares'
        # post_share_link = requests.post(url=post_url, params=params, headers=head, auth=(username, password))
        # xml_data = post_share_link.content.decode("utf-8")
        # root = ET.fromstring(xml_data)
        # share_url = ""
        # for node in root.iter('data'):
        #     for elem in node.iter():
        #         if not elem.tag == node.tag:
        #             if elem.tag == 'url':
        #                 share_url = elem.text

        return request.make_response(
            data=json.dumps(attachmentData),
            headers=[('Content-Type', 'application/json')]
        )
