/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.nextcloudBrowse = useService("nextcloud_browse");
    },

    onClickBrowseNextcloud() {
        if (!this.state.thread || !this.props.threadId) {
            return;
        }
        this.nextcloudBrowse.open({
            resModel: this.props.threadModel,
            resId: this.props.threadId,
            onPicked: async () => {
                // Reload chatter attachments after picking.
                if (this.state.thread.fetchNewMessages) {
                    await this.state.thread.fetchNewMessages();
                }
                if (this.state.thread.fetchAttachments) {
                    await this.state.thread.fetchAttachments();
                }
            },
        });
    },
});
