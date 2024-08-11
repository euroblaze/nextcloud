/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear, insert, replace, insertAndReplace } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.attachment_card', 'document_folder/static/src/models/attachment.js', {

    _created() {
        this._super(...arguments);
        // defined onClickUpload
        this.onClickOpenFolders = this.onClickOpenFolders.bind(this);
    },

    async onClickOpenFolders(ev) {
//        ev.stopPropagation();
        var self = this;
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t("Open Folder"),
            res_model: 'select.nextcloud.folder.wizard',
            view_mode: 'file_explore_view',
            views: [[false, 'file_explore_view']],
            target: 'new',
            context: {
                attachment_id: this.attachment.id,
                fileexplore_mode: 'open_folder',
                origin_resmodel: this.attachment.originThread.model,
                origin_resid: this.attachment.originThread.id,
            },
            res_id: false,
            domain: [],
        };
        return this.env.bus.trigger('do-action', {
            action,
            options: {
                on_close: () => {
                    this.attachment.originThread.refresh();
                },
            },
        });
    },

    onClickImage() {
        if (!this.attachment || !this.attachment.isViewable) {
            return;
        }
        if (!this.attachment.isDocumentFolder){
            this.messaging.dialogManager.update({
                dialogs: insert({
                    attachmentViewer: insertAndReplace({
                        attachment: replace(this.attachment),
                        attachmentList: replace(this.attachmentList),
                    }),
                }),
            });
        } else {
            this.onClickOpenFolders()
        }
    }
});