/** @odoo-module **/

const {hooks} = owl;
const {useRef} = hooks;
import { Race } from "@web/core/utils/concurrency";
import { Model } from "@web/views/helpers/model";
import framework from 'web.framework';

import core from 'web.core';

export class FileExploreModel extends Model {

    setup(params) {
        this._dialogRef = useRef('dialog');
        this.race = new Race();
        const _loadData = this._loadData.bind(this);
        this._loadData = (...args) => {
            return this.race.add(_loadData(...args));
        };
        this.attachment_id = params.context.attachment_id;
        this.fileexplore_mode = params.context.fileexplore_mode;
        this.origin_resmodel = params.context.origin_resmodel;
        this.origin_resid = params.context.origin_resid;

        let sortedColumn = params.metaData.sortedColumn || null;
        if (!sortedColumn && params.metaData.defaultOrder) {
            const defaultOrder = params.metaData.defaultOrder.split(" ");
            sortedColumn = {
                groupId: [[], []],
                measure: defaultOrder[0],
                order: defaultOrder[1] ? defaultOrder[1] : "asc",
            };
        }

        this.searchParams = {
            context: params.context || {},
            domain: params.domain || [],
            model: params.metaData.resModel || []
        };

        this.data = []
        const metaData = Object.assign({}, params.metaData, {});
        this.metaData = this._buildMetaData(metaData);
        this.reload = false; // used to discriminate between the first load and subsequent reloads
        
        this.current_folder = false;
        this.current_folder_data = [];
        this.folder_selected = false;
        this.files_selected = [];

        this.feature = Object.assign({}, {
            allowUpload: false,
            allowDownload: false,
        }, {});

        // Trigger method
        this.onItemClicked = this.onItemClicked.bind(this);
        this.onUploadClicked = this.onUploadClicked.bind(this);
        this.onDownloadClicked = this.onDownloadClicked.bind(this);
    }

    getDataById(data, id) {
        return data.find(item => item.id === id);
    }

    getDataByIds(data, ids) {
        return data.filter(item => ids.includes(item.id));
    }

    async load(params) {
        const data = await this.orm.call('nextcloud.folder', 'get_master_data', [params.domain], {
            res_model: this.origin_resmodel,
            res_id: this.origin_resid
        });
        this.data = data.data;
        this.breadcrumbs = this.getBreadcums(this.data, data.default_folder.id);
        this.current_folder = data.default_folder;
        this.current_folder_data = this.getDataByIds(this.data, this.current_folder.child_ids);
        this.folder_selected = this.current_folder.id;
        this.feature.allowUpload = true ? this.fileexplore_mode == 'upload' && this.folder_selected : false;
        this.notify();
    }

    async _loadData(config, prune = true) {
        config.data = {}; // data will be completely recomputed
        const { data, metaData } = config;
        this.data = config.data;
        this.metaData = config.metaData;
    }

    _buildMetaData(params) {
        const metaData = Object.assign({}, this.metaData, params);
        // shallow copy sortedColumn because we never modify groupId in place
        if (this.searchParams.comparison) {
            const domains = this.searchParams.comparison.domains.slice().reverse();
            metaData.domains = domains.map((d) => d.arrayRepr);
            metaData.origins = domains.map((d) => d.description);
        } else {
            metaData.domains = [this.searchParams.domain];
            metaData.origins = [""];
        }
        return metaData;
    }
    
    onItemClicked(ev) {
        let $currentTarget = $(ev.target).parents('.fe_fileexplorer_item_wrap');
        let selected_info = $currentTarget.getAttributes().id;
        if (selected_info === undefined) {
            return;
        }
        let identify_key = selected_info.split('_');
        let selected = $currentTarget.hasClass('fe_fileexplorer_item_selected');
        if (selected === true && identify_key[0] == 'folder') {
            this.openFolder(parseInt(identify_key[1]));
        }
        if (identify_key[0] == 'folder') {
            if (selected === false) {
                let $previousSelected = $currentTarget.parents('.fe_fileexplorer_items_wrap').find('.fe_fileexplorer_item_selected');
                if ($previousSelected.length > 0) {
                    $previousSelected.removeClass('fe_fileexplorer_item_selected');
                    this.folder_selected = false;
                }
                $currentTarget.addClass('fe_fileexplorer_item_selected');
                this.folder_selected = identify_key[1];
            }
        } else if (identify_key[0] == 'file') {
            let select_file = this.getDataById(this.data, parseInt(identify_key[1]));
            if (selected === false) {
                $currentTarget.addClass('fe_fileexplorer_item_selected');
                this.files_selected.push(select_file);
            } else {
                $currentTarget.removeClass('fe_fileexplorer_item_selected');
                this.files_selected = this.files_selected.filter(item => item !== select_file);
            }
        }
        this.feature.allowUpload = true ? this.fileexplore_mode == 'upload' && this.folder_selected : false;
        this.feature.allowDownload = true ? this.fileexplore_mode == 'download' && this.files_selected.length > 0 : false;
        this.notify();
    }

    getBreadcums(data, folderID) {
        let breadcrumbs = [];
        function findParent(id) {
            const item = data.find((element) => element.id === id);
            if (item) {
              breadcrumbs.unshift(item);
              if (item.parent_id !== null) {
                findParent(item.parent_id[0]);
              }
            }
        }
        findParent(folderID);
        return breadcrumbs;
    }

    openFolder(folderID) {
        let currentFolder = this.getDataById(this.data, folderID);
        this.current_folder = currentFolder;
        this.current_folder_data = this.getDataByIds(this.data, this.current_folder.child_ids);
        this.breadcrumbs = this.getBreadcums(this.data, folderID);
        this.files_selected = [];
        this.feature.allowDownload = false;
        this.notify();
    }

    _createFormDataNextcloud() {
        const formData = new window.FormData();
        formData.append('csrf_token', core.csrf_token);
        formData.append('attachment_id', this.attachment_id);
        formData.append('folder_id', this.folder_selected);
        return formData;
    }

    async onDownloadClicked(ev) {
        var self = this;
        await this.orm.call('nextcloud.folder', 'download_file_from_nextcloud',
            [this.files_selected, this.origin_resmodel, this.origin_resid], {});
        return self.env.services.action.doAction({
            'type': 'ir.actions.act_window_close'
        });
    }

    async onUploadClicked(ev) {
        var self = this;
        framework.blockUI();
        try {
            const response = await this.env.browser.fetch('/mail/attachment/uploadnextcloud', {
                method: 'POST',
                body: this._createFormDataNextcloud()
            });
            const response_data = await response.json();
            if (response_data.error) {
                self.env.services['notification'].notify({
                    type: 'danger',
                    message: attachmentData.error,
                });
                return;
            }
            framework.unblockUI();
            return self.env.services.action.doAction({
                type: 'ir.actions.act_window_close',
                infos: response_data,
            });
        } catch (e) {
            framework.unblockUI();
            if (e.name !== 'AbortError') {
                throw e;
            }
        }
    }

    onClickedFolderSelection(node) {
        var posx = node.lastChild.offsetLeft - elems.pathsegmentsscrollwrap.scrollLeft + elems.pathsegmentsscrollwrap.offsetLeft - 18;
        var basepath = currfolder.GetPath();

        // Adjust basepath.
        basepath = basepath.slice(0, GetCurrentPathSegmentPos() + 1);

        // Apply styles.
        node.classList.add('fe_fileexplorer_path_segment_wrap_focus');
        node.classList.add('fe_fileexplorer_path_segment_wrap_down');

        // Cancel any existing popup menu.
        if (popupmenu)  popupmenu.Cancel();

        // Setup popup menu options.
        var options = {
            items: [],

            resizewatchers: [
                { elem: document.body, attr: 'offsetWidth', val: -1 }
            ],

            onposition: function(popupelem) {
                var posx2 = (posx + popupelem.offsetWidth < document.body.offsetWidth ? posx : document.body.offsetWidth - popupelem.offsetWidth - 1);

                popupelem.style.left = posx2 + 'px';
                popupelem.style.top = (elems.toolbar.offsetTop + elems.toolbar.offsetHeight) + 'px';
            },

            onselected: function(id, item, lastelem, etype) {
                popupmenu = null;
                $this.Focus(true);
                this.Destroy();

                // Append the selected path segment.
                var pathitem = [item.info.id, item.name];
                if ('attrs' in item.info)  pathitem.push(item.info.attrs);

                basepath.push(pathitem);

                $this.SetPath(basepath);
            },

            oncancel: function(lastelem, etype) {
                popupmenu = null;

                node.classList.remove('fe_fileexplorer_path_segment_wrap_focus');
                node.classList.remove('fe_fileexplorer_path_segment_wrap_down');

                if (lastelem)  lastelem.focus();

                if (etype === 'mouse' && lastelem.classList.contains('fe_fileexplorer_path_opts'))  node.classList.add('fe_fileexplorer_block_popup');

                this.Destroy();
            },

            onleft: function(lastelem) {
                var pos = GetCurrentPathSegmentPos();

                if (pos)
                {
                    popupmenu = null;

                    node.classList.remove('fe_fileexplorer_path_segment_wrap_focus');
                    node.classList.remove('fe_fileexplorer_path_segment_wrap_down');

                    // Don't let oncancel be called because it steals focus to the wrong element.
                    this.PreventCancel();

                    elems.pathsegmentswrap.children[pos - 1].focus();

                    this.Destroy();

                    StartPathSegmentFolderSelection(elems.pathsegmentswrap.children[pos - 1]);
                }
            },

            onright: function(lastelem) {
                var pos = GetCurrentPathSegmentPos();

                if (pos < elems.pathsegmentswrap.children.length - 1)
                {
                    popupmenu = null;

                    node.classList.remove('fe_fileexplorer_path_segment_wrap_focus');
                    node.classList.remove('fe_fileexplorer_path_segment_wrap_down');

                    // Don't let oncancel be called because it steals focus to the wrong element.
                    this.PreventCancel();

                    elems.pathsegmentswrap.children[pos + 1].focus();

                    this.Destroy();

                    StartPathSegmentFolderSelection(elems.pathsegmentswrap.children[pos + 1]);
                }
            }
        }
    }
}