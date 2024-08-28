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
        this.onUploadFileClicked = this.onUploadFileClicked.bind(this);
        this.onDownloadClicked = this.onDownloadClicked.bind(this);
        this.onUploadFolderClicked = this.onUploadFolderClicked.bind(this);
        this.onDownloadDocumentClicked = this.onDownloadDocumentClicked.bind(this);
    }

    getDataById(data, id) {
        return data.find(item => item.id === id);
    }

    getDataByIds(data, ids) {
        return data.filter(item => ids.includes(item.id));
    }

    async load(params) {
        var data = []
        if (this.fileexplore_mode != 'open_folder'){
            data = await this.orm.call('nextcloud.folder', 'get_master_data', [params.domain], {
                res_model: this.origin_resmodel,
                res_id: this.origin_resid
            });
        } else {
            data = await this.orm.call('document.folder', 'get_folder_hierarchy', [params.domain], {
                res_model: this.origin_resmodel,
                res_id: this.origin_resid,
                doc_folder_id: this.attachment_id
            });
        }
        this.data = data.data;
        this.breadcrumbs = this.getBreadcums(this.data, data.default_folder.id);
        this.current_folder = data.default_folder;
        this.current_folder_data = this.getDataByIds(
            this.data,
            !this.current_folder.child_ids ? this.current_folder.x_child_folder_ids.concat(this.current_folder.x_child_file_ids) : this.current_folder.child_ids
        );
        this.folder_selected = this.current_folder.id;
        this.feature.allowUpload = true ? this.fileexplore_mode == 'upload' || this.fileexplore_mode == 'open_folder' && this.folder_selected : false;
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
        this.feature.allowUpload = true ? (this.fileexplore_mode == 'upload' || this.fileexplore_mode == 'open_folder') && this.folder_selected : false;
        this.feature.allowDownload = true ? (this.fileexplore_mode == 'download' || this.fileexplore_mode == 'open_folder') && (this.files_selected.length > 0 || this.folder_selected) : false;
        this.notify();
    }

    getBreadcums(data, folderID) {
        let breadcrumbs = [];
        function findParent(id) {
            const item = data.find((element) => element.id === id);
            if (item) {
              breadcrumbs.unshift(item);
              if (item.parent_id) {
                findParent(item.parent_id[0]);
              } else {
                if (item.x_document_folder_id) {
                    findParent(item.x_document_folder_id[0]);
                }
                if (item.x_parent_folder_id) {
                    findParent(item.x_parent_folder_id[0]);
                }
              }
            }
        }
        findParent(folderID);
        return breadcrumbs;
    }

    openFolder(folderID) {
        let currentFolder = this.getDataById(this.data, folderID);
        this.current_folder = currentFolder;
        this.current_folder_data = this.getDataByIds(
            this.data,
            !this.current_folder.child_ids ? this.current_folder.x_child_folder_ids.concat(this.current_folder.x_child_file_ids) : this.current_folder.child_ids
        );
        this.breadcrumbs = this.getBreadcums(this.data, folderID);
        this.files_selected = [];
        this.feature.allowDownload = false;
        this.notify();
    }

    _createFormDataNextcloud() {
        const formData = new window.FormData();
        formData.append('csrf_token', core.csrf_token);
        formData.append('attachment_id', this.attachment_id);
        formData.append('folder_id', this.current_folder.id);
        return formData;
    }

    _createFormDataDocumentFolder(files) {
        const formData = new window.FormData();
        formData.append('csrf_token', core.csrf_token);
        formData.append('parent_attachment_folder_id', this.attachment_id);
        formData.append('current_folder_id', this.current_folder.id);

        for (let i = 0; i < files.length; i++) {
            // Use template literals to construct the key
            formData.append('ufiles_'+i, files[i], files[i].webkitRelativePath || files[i].name);
        }
        return formData;
    }

    async onDownloadClicked(ev) {
        var self = this;
        await this.orm.call('nextcloud.folder', 'download_file_from_nextcloud',
            [this.files_selected, this.origin_resmodel, this.origin_resid], {});

        if (this.folder_selected) {
            var download_folder = false
            if (!this.files_selected.length) {
                download_folder = true
            } else {
                if (this.files_selected[0].parent_id[0] == this.folder_selected) {
                    download_folder = false
                } else {
                    download_folder = true
                }
            }
            if (download_folder) {
                await this.orm.call('nextcloud.folder', 'download_folder_from_nextcloud',
                [this.folder_selected, this.origin_resmodel, this.origin_resid], {});
            }
        }
        return self.env.services.action.doAction({
            'type': 'ir.actions.act_window_close'
        });
    }

    fileDownload(files_selected) {
        var downloadUrl = '#'
        files_selected.forEach((file) => {
            if (!file.accessToken && file.origin_resid && file.origin_resmodel === 'mail.channel') {
                downloadUrl = `/mail/channel/${file.origin_resid}/attachment/${file.id}?download=true`;
            } else {
                const accessToken = file.accessToken ? `access_token=${file.accessToken}&` : '';
                downloadUrl = `/web/content/ir.attachment/${file.id}/datas?${accessToken}download=true`;
            }
            const downloadLink = document.createElement('a');
            downloadLink.setAttribute('href', downloadUrl);
            // Adding 'download' attribute into a link prevents open a new tab or change the current location of the window.
            // This avoids interrupting the activity in the page such as rtc call.
            downloadLink.setAttribute('download','');
            downloadLink.click();
        })
    }

    async onDownloadDocumentClicked(ev){
        var self = this;
        if (this.files_selected) {
            this.fileDownload(this.files_selected)
        }
    }

    openBrowserFileUpload(ev) {
        const input = document.createElement('input');
        input.type = 'file';
        input.webkitdirectory = false; // Allow folder selection
        input.style.display = 'none'; // Ensure it's not visible
        document.body.appendChild(input);
        input.addEventListener('change', async (ev) => {
            const files = ev.target.files; // Get the selected file
            if (files) {
                // Send the file to the server
                framework.blockUI();
                const response = await fetch('/document/folder/uploadFileExistFolder', {
                    method: 'POST',
                    body: this._createFormDataDocumentFolder(files),
                });
                const response_data = await response.json();
                framework.unblockUI();
                this.env.services.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _("Your file is successfully uploaded !"),
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                });
            }
        });

        // Trigger the file uploader dialog
        input.click();
    }

    async onUploadFileClicked(ev){
        var self = this;
        framework.blockUI();
        try {
            await this.openBrowserFileUpload(ev)
            framework.unblockUI();
        } catch (e) {
            framework.unblockUI();
            if (e.name !== 'AbortError') {
                throw e;
            }
        }
    }

    openBrowserFolderUpload(ev){
        const input = document.createElement('input');
        input.type = 'file';
        input.webkitdirectory = true; // Allow folder selection
        input.style.display = 'none'; // Ensure it's not visible
        document.body.appendChild(input);
        input.addEventListener('change', async (ev) => {
            const files = ev.target.files; // Get the selected file
            if (files) {
                // Send the file to the server
                framework.blockUI();
                const response = await fetch('/document/folder/uploadFolderExistFolder', {
                    method: 'POST',
                    body: this._createFormDataDocumentFolder(files),
                });
                const response_data = await response.json();
                framework.unblockUI();
                this.env.services.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _("Your Folder is successfully uploaded !"),
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                });
            }
        });

        // Trigger the file uploader dialog
        input.click();
    }

    async onUploadFolderClicked(ev){
        var self = this;
        framework.blockUI();
        try {
            await this.openBrowserFolderUpload(ev)
            framework.unblockUI();
        } catch (e) {
            framework.unblockUI();
            if (e.name !== 'AbortError') {
                throw e;
            }
        }
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
                    message: response_data.error,
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