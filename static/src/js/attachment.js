/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';
import { useAutofocus, useService } from "@web/core/utils/hooks";

registerFieldPatchModel('mail.attachment', 'bf_nextcloud/static/src/js/attachment.js', {
    nextcloud_attachment: attr({
        compute: '_computeNextCloud',
    }),
    nextcloud_share_link: attr({
        compute: '_computeNextCloudShare',
    }),
});

registerClassPatchModel('mail.attachment', 'bf_nextcloud/static/src/js/attachment.js', {
    /**
     * @override
     */
    convertData(data) {
        const res = this._super(data);
        if ('nextcloud_attachment' in data) {
            res.nextcloud_attachment = data.nextcloud_attachment;
        }
        if ('nextcloud_share_link' in data) {
            res.nextcloud_share_link = data.nextcloud_share_link;
        }
        return res;
    },
});

registerInstancePatchModel('mail.attachment', 'bf_nextcloud/static/src/js/attachment.js', {
    _computeNextCloud() {
        const nextcloud_attachment = this.nextcloud_attachment;
        if (nextcloud_attachment) {
            return nextcloud_attachment;
        }
        return clear();
    },

    _computeNextCloudShare() {
        const nextcloud_share_link = this.nextcloud_share_link;
        if (nextcloud_share_link) {
            return nextcloud_share_link;
        }
        return clear();
    },



});