/** @odoo-module **/

import { registry } from "@web/core/registry";
import { NextcloudBrowseDialog } from "@nextcloud/components/browse_dialog/browse_dialog";

/**
 * Service exposing `open({ resModel, resId, onPicked })` to launch
 * the Nextcloud browse dialog from anywhere (chatter button,
 * client action, custom UI).
 */
export const nextcloudBrowseService = {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        return {
            open({ resModel, resId, onPicked }) {
                if (!resModel) {
                    console.warn("nextcloud_browse: resModel is required");
                    return;
                }
                dialog.add(NextcloudBrowseDialog, {
                    resModel,
                    resId: resId || 0,
                    onPicked,
                });
            },
        };
    },
};

registry.category("services").add("nextcloud_browse", nextcloudBrowseService);
