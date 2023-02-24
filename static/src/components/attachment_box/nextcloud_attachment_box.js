/** @odoo-module **/

import { csrf_token, _t } from 'web.core';
import { registerNewModel } from '@mail/model/model_core';
import { AttachmentBox } from '@mail/components/attachment_box/attachment_box'
import { FileUploader } from '@mail/components/file_uploader/file_uploader'
import { AttachmentCard } from '@mail/components/attachment_card/attachment_card'
import { AttachmentImage } from '@mail/components/attachment_image/attachment_image'
import { patch } from "@web/core/utils/patch";
import { factory } from '@mail/models/attachment/attachment'

const NextcloudUpload = require('bf_nextcloud.NextcloudUpload');

patch(AttachmentBox.prototype, "nextcloud.upload_patch", {
    _onClickAddNextcloud(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        $('input.o_FileUploaderNextcloud').click();
    }
});
