# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import copy
import datetime
import functools
import hashlib
import io
import itertools
import json
import logging
import operator
import os
import re
import sys
import tempfile
import unicodedata
from collections import OrderedDict, defaultdict
import json
import xml.etree.ElementTree as ET

import babel.messages.pofile
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from lxml import etree, html
from markupsafe import Markup
from werkzeug.urls import url_encode, url_decode, iri_to_uri

import odoo
import odoo.modules.registry
from odoo.api import call_kw
from odoo.addons.base.models.ir_qweb import render as qweb_render
from odoo.modules import get_resource_path, module
from odoo.tools import html_escape, pycompat, ustr, apply_inheritance_specs, lazy_property, osutil
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _
from odoo.tools.misc import str2bool, xlsxwriter, file_open, file_path, get_lang
from odoo.tools.safe_eval import safe_eval, time
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.models import check_method_name
from odoo.service import db, security
import requests

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


class BinaryNextCloud(http.Controller):
    @http.route([
        '/web/binary/upload_attachment_nextcloud',
        '/web/binary/upload_attachment_nextcloud/<string:res_model>/<string:res_id>'
    ],
        type='http', auth="user")
    @serialize_exception
    def upload_attachment_nextcloud(self, ufile, callback=None, res_id=None, res_model=None, **kw):
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
                'nextcloud_view_link': 'test',
                'res_model': 'documents.document',
            }
            if res_id:
                values.update({'res_id': res_id})
            if res_model:
                values.update({'res_model': res_model})
            attachment = Model.create(values)
            attachment._post_add_create()
            folder_id = kw.get('folder_id', 1)
            if folder_id == 'false' or not isinstance(folder_id, int):
                folder_id = 1
            request.env['documents.document'].sudo().create({
                'attachment_id': attachment.id,
                'folder_id': folder_id,
            })
