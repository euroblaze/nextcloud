# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import zipfile
import functools
import logging
import json
import base64
import xml.etree.ElementTree as ET
import requests
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception
from odoo.addons.documents.controllers.main import ShareRoute

_logger = logging.getLogger(__name__)

CONTENT_MAXAGE = http.STATIC_CACHE_LONG  # menus, translations, static qweb

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

COMMENT_PATTERN = r'Modified by [\s\w\-.]+ from [\s\w\-.]+'


def clean(name): return name.replace('\x3c', '')


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


class ShareRouteNextCloud(ShareRoute):

    def _make_zip(self, name, documents):
        """returns zip files for the Document Inspector and the portal.

        :param name: the name to give to the zip file.
        :param documents: files (documents.document) to be zipped.
        :return: a http response to download a zip file.
        """
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for document in self._get_downloadable_documents(documents):
                    if document.type != 'binary':
                        continue
                    if document.nextcloud_attachment:
                        status, content, filename, mimetype, filehash = request.env['ir.http']._binary_record_content(
                            document, field='nextcloud_share_link', filename=None, filename_field='name',
                            default_mimetype='application/octet-stream')
                        content = requests.get("%s/download" % document.nextcloud_share_link).content
                        doc_zip.writestr(filename, content,
                                         compress_type=zipfile.ZIP_DEFLATED)
                    else:
                        status, content, filename, mimetype, filehash = request.env['ir.http']._binary_record_content(
                            document, field='datas', filename=None, filename_field='name',
                            default_mimetype='application/octet-stream')
                        doc_zip.writestr(filename, base64.b64decode(content),
                                         compress_type=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipfile:
            _logger.exception("BadZipfile exception")

        content = stream.getvalue()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)


class BinaryNextCloud(http.Controller):
    @http.route([
        '/web/binary/upload_attachment_nextcloud',
        '/web/binary/upload_attachment_nextcloud/<int:folder_id>'
    ],
        type='http', auth="user")
    @serialize_exception
    def upload_attachment_nextcloud_documents(self, folder_id=False):
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        url = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_url')
        username = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_username')
        password = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_password')
        head = {'OCS-APIRequest': 'true'}
        for ufile in files:
            filename = ufile.filename
            mydata = ufile.read()
            exist, index = False, 1
            while not exist:
                get_url = url + '/remote.php/dav/files/%s/%s' % (username, filename)
                get_call = requests.get(get_url, headers=head, auth=(username, password))
                if get_call.status_code == 200:
                    filename = '(%s).'.join(filename.rsplit('.', 1)) % str(index)
                    index += 1
                else:
                    exist = True
            put_url = url + '/remote.php/dav/files/' + username + '/' + filename
            put_request = requests.put(put_url,
                                       headers=head,
                                       auth=(username, password),
                                       data=mydata)
            params = {'shareType': 3, 'publicUpload': True, 'path': filename}
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
                'res_model': 'documents.document',
            }
            attachment = Model.create(values)
            attachment._post_add_create()
            request.env['documents.document'].sudo().create({
                'attachment_id': attachment.id,
                'folder_id': folder_id,
            })
        return json.dumps({})

    @http.route([
        '/web/binary/upload_attachment_nextcloud/<string:res_model>/<string:res_id>'
    ],
        type='http', auth="user")
    @serialize_exception
    def upload_attachment_nextcloud(self, res_id=None, res_model=None):
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        url = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_url')
        username = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_username')
        password = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_password')
        head = {'OCS-APIRequest': 'true'}
        for ufile in files:
            filename = ufile.filename
            mydata = ufile.read()
            exist, index = False, 1
            while not exist:
                get_url = url + '/remote.php/dav/files/%s/%s' % (username, filename)
                get_call = requests.get(get_url, headers=head, auth=(username, password))
                if get_call.status_code == 200:
                    filename = '(%s).'.join(filename.rsplit('.', 1)) % str(index)
                    index += 1
                else:
                    exist = True
            put_url = url + '/remote.php/dav/files/' + username + '/' + filename
            put_request = requests.put(put_url, headers=head, auth=(username, password), data=mydata)
            params = {'shareType': 3, 'publicUpload': True, 'path': filename}
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
                'res_model': res_model
            }
            attachment = Model.create(values)
            attachment._post_add_create()
