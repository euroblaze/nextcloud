/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from "@web/core/l10n/translation";

export class FileExploreDialog extends Dialog {
    setup() {
        super.setup();
        this.title = this.props.title;
    }
    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.close();
    }

    _confirm() {
        if (this.props.confirm) {
            this.props.confirm();
        }
        this.close();
    }

    async willStart() {
        const { errorData } = this.props;
        this.url = await this.orm.call("iap.account", "get_credits_url", [], {
            base_url: errorData.base_url,
            service_name: errorData.service_name,
            credit: errorData.credit,
            trial: errorData.trial,
        });
        this.style = errorData.body ? "padding:0;" : "";
    }
}
FileExploreDialog.props = {
    title: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
    },
    confirm: { type: Function, optional: true },
    cancel: { type: Function, optional: true },
    close: Function,
};
FileExploreDialog.defaultProps = {
    title: _lt("FileExplore"),
};

FileExploreDialog.bodyTemplate = "nextcloud.FileExplore";
FileExploreDialog.size = "modal-md";