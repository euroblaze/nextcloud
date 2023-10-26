/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NextCloudAttachmentList extends Component {

    /**
     * @returns {mail.attachment_list}
     */
    get attachmentList() {
        return this.messaging && this.messaging.models['mail.attachment_list'].get(this.props.attachmentListLocalId);
    }

}

Object.assign(NextCloudAttachmentList, {
    props: {
        attachmentListLocalId: String,
    },
    template: 'nextcloud.NextCloudAttachmentList',
});

registerMessagingComponent(NextCloudAttachmentList);
