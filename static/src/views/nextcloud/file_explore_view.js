/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useModel } from "@web/views/helpers/model";
import { Layout } from "@web/views/layout";
import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { FileExploreModel } from "./file_explore_model";
const { Component } = owl;
import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/core/dialog/dialog";
/**
 * This is a patch of the new Dialog class to hide footer.
 */
patch(Dialog.prototype, "FileExplore Adapted Dialog", {
    setup() {
        this.size += ' file_explore_view';
        this._super();
        if ('actionProps' in this.props && this.props.actionProps.type == "file_explore_view") {
            this.renderFooter = false;
        }
    },
});

// Empty component for now
class NextcloudFileExplore extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.renderFooter = false;
    }

    _renderView() {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var purchase_dashboard = QWeb.render('purchase.PurchaseDashboard', {
                values: values,
            });
            self.$el.prepend(purchase_dashboard);
        });
    }

    setup() {
        this.actionService = useService("action");

        let modelParams = {
            context: this.props.context,
            domain: this.props.domain
        };
        if (this.props.state) {
            modelParams.data = this.props.state.data;
            modelParams.metaData = this.props.state.metaData;
        } else {
            modelParams.metaData = {
                fields: this.props.fields,
                resModel: this.props.resModel,
            };
        }

        this.model = useModel(this.constructor.Model, modelParams);
    }

}

NextcloudFileExplore.type = "file_explore_view";
NextcloudFileExplore.display_name = "NextcloudFileExplore";
NextcloudFileExplore.icon = "fa-heart";
NextcloudFileExplore.multiRecord = true;
NextcloudFileExplore.searchMenuTypes = ["filter", "favorite"];
NextcloudFileExplore.Model = FileExploreModel;

// Registering the Layout Component is optional
// But in this example we use it in our template
NextcloudFileExplore.components = { Layout , ActionDialog};
NextcloudFileExplore.template = 'nextcloud.FileExplore';

registry.category("views").add("file_explore_view", NextcloudFileExplore);