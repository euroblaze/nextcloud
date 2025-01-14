/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { replace } from '@mail/model/model_field_command';
import core from 'web.core';
import { csrf_token, _t } from 'web.core';

const { Component } = owl;
const { useRef } = owl.hooks;
import framework from 'web.framework';

const geAttachmentNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

export class FileUploaderNextcloud extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._fileInputRef = useRef('fileInputNextcloud');
        this._fileUploadId = _.uniqueId('o_FileUploader_fileupload');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get composerView() {
        return this.messaging.models['mail.composer_view'].get(this.props.composerViewLocalId);
    }

    /**
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async uploadFiles(files) {
        await this._performUpload({
            composer: this.composerView && this.composerView.composer,
            files,
            thread: this.thread,
        });
        this._fileInputRef.el.value = '';
    }

    openBrowserFileUploader() {
        this._fileInputRef.el.click();
    }

    get thread() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} param0
     * @param {mail.composer} param0.composer
     * @param {File} param0.file
     * @param {mail.thread} param0.thread
     * @returns {FormData}
     */
    _createFormData({ composer, file, thread }) {
        const formData = new window.FormData();
        formData.append('csrf_token', core.csrf_token);
        formData.append('is_pending', Boolean(composer));
        formData.append('thread_id', thread && thread.id);
        formData.append('thread_model', thread && thread.model);
        formData.append('ufile', file, file.name);
        return formData;
    }

    /**
     * @private
     * @param {Object} param0
     * @param {mail.composer} param0.composer
     * @param {FileList|Array} param0.files
     * @param {mail.thread} param0.thread
     * @returns {Promise}
     */
    async _performUpload({ composer, files, thread }) {
        const uploadingAttachments = new Map();
        for (const file of files) {
            uploadingAttachments.set(file, this.messaging.models['mail.attachment'].insert({
                composer: composer && replace(composer),
                filename: file.name,
                id: geAttachmentNextTemporaryId(),
                isUploading: true,
                mimetype: file.type,
                name: file.name,
                originThread: (!composer && thread) ? replace(thread) : undefined,
            }));
        }
        for (const file of files) {
            const uploadingAttachment = uploadingAttachments.get(file);
            if (!uploadingAttachment.exists()) {
                // This happens when a pending attachment is being deleted by user before upload.
                continue;
            }
            if ((composer && !composer.exists()) || (thread && !thread.exists())) {
                return;
            }
            try {
                const response = await this.env.browser.fetch('/mail/attachment/upload', {
                    method: 'POST',
                    body: this._createFormData({ composer, file, thread }),
                    signal: uploadingAttachment.uploadingAbortController.signal,
                });
                const attachmentData = await response.json();
                if (uploadingAttachment.exists()) {
                    uploadingAttachment.delete();
                }
                if ((composer && !composer.exists()) || (thread && !thread.exists())) {
                    return;
                }
                this._onAttachmentUploaded({ attachmentData, composer, thread });
            } catch (e) {
                if (e.name !== 'AbortError') {
                    throw e;
                }
            }
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} param0
     * @param {Object} attachmentData
     * @param {mail.composer} param0.composer
     * @param {mail.thread} param0.thread
     */
    _onAttachmentUploaded({ attachmentData, composer, thread }) {
        if (attachmentData.error || !attachmentData.id) {
            this.env.services['notification'].notify({
                type: 'danger',
                message: attachmentData.error,
            });
            return;
        }
        const attachment = this.messaging.models['mail.attachment'].insert({
            composer: composer && replace(composer),
            originThread: (!composer && thread) ? replace(thread) : undefined,
            ...attachmentData,
        });
        this.trigger('o-attachment-created', { attachment });
    }

    /**
     * Called when there are changes in the file input.
     *
     * @private
     * @param {Event} ev
     * @param {EventTarget} ev.target
     * @param {FileList|Array} ev.target.files
     */
    async _onChangeAttachment(ev) {
        await this.uploadFiles(ev.target.files);
    }

    async _onChangeAttachmentNextCloud(ev) {
        this._uploadFilesNextcloud(ev.target.files);
    }

    _createXhr() {
        return new window.XMLHttpRequest();
    }

    _makeFileUploadFormDataKeys({ fileUploadId }) {
        return {
            callback: fileUploadId,
        };
    }

    _makeFileUpload(params) {
        const { files, xhr } = params;
        const fileUploadId = _.uniqueId('fileUploadId');
        const formData = new FormData();
        const formDataKeys = this._makeFileUploadFormDataKeys(Object.assign({ fileUploadId }, params));

        formData.append('csrf_token', csrf_token);
        for (const key in formDataKeys) {
            if (formDataKeys[key] !== undefined) {
                formData.append(key, formDataKeys[key]);
            }
        }
        for (const file of files) {
            formData.append('ufile', file);
        }

        return {
            fileUploadId,
            xhr,
            title: files.length === 1
                ? files[0].name
                : _.str.sprintf(_t("%s Files"), files.length),
            type: files.length === 1 ? files[0].type : undefined,
            formData,
        };
    }

    _updateFileUploadProgress(fileUploadId, ev) {
        const { progressCard, progressBar } = this._fileUploads[fileUploadId];
        progressCard && progressCard.update(ev.loaded, ev.total);
        progressBar && progressBar.update(ev.loaded, ev.total);
    }

    async _uploadFilesNextcloud(files, params = {}) {
        var self = this;
        if (!files || !files.length) { return; }
        this._fileUploads = {};
        framework.blockUI();
        await new Promise(resolve => {
            var res_id = this.thread.id;
            var res_model = this.thread.model;
            const xhr = this._createXhr();
            xhr.open('POST', '/web/binary/upload_attachment_nextcloud/' + String(res_model) + '/' + String(res_id));
            const fileUploadData = this._makeFileUpload(Object.assign({ files, xhr }, params));
            const { fileUploadId, formData } = fileUploadData;
            this._fileUploads[fileUploadId] = fileUploadData;
            xhr.upload.addEventListener("progress", ev => {
                self._updateFileUploadProgress(fileUploadId, ev);
            });
            xhr.onload = async () => {
                resolve();
                framework.unblockUI();
                setTimeout("location.reload(true);", 1000);
            };
            xhr.send(formData);
        });
    }

}

Object.assign(FileUploaderNextcloud, {
    props: {
        composerViewLocalId: {
            type: String,
            optional: true,
        },
        threadLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'nextcloud.FileUploaderNextcloud',
});

registerMessagingComponent(FileUploaderNextcloud);