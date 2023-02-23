odoo.define('bf_nextcloud.NextcloudUpload', function (require) {
    'use strict';

    const DocumentsKanbanControllerMixin = require('documents.controllerMixin');
    const DocumentsKanbanController = require("documents.DocumentsKanbanController");
    const uploadFucn = require('web.fileUploadMixin');

    DocumentsKanbanControllerMixin._uploadFilesNextcloud = uploadFucn._uploadFilesNextcloud

    DocumentsKanbanController.include({

        events: {
            'click .o_documents_kanban_nextcloud': '_onClickNextcloudDocumentsUpload',
            'click .o_AttachmentBox_buttonAdd': '_onClickNextcloudDocumentsUpload'
        },

        _uploadFilesNextcloud: uploadFucn._uploadFilesNextcloud,

        _onClickNextcloudDocumentsUpload: function (ev) {
            this._uploadFilesHandlerNextCloud(true)(ev);
        },

        _uploadFilesHandlerNextCloud: function (ev) {
            return (ev) => {
                var self = this;
                const recordId = ev.data ? ev.data.id : undefined;
                const $uploadInput = this.hiddenUploadInputFile ?
                    this.hiddenUploadInputFile.off('change') :
                    (this.hiddenUploadInputFile = $('<input>', { type: 'file', name: 'files[]', class: 'o_hidden' }).appendTo(this.$el));
                $uploadInput.attr('multiple', false ? true : null);
                const cleanup = $.prototype.remove.bind($uploadInput);
                $uploadInput.on('change', async changeEv => {
                    await self._uploadFilesNextcloud(changeEv.target.files, { recordId }).finally(cleanup);
                });
                $uploadInput.click();
            };
        },
    });

    var documentMixin = require('documents.viewMixin');
    documentMixin.inspectorFields.push('nextcloud_attachment');
    documentMixin.inspectorFields.push('nextcloud_share_link');

});