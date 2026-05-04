/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class NextcloudBrowseDialog extends Component {
    static template = "nextcloud.BrowseDialog";
    static components = { Dialog };
    static props = {
        resModel: String,
        resId: { type: Number, optional: true },
        onPicked: { type: Function, optional: true },
        close: Function,
    };
    static defaultProps = { resId: 0 };

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            rows: [],
            byParent: new Map(),
            currentFolderId: null,
            breadcrumbs: [],
            picking: false,
        });
        onWillStart(async () => {
            await this.loadTree();
        });
    }

    async loadTree() {
        this.state.loading = true;
        try {
            const data = await this.rpc("/nextcloud/folder/tree", {});
            this.state.rows = data.rows || [];
            const byParent = new Map();
            for (const row of this.state.rows) {
                const pid = row.parent_id ? row.parent_id[0] : null;
                if (!byParent.has(pid)) byParent.set(pid, []);
                byParent.get(pid).push(row);
            }
            this.state.byParent = byParent;
            // Pick a sensible starting folder.
            const root = this.state.rows.find(
                (r) => r.folder && (!r.parent_id || r.name === "/")
            );
            if (data.default_folder_id) {
                this.openFolder(data.default_folder_id);
            } else if (root) {
                this.openFolder(root.id);
            }
        } catch (err) {
            this.notification.add(_t("Could not load Nextcloud tree."), {
                type: "danger",
            });
        }
        this.state.loading = false;
    }

    openFolder(folderId) {
        const row = this.state.rows.find((r) => r.id === folderId);
        if (!row) return;
        this.state.currentFolderId = folderId;
        // Rebuild breadcrumbs by walking up parent chain.
        const crumbs = [];
        let cursor = row;
        const seen = new Set();
        while (cursor && !seen.has(cursor.id)) {
            crumbs.unshift({ id: cursor.id, label: cursor.folder_name || cursor.name });
            seen.add(cursor.id);
            const pid = cursor.parent_id ? cursor.parent_id[0] : null;
            cursor = pid ? this.state.rows.find((r) => r.id === pid) : null;
        }
        this.state.breadcrumbs = crumbs;
    }

    children() {
        return (this.state.byParent.get(this.state.currentFolderId) || []).slice().sort(
            (a, b) => Number(b.folder) - Number(a.folder) ||
                a.folder_name?.localeCompare(b.folder_name)
        );
    }

    async onPickFile(row) {
        if (this.state.picking) return;
        this.state.picking = true;
        try {
            const result = await this.rpc("/nextcloud/attachment/from_nc", {
                nc_path: row.name,
                res_model: this.props.resModel,
                res_id: this.props.resId,
            });
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
            } else {
                this.notification.add(
                    _t("Attached %s from Nextcloud.", result.name),
                    { type: "success" }
                );
                if (this.props.onPicked) {
                    await this.props.onPicked(result);
                }
                this.props.close();
            }
        } finally {
            this.state.picking = false;
        }
    }

    async onSync() {
        this.state.loading = true;
        try {
            await this.rpc("/nextcloud/folder/sync", {});
            await this.loadTree();
            this.notification.add(_t("Nextcloud tree synchronised."), { type: "success" });
        } catch (err) {
            this.notification.add(_t("Sync failed."), { type: "danger" });
            this.state.loading = false;
        }
    }
}
