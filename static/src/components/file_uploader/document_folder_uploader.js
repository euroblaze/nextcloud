/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import {
    registerFieldPatchModel,
    registerInstancePatchModel
} from '@mail/model/model_core';
const { Component, hooks, useState } = owl;
const {useRef} = hooks;
import { attr } from '@mail/model/model_field';
import { insertAndReplace, clear, insert, replace } from '@mail/model/model_field_command';
import { FileUploader } from '@mail/components/file_uploader/file_uploader';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const geAttachmentNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

patch(FileUploader.prototype,'nextcloud/static/src/components/file_uploader/document_folder_uploader.js',{
    getParentFolder(files) {
        if (files.length === 0) {
            return '';
        } else {
            const firstFile = files[0];
            const webkitPath = firstFile.webkitRelativePath;
            if (webkitPath.length === 0) {
                return '';
            }
            if (webkitPath.includes('/')) {
                const parentFName = webkitPath.split('/')[0];
                return {
                    'parentFName': parentFName,
                    'totalFiles': files.length
                };
            }
        }
    },

    async uploadFolder(files, folder) {
        await this._performUploadFolder({
            composer: this.composerView && this.composerView.composer,
            files,
            thread: this.thread,
            folder: folder
        });
        this._fileInputRef.el.value = '';
    },

    _createFormDataFolder({ composer, files, folder, thread }) {
    const formData = new window.FormData();
    formData.append('csrf_token', odoo.csrf_token);
    formData.append('is_pending', Boolean(composer));
    formData.append('thread_id', thread && thread.id);
    formData.append('thread_model', thread && thread.model);
    formData.append('folder', JSON.stringify(folder));

    for (let i = 0; i < files.length; i++) {
        // Use template literals to construct the key
        formData.append('ufiles_'+i, files[i], files[i].webkitRelativePath || files[i].name);
    }

    return formData;
},

    async _performUploadFolder({ composer, files, thread, folder}) {
        const uploadingFolders = new Map();
        uploadingFolders.set(folder, this.messaging.models['mail.attachment'].insert({
            composer: composer && replace(composer),
            filename: folder.parentFName,
            id: geAttachmentNextTemporaryId(),
            isUploading: true,
            mimetype: 'document/folder',
            name: folder.parentFName,
            originThread: (!composer && thread) ? replace(thread) : undefined,
        }));
        if (folder) {
            const uploadingFolder = uploadingFolders.get(folder);
            if ((composer && !composer.exists()) || (thread && !thread.exists())) {
                return;
            }
            try {
                const response = await this.env.browser.fetch('/document/folder/upload', {
                    method: 'POST',
                    body: this._createFormDataFolder({ composer, files, folder, thread }),
                    signal: uploadingFolder.uploadingAbortController.signal,
                });
                const attachmentData = await response.json();
                if (uploadingFolder.exists()) {
                    uploadingFolder.delete();
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
    },

    async _onChangeAttachment(ev) {
        console.log(ev)
        if (!this.getParentFolder(ev.target.files)) {
          await this.uploadFiles(ev.target.files);
        }else{
            await this.uploadFolder(ev.target.files, this.getParentFolder(ev.target.files))
        }
    }
})