/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NextCloudAttachmentList extends Component {

    /**
     * @returns {mail.attachment_list}
     */
    get attachmentList() {
        console.log(this);
//        console.log(this.messaging);
//        console.log(this.props);
//        console.log(this.messaging.models['mail.attachment_list'].get(this.props.attachmentListLocalId));
        return this.messaging && this.messaging.models['mail.attachment_list'].get(this.props.attachmentListLocalId);
    }

}

Object.assign(NextCloudAttachmentList, {
    props: {
        attachmentListLocalId: String,
    },
    template: 'bf_nextcloud.NextCloudAttachmentList',
});

registerMessagingComponent(NextCloudAttachmentList);
