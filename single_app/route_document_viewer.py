# Add to route_document_viewer.py

from config import *
from functions_authentication import *
from functions_blob_storage import download_from_blob_storage, get_blob_properties
from functions_document_preview import get_office_preview_url
import mimetypes
import os
import urllib.parse

def register_route_document_viewer(app):
    @app.route('/document-viewer')
    @login_required
    def document_viewer():
        """
        Universal document viewer that handles multiple file formats.
        
        Query parameters:
        - file: URL of the file to view (required)
        - type: File type hint (optional, auto-detected if not provided)
        - name: Display name of the file (optional)
        - page: Initial page number for PDFs (optional, default 1)
        - zoom: Initial zoom level for PDFs (optional, default auto)
        """
        file_url = request.args.get('file')
        file_type = request.args.get('type', 'auto')
        file_name = request.args.get('name', 'Document')
        page = request.args.get('page', 1)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
            
        zoom = request.args.get('zoom', 'auto')
        
        # Validate that the user is authenticated
        user_id = get_current_user_id()
        if not user_id:
            return "Unauthorized", 401
        
        if not file_url:
            return "Missing file URL parameter", 400
        
        # If file_type is auto, try to determine it from file_name
        if file_type == 'auto' and file_name:
            extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
            if extension in ['pdf']:
                file_type = 'pdf'
            elif extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                file_type = 'image'
            elif extension in ['docx', 'doc']:
                file_type = 'docx'
            elif extension in ['xlsx', 'xls']:
                file_type = 'xlsx'
            elif extension in ['pptx', 'ppt']:
                file_type = 'pptx'
            elif extension in ['txt', 'log', 'md']:
                file_type = 'text'
            elif extension in ['csv']:
                file_type = 'csv'
        
        # For Office documents, redirect to MS Graph viewer
        if file_type in ['docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt']:
            return redirect(url_for('ms_graph_document_viewer', 
                                   file=file_url,
                                   type=file_type,
                                   name=file_name,
                                   page=page))
        
        # For other viewable documents, use our standard viewer
        return render_template('document_viewer.html', 
                              file_url=file_url,
                              file_type=file_type,
                              file_name=file_name,
                              page=page,
                              zoom=zoom)
    
    @app.route('/ms-graph-document-viewer')
    @login_required
    def ms_graph_document_viewer():
        """
        Microsoft Graph-powered document viewer for Office documents.
        Gets a Microsoft Graph preview URL for the document.
        """
        file_url = request.args.get('file')
        file_type = request.args.get('type', 'auto')
        file_name = request.args.get('name', 'Document')
        page = request.args.get('page', 1)
        
        # Validate that the user is authenticated
        user_id = get_current_user_id()
        if not user_id:
            return "Unauthorized", 401
        
        if not file_url:
            return "Missing file URL parameter", 400
        
        try:
            # Get a Microsoft Graph preview URL for the document
            preview_url = get_office_preview_url(file_url, file_name)
            
            if preview_url:
                # Render the MS Graph viewer template
                return render_template('ms_graph_document_viewer.html',
                                      file_name=file_name,
                                      file_type=file_type,
                                      preview_url=preview_url,
                                      page=page)
            else:
                # Fallback if we couldn't get a preview URL
                return render_template('document_viewer_error.html',
                                      file_name=file_name,
                                      error="Could not generate a preview for this document.",
                                      download_url=file_url)
        except Exception as e:
            print(f"Error in MS Graph document viewer: {str(e)}")
            # Fallback to download option
            return render_template('document_viewer_error.html',
                                  file_name=file_name,
                                  error=f"Error generating document preview: {str(e)}",
                                  download_url=file_url)
    
    @app.route('/document-proxy', endpoint='document_proxy_viewer')
    @login_required
    def document_proxy():
        """
        Proxy for document requests to blob storage with better content type detection.
        This allows the client to access documents without needing direct access to blob storage.
        """
        blob_url = request.args.get('url')
        if not blob_url:
            return "Missing URL parameter", 400
        
        user_id = get_current_user_id()
        if not user_id:
            return "Unauthorized", 401
        
        try:
            # Download the document from blob storage
            file_content = download_from_blob_storage(blob_url)
            
            # Try to determine content type
            content_type = None
            
            # First try getting from blob properties
            try:
                properties = get_blob_properties(blob_url)
                content_type = properties.content_settings.content_type
                print(f"Content type from blob properties: {content_type}")
            except Exception as e:
                print(f"Error getting blob properties: {e}")
                
            # If no content type or it's generic, try to determine from URL
            if not content_type or content_type == 'application/octet-stream':
                file_ext = os.path.splitext(blob_url)[1].lower()
                
                # Map common extensions to MIME types
                content_type_map = {
                    '.pdf': 'application/pdf',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    '.txt': 'text/plain',
                    '.csv': 'text/csv',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp',
                    '.json': 'application/json',
                    '.xml': 'application/xml',
                    '.html': 'text/html',
                    '.htm': 'text/html',
                    '.css': 'text/css',
                    '.js': 'application/javascript',
                    '.md': 'text/markdown'
                }
                
                content_type = content_type_map.get(file_ext)
                if not content_type:
                    # Use Python's mimetypes as fallback
                    content_type = mimetypes.guess_type(blob_url)[0] or 'application/octet-stream'
                
                print(f"Content type determined from extension: {content_type}")
            
            # Return the file as a response
            return Response(
                file_content,
                mimetype=content_type,
                headers={
                    'Content-Disposition': f'inline; filename="{os.path.basename(blob_url)}"',
                    'Content-Type': content_type,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        except Exception as e:
            print(f"Error serving document: {str(e)}")
            return jsonify({'error': f'Error serving document: {str(e)}'}), 500

    # API endpoint to get citation
    @app.route("/api/get_document_preview", methods=["POST"])
    @login_required
    @user_required
    def get_document_preview():
        """
        Get a document preview URL for a given document.
        This is useful for getting previews for documents that can't be viewed directly in the browser.
        """
        try:
            data = request.get_json()
            document_url = data.get("document_url")
            file_name = data.get("file_name", "document.docx")
            
            if not document_url:
                return jsonify({"error": "Missing document_url"}), 400
            
            # Get extension to determine document type
            extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
            is_office_document = extension in ['docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt']
            
            if is_office_document:
                # Get Microsoft Graph preview URL
                preview_url = get_office_preview_url(document_url, file_name)
                
                if preview_url:
                    return jsonify({
                        "preview_url": preview_url,
                        "preview_type": "ms_graph"
                    }), 200
                else:
                    return jsonify({
                        "error": "Could not generate preview",
                        "download_url": document_url
                    }), 500
            else:
                # For non-Office documents, just return the document_url
                return jsonify({
                    "preview_url": f"/document-proxy?url={document_url}",
                    "preview_type": "direct"
                }), 200
                
        except Exception as e:
            print(f"Error in get_document_preview: {str(e)}")
            return jsonify({"error": f"Server error generating preview: {str(e)}"}), 500