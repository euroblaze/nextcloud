/** @odoo-module alias=web.NextcloudFileUploadMixin **/

/**
 * Mixin to be used in view Controllers to manage uploads and generate progress bars.
 * supported views: kanban, list
 * NextCloud Version
 */

import ProgressBarMixin from 'web.fileUploadMixin';

ProgressBarMixin._getFileUploadRouteNextcloud = function _getFileUploadRouteNextcloud() {
    return '/web/binary/upload_attachment_nextcloud';
};

ProgressBarMixin._uploadFilesNextcloud = async function _uploadFilesNextcloud(files, params = {}) {
    if (!files || !files.length) { return; }

    await new Promise(resolve => {
        var folderId = this.searchModel.get('selectedFolderId');
        const xhr = this._createXhr();
        if (folderId) {
            xhr.open('POST', '/web/binary/upload_attachment_nextcloud/' + String(folderId));
        } else {
            xhr.open('POST', '/web/binary/upload_attachment_nextcloud');
        }
        const fileUploadData = this._makeFileUpload(Object.assign({ files, xhr }, params));
        const { fileUploadId, formData } = fileUploadData;
        this._fileUploads[fileUploadId] = fileUploadData;
        xhr.upload.addEventListener("progress", ev => {
            this._updateFileUploadProgress(fileUploadId, ev);
        });
        const progressPromise = this._onBeforeUpload();
        xhr.onload = async () => {
            await progressPromise;
            resolve();
            this._onUploadLoad({ fileUploadId, xhr });
        };
        xhr.onerror = async () => {
            await progressPromise;
            resolve();
            this._onUploadError({ fileUploadId, xhr });
        };
        xhr.send(formData);
    });
};
