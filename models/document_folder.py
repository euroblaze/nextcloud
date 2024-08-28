# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
import base64
import io
import zipfile

_logger = logging.getLogger(__name__)


class DocumentFolder(models.Model):
    _name = 'document.folder'
    _description = 'Document Folder'
    _rec_name = 'x_name'

    x_name = fields.Char(string='Folder Name', store=True)
    x_parent_folder_id = fields.Many2one(comodel_name='document.folder', string='Parent Folder', ondelete="cascade")
    x_child_folder_ids = fields.One2many(comodel_name='document.folder', inverse_name='x_parent_folder_id',
                                         string="Child Folders")
    x_child_file_ids = fields.One2many(comodel_name='ir.attachment', inverse_name='x_document_folder_id',
                                       string="Child Files")
    x_count_total_child = fields.Char(string="Total Resources")
    x_res_id = fields.Integer(string="Resource Id")
    x_res_model = fields.Char(string="Resource Model")
    x_linked_attachment = fields.Many2one('ir.attachment', string="Linked Attachment", ondelete="cascade")
    x_sequence_folder = fields.Integer(string="Sequence Folder", store=True)
    x_original_folder_id = fields.Integer(string="Original Folder Id", store=True)
    x_is_folder = fields.Boolean(string="Folder", default=True, store=True)
    x_document_folder_path = fields.Char(string="Path", store=True)
    x_downloaded_folder_id = fields.Many2one('ir.attachment', string="Download Zip")

    def unlink(self):
        downloaded_folder_id = False
        if self.x_downloaded_folder_id:
            downloaded_folder_id = self.x_downloaded_folder_id
        if downloaded_folder_id:
            downloaded_folder_id.unlink()
        ret = super(DocumentFolder, self).unlink()
        return ret

    def generate_folder_hierarchy(self, parent_folder_id, files_list, res_id, res_model):
        if not (parent_folder_id and files_list):
            return False

        try:
            parent_folder_id['x_sequence_folder'] = 0
            parent_folder_id['x_original_folder_id'] = parent_folder_id.id
            parent_folder_id['x_res_id'] = res_id
            parent_folder_id['x_res_model'] = res_model
            for ufile_k, ufile_v in files_list.items():
                f_path = ufile_v.filename
                path_items = f_path.split('/')
                file_name = path_items.pop()  # Extract the file name
                parent_folder = parent_folder_id

                for sequence, item in enumerate(path_items[1:]):
                    # Check if the folder already exists
                    exist_folder = self.env['document.folder'].search([
                        ('x_name', '=', item),
                        ('x_sequence_folder', '=', sequence + 1),
                        ('x_parent_folder_id', '=', parent_folder.id)
                    ], limit=1)

                    if not exist_folder:
                        # Create a new folder if it doesn't exist
                        document_subfolder = self.env['document.folder'].create({
                            'x_name': item,
                            'x_sequence_folder': sequence + 1,
                            'x_parent_folder_id': parent_folder.id,
                            'x_original_folder_id': parent_folder_id.id,
                            'x_document_folder_path': parent_folder.x_document_folder_path + f'/{item}',
                            'x_res_id': res_id,
                            'x_res_model': res_model
                        })
                    else:
                        document_subfolder = exist_folder

                    # Update the parent folder reference for the next iteration
                    parent_folder = document_subfolder

                # Create the file in the final folder
                self.create_file(parent_folder, ufile_v, file_name, parent_folder_id.id, res_id, res_model)
        except Exception as e:
            _logger.error(f"Error generating folder hierarchy: {e}")
            return False

    def generate_folder_hierarchy_exist(self, parent_folder_id, files_list, original_folder_id):
        if not (parent_folder_id and files_list):
            return False

        try:
            for ufile_k, ufile_v in files_list.items():
                f_path = ufile_v.filename
                path_items = f_path.split('/')
                file_name = path_items.pop()  # Extract the file name
                parent_folder = parent_folder_id

                for sequence, item in enumerate(path_items[0:]):
                    # Check if the folder already exists
                    exist_folder = self.env['document.folder'].search([
                        ('x_name', '=', item),
                        ('x_sequence_folder', '=', sequence + 1),
                        ('x_parent_folder_id', '=', parent_folder.id)
                    ], limit=1)

                    if not exist_folder:
                        # Create a new folder if it doesn't exist
                        document_subfolder = self.env['document.folder'].create({
                            'x_name': item,
                            'x_sequence_folder': sequence + 1,
                            'x_parent_folder_id': parent_folder.id,
                            'x_original_folder_id': original_folder_id.id,
                            'x_document_folder_path': parent_folder.x_document_folder_path + f'/{item}',
                            'x_res_id': parent_folder.x_res_id,
                            'x_res_model': parent_folder_id.x_res_model
                        })
                    else:
                        document_subfolder = exist_folder

                    # Update the parent folder reference for the next iteration
                    parent_folder = document_subfolder

                # Create the file in the final folder
                self.create_file(parent_folder, ufile_v, file_name, original_folder_id.id, False, False)
        except Exception as e:
            _logger.error(f"Error generating folder hierarchy: {e}")
            return False

    def create_file(self, parent_folder, ufile, file_name, original_folder_id, res_id, res_model):
        try:
            # Check if the file is a BytesIO object
            if isinstance(ufile.stream, io.BytesIO):
                file_content = ufile.stream.read()  # Read the file content from the stream
            else:
                file_content = ufile.read()  # Read the file content

            # Convert the file content to base64 for storage
            file_base64 = base64.b64encode(file_content)

            vals = {
                'name': file_name,
                'datas': file_base64,  # Store the base64-encoded content
                'x_document_folder_id': parent_folder.id,
                'x_original_folder_id': original_folder_id,
                'x_document_folder_path': ufile.filename,
            }
            return self.env['ir.attachment'].create(vals)
        except Exception as e:
            _logger.error(f"Error creating file: {file_name}, Error: {e}")
            return False

    @api.model
    def get_folder_hierarchy(self, domain, **kwargs):
        values = {}
        res_model = kwargs.get('res_model', False)
        res_id = kwargs.get('res_id', False)
        attachment_folder_id = kwargs.get('doc_folder_id', False)
        if not attachment_folder_id:
            return {}
        attachment_folder_id = self.env['ir.attachment'].browse(attachment_folder_id)
        # company = self.env.user.company_id.sudo()
        default_folder = attachment_folder_id.x_link_document_folder_id
        domain += [('x_original_folder_id', '=', default_folder.id)]
        data_folder = self.sudo().search_read(domain, fields=[], order="x_name")
        data_files = self.env['ir.attachment'].sudo().search_read([('x_original_folder_id', '=', default_folder.id)])
        data = data_folder + data_files

        values.update({
            'data': data,
            'folder_data': data_folder,
            'default_folder': default_folder.read()[0]
        })

        return values

    def document_folder_zip(self, attachment_id):
        folder_attachment = self.env['ir.attachment'].browse(int(attachment_id))
        if folder_attachment:
            document_folder = folder_attachment.x_link_document_folder_id
            output_zip_name = f'{document_folder.x_document_folder_path}.zip'
            output = io.BytesIO()
            folder_files = self.env['ir.attachment'].sudo().search(
                [('x_original_folder_id', '=', document_folder.id)])
            # Create a ZipFile in memory
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in folder_files:
                    # Get the file content and its name
                    file_content = base64.b64decode(file.datas)
                    path_parts = file.x_document_folder_path.split('/')
                    file_name = '/'.join(path_parts[1:])
                    # Write the file into the zip file
                    zipf.writestr(file_name, file_content)

            folder_vals = {
                'name': folder_attachment.name,
                'datas': base64.b64encode(output.getvalue()),
            }

            download_folder_attachment = self.env['ir.attachment'].sudo().create(folder_vals)
            document_folder['x_downloaded_folder_id'] = download_folder_attachment.id

        return folder_attachment
