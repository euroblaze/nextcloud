/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, hooks } = owl;

class NextcloudSystray extends Component {
    setup() {
        this.hm = useService("home_menu");
        this.rootRef = hooks.useRef("root");
        this.orm = useService("orm");
    }

    _onClickSyncNC() {
        return this.syncNextcloudData()
    }

    async syncNextcloudData() {
        await this.orm.call('nextcloud.folder', 'sync_nextcloud_folder', []);
    }
}
NextcloudSystray.template = "nextcloud.SystrayItem";

export const systrayItem = {
    Component: NextcloudSystray,
    isDisplayed: (env) => env.services.user.isSystem,
};

registry.category("systray").add("NextcloudSystray", systrayItem, { sequence: 1 });
