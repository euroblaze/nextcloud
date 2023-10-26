/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel
} from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.thread', 'nextcloud/static/src/js/nextcloud_attachments.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------
    /**
     * @override
     */
    async fetchAttachments() {
        let attachmentsData = await this.async(() => this.env.services.rpc({
            model: 'ir.attachment',
            method: 'search_read',
            domain: [
                ['res_id', '=', this.id],
                ['res_model', '=', this.model],
            ],
            fields: ['id', 'name', 'mimetype', 'nextcloud_attachment', 'nextcloud_share_link'],
            orderBy: [{name: 'id', asc: false}],
        }, {shadow: true}));
        this.update({
            originThreadAttachments: insertAndReplace(attachmentsData),
        });
        this.update({ areAttachmentsLoaded: true });
    }
});
