/** @odoo-module **/

import { _t } from 'web.core';
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';
import { AttachmentBox } from '@mail/components/attachment_box/attachment_box'
import { patch } from "@web/core/utils/patch";
const { useRef } = owl.hooks;

patch(AttachmentBox.prototype, "nextcloud.upload_patch", {
    setup() {
        this._super(...arguments);
        this.isDropZoneNextCloudVisible = useDragVisibleDropZone();
        this._FileUploaderNextcloudRef = useRef('FileUploaderNextcloud');
    },

    _onClickAddNextcloud(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        $('input.o_FileUploaderNextcloud').click();
    },

    async _onDropZoneFilesNextCloudDropped(ev) {
        ev.stopPropagation();
        await this._FileUploaderNextcloudRef.comp.uploadFiles(ev.detail.files);
        this.isDropZoneNextCloudVisible.value = false;
    }
});

patch(AttachmentBox.prototype,'document_folder.AttachmentBox',{
    _onClickAdd(ev){
        ev.preventDefault();
        ev.stopPropagation();
        this._fileUploaderRef.el.childNodes[0].removeAttribute('webkitdirectory')
        this._fileUploaderRef.el.childNodes[0].removeAttribute('directory')
        this._fileUploaderRef.comp.openBrowserFileUploader();
    },
    _onClickAddFolder(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._fileUploaderRef.el.childNodes[0].setAttribute('webkitdirectory',true)
        this._fileUploaderRef.el.childNodes[0].setAttribute('directory',true)
        this._fileUploaderRef.comp.openBrowserFileUploader();
    }
})
