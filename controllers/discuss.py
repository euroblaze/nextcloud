from odoo import http
from odoo.http import request

import json

from odoo.addons.mail.controllers.discuss import DiscussController

class DiscussController(DiscussController):

    @http.route('/mail/attachment/upload', methods=['POST'], type='http', auth='public')
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        print("A" * 100)
        print(thread_id)
        print(ufile)
        print(thread_model)
        if isinstance(ufile, str):
            file = json.loads(ufile)
            vals = {
                'name': file["name"],
                'res_id': int(thread_id),
                'res_model': thread_model,
                # 'type': "folder",
                "mimetype": "application/x-directory",
            }
            attachment = request.env['ir.attachment'].create(vals)
            print("B" * 100)
            print(attachment)
            attachmentData = {
                'filename': file["name"],
                'id': attachment.id,
                'mimetype': attachment.mimetype,
                'name': attachment.name,
            }
            return request.make_response(
                data=json.dumps(attachmentData),
                headers=[('Content-Type', 'application/json')]
            )
        else:
            res = super(DiscussController, self).mail_attachment_upload(ufile, thread_id, thread_model, is_pending=is_pending, **kwargs)
            return res