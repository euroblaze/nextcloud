/** @odoo-module **/

import {
    registerInstancePatchModel
} from'@mail/model/model_core';
import { FileExploreDialog } from "../views/nextcloud/file_explore_dialog";
import { useService } from "@web/core/utils/hooks";

registerInstancePatchModel('mail.chatter', 'nextcloud/static/src/js/chatter.js', {

    setup() {
        this._super();
        this.dialogService = useService("dialog");
    },
    /**
     * @override
     */
    _created() {
        this._super(...arguments);
        // defined onClickUpload
        this.onClickDownloadNextcloud = this.onClickDownloadNextcloud.bind(this);
        this.onClickOpenFileExploreDialog = this.onClickOpenFileExploreDialog.bind(this);
    },

    /**
     * Handles click on download icon.
     *
     * @param {MouseEvent} ev
     */
    onClickDownloadNextcloud(ev) {
        ev.stopPropagation();
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t("Download file from Nextcloud"),
            res_model: 'select.nextcloud.folder.wizard',
            view_mode: 'file_explore_view',
            views: [[false, 'file_explore_view']],
            target: 'new',
            context: {
                attachment_id: false,
                fileexplore_mode: 'download',
                origin_resmodel: this.threadModel,
                origin_resid: this.threadId,
            },
            res_id: false,
            domain: [],
        };
        return this.env.bus.trigger('do-action', {
            action,
            options: {
                on_close: () => {
                    if (!this.componentChatterTopbar) {
                        return;
                    }
                    this.componentChatterTopbar.trigger('reload', { keepChanges: true });
                },
            },
        });
    },

    onClickOpenFileExploreDialog(ev) {
        ev.stopPropagation();
        new FileExploreDialog(this, {
            attachment_id: false,
                fileexplore_mode: 'download',
                origin_resmodel: this.threadModel,
                origin_resid: this.threadId,
                domain: [],
        }).open();
        // const dialogProps = {
        //     title: this.env._t("Download file from Nextcloud"),
        //     confirm: () => {},
        //     cancel: () => {},
        //     data: {
        //         attachment_id: false,
        //         fileexplore_mode: 'download',
        //         origin_resmodel: this.threadModel,
        //         origin_resid: this.threadId,
        //         domain: [],
        //     }
        // };
        // this.dialogService.add(FileExploreDialog, dialogProps);
    }
})