/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useModel } from "@web/views/helpers/model";
import { Layout } from "@web/views/layout";
import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { FileExploreModel } from "./file_explore_model";
const { Component, hooks, useState } = owl;
const {useRef} = hooks;
import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/core/dialog/dialog";
import { useDragVisibleDropZone } from '@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone';

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
            this.state = useState({
                /**
                 * Determine whether the user is dragging files over the dropzone.
                 * Useful to provide visual feedback in that case.
                 */
                isDraggingInside: false,
            });
            /**
             * Counts how many drag enter/leave happened on self and children. This
             * ensures the drop effect stays active when dragging over a child.
             */
            this._dragCount = 0;
        }

    setup() {
        this.actionService = useService("action");
        this.isDropZoneVisible = useDragVisibleDropZone();
        this._fileUploaderRef = useRef('fileUploader');
        this.isDraggingInside = false;
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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns whether the given node is self or a children of self.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        return Boolean(this.el && this.el.contains(node));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Making sure that dragging content is external files.
     * Ignoring other content dragging like text.
     *
     * @private
     * @param {DataTransfer} dataTransfer
     * @returns {boolean}
     */
    _isDragSourceExternalFile(dataTransfer) {
        const dragDataType = dataTransfer.types;
        if (dragDataType.constructor === window.DOMStringList) {
            return dragDataType.contains('Files');
        }
        if (dragDataType.constructor === Array) {
            return dragDataType.includes('Files');
        }
        return false;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Shows a visual drop effect when dragging inside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragenter(ev) {
        ev.preventDefault();
        if (this._dragCount === 0) {
            this.state.isDraggingInside = true;
        }
        this._dragCount++;
    }

    /**
     * Hides the visual drop effect when dragging outside the dropzone.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragleave(ev) {
        this._dragCount--;
        if (this._dragCount === 0) {
            this.state.isDraggingInside = false;
        }
    }

    /**
     * Prevents default (from the template) in order to receive the drop event.
     * The drop effect cursor works only when set on dragover.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDragover(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'copy';
    }

    /**
     * Triggers the `o-dropzone-files-dropped` event when new files are dropped
     * on the dropzone, and then removes the visual drop effect.
     *
     * The parents should handle this event to process the files as they wish,
     * such as uploading them.
     *
     * @private
     * @param {DragEvent} ev
     */
    _onDrop(ev) {
        ev.preventDefault();
        if (this._isDragSourceExternalFile(ev.dataTransfer)) {
            this.trigger('o-dropzone-files-dropped', {
                files: ev.dataTransfer.files,
            });
        }
        this.state.isDraggingInside = false;
    }

    async _onDropZoneFilesNextCloudDropped(ev) {
        ev.stopPropagation();
        await this._FileUploaderNextcloudRef.comp.uploadFiles(ev.detail.files);
        this.isDropZoneNextCloudVisible.value = false;
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