/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';
import { FileExploreDialog } from "../views/nextcloud/file_explore_dialog";
import { useEffect, useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";

import core from 'web.core';

registerFieldPatchModel('mail.attachment', 'nextcloud/static/src/js/attachment.js', {
    nextcloud_attachment: attr({
        compute: '_computeNextCloud',
    }),
    nextcloud_share_link: attr({
        compute: '_computeNextCloudShare',
    }),
    isNextCloudUploading: attr({
        default: false,
    }),
    isDocumentFolder: attr({
        compute: '_computeDocumentFolder',
    }),
});

registerClassPatchModel('mail.attachment', 'nextcloud/static/src/js/attachment.js', {
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

registerInstancePatchModel('mail.attachment', 'nextcloud/static/src/js/attachment.js', {
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

    _computeDocumentFolder() {
        return this.mimetype === 'document/folder';
    },

    /**
     * @private
     * @returns {boolean}
     */
    _computeIsViewable() {
        const res = this._super(...arguments);
        return res || this.isDocumentFolder
    },
    /**
 * @override
 */
    _created() {
        this._super(...arguments);
        // defined onClickUpload
        this.onClickUploadNextcloud = this.onClickUploadNextcloud.bind(this);
        this.onClickPublicLink = this.onClickPublicLink.bind(this);
    },

    /**
     * Handles click on upload icon.
     *
     * @param {MouseEvent} ev
     */
    onClickUploadNextcloud(ev) {
        ev.stopPropagation();
        var self = this;
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t("Choose Nextcloud Folder to Upload"),
            res_model: 'select.nextcloud.folder.wizard',
            view_mode: 'file_explore_view',
            views: [[false, 'file_explore_view']],
            target: 'new',
            context: {
                attachment_id: this.id,
                fileexplore_mode: 'upload',
                origin_resmodel: this.originThread.model,
                origin_resid: this.originThread.id,
            },
            res_id: false,
            domain: [],
        };
        return this.env.bus.trigger('do-action', {
            action,
            options: {
                on_close: () => {
                    self.originThread.refresh();
                },
            },
        });
        // this.UploadAttachmentNextcloud();
    },

    /**
     * @private
     * @param {Object} param0
     * @returns {FormData}
     */
    _createFormDataNextcloud() {
        const formData = new window.FormData();
        formData.append('csrf_token', core.csrf_token);
        formData.append('attachment_id', this.id);
        formData.append('res_id', this.originThread.id);
        formData.append('res_model', this.originThread.model)
        return formData;
    },

    async UploadAttachmentNextcloud() {
        var self = this;
        self.update({'isNextCloudUploading': true})
        try {
            const response = await this.env.browser.fetch('/mail/attachment/uploadnextcloud', {
                method: 'POST',
                body: this._createFormDataNextcloud()
            });
            const attachmentData = await response.json();
            if (attachmentData.error) {
                self.env.services['notification'].notify({
                    type: 'danger',
                    message: attachmentData.error,
                });
                self.update({'isNextCloudUploading': false})
                return;
            }
            self.update(attachmentData);
        } catch (e) {
            if (e.name !== 'AbortError') {
                throw e;
            }
        }
    },

    folderDownload(folder_zip_id) {
        var downloadUrl = '#'
        if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
            downloadUrl = `/mail/channel/${this.originThread.id}/attachment/${folder_zip_id}?download=true`;
        } else {
            const accessToken = this.accessToken ? `access_token=${this.accessToken}&` : '';
            downloadUrl = `/web/content/ir.attachment/${folder_zip_id}/datas?${accessToken}download=true`;
        }
        const downloadLink = document.createElement('a');
        downloadLink.setAttribute('href', downloadUrl);
        // Adding 'download' attribute into a link prevents open a new tab or change the current location of the window.
        // This avoids interrupting the activity in the page such as rtc call.
        downloadLink.setAttribute('download','');
        downloadLink.click();
    },
    /**
     * Handles click on download icon.
     *
     * @param {MouseEvent} ev
     */
    async onClickDownload(ev) {
        ev.stopPropagation();
        if (!this.isDocumentFolder) {
            this.download();
        } else {
            const response = await this.env.browser.fetch('/document/folder/download', {
                method: 'POST',
                body: this._createFormDataNextcloud()
            });
            const attachmentData = await response.json();
            if (attachmentData.folder_download_id) {
                this.folderDownload(attachmentData.folder_download_id)
            }
        }
    },

    async onClickPublicLink(ev){
        ev.stopPropagation()
        const response = await this.env.browser.fetch('/mail/attachment/getPublicLink', {
            method: 'POST',
            body: this._createFormDataNextcloud()
        });
        const publicLink = await response.json();
        if (!publicLink) {
            this.env.services['notification'].notify({
                type: 'danger',
                message: "Get Public Link Failed",
            });
        } else {
            browser.navigator.clipboard.writeText(
                `${publicLink['nc_public_link']}`
            );
            this.env.services['notification'].notify({
                message: "Copy public link successfully",
                type: 'success',
            });
        }
    }
});
