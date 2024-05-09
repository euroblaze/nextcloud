/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

import { DropZone } from '@mail/components/drop_zone/drop_zone'

patch(DropZone.prototype, "nextcloud.dropzone", {

//    _uploadDirectory(directory) {
//        var formData = new FormData();
//
//        // Kiểm tra xem `directory` có phải là một đối tượng hoặc giá trị bất đồng bộ không
//        if (typeof directory === 'object' && directory !== null) {
//            // Nếu `directory` là một đối tượng, chờ cho đến khi nó được hoàn thành
//            Promise.resolve(directory).then(function(resolvedDirectory) {
//                formData.append('directory', resolvedDirectory);
//
//                // Sau khi đã gắn giá trị cho formData, thực hiện fetch
//                performFetch(formData);
//            });
//        } else {
//            // Nếu `directory` không phải là một đối tượng hoặc giá trị bất đồng bộ,
//            // chỉ đơn giản gắn giá trị và thực hiện fetch
//            formData.append('directory', directory);
//            performFetch(formData);
//        }
//    }

    _onDrop(ev) {
        ev.preventDefault();
        var items = ev.dataTransfer.items;

        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            var entry = item.webkitGetAsEntry();
            if (entry.isDirectory) {
                console.log("Đây là folder");
                this.trigger('o-dropzone-files-dropped', {
                    files: [item],
                });
            } else {
                if (this._isDragSourceExternalFile(ev.dataTransfer)) {
                    this.trigger('o-dropzone-files-dropped', {
                        files: [item],
                    });
                }
            }
        }
        this.state.isDraggingInside = false;
    }
});
