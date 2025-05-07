# route_document_viewer.py with fixed imports

from config import *
from functions_authentication import *
from functions_blob_storage import download_from_blob_storage, get_blob_properties
from functions_document_preview import get_office_preview_url
from functions_group import find_group_by_id, is_user_in_group  # Added missing import
from functions_group_documents import get_group_document  # Added missing import
import mimetypes
import os
import urllib.parse
import traceback

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
    
    @app.route('/api/get_document_view', methods=['POST'])
    @login_required
    @user_required
    def get_document_view():
        """
        Get view information for a document to display in the document viewer.
        This mimics the behavior of get_citation but works directly with document IDs.
        """
        try:
            # 1. Get and validate request data
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid request data - no JSON body"}), 400
                    
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401
            
            doc_id = data.get("document_id")
            doc_type = data.get("doc_type", "personal")  # personal, group, or default
            group_id = data.get("group_id")  # Required for group documents
            
            if not doc_id:
                return jsonify({"error": "Missing required parameter: document_id"}), 400
            
            print(f"Document view request: ID={doc_id}, Type={doc_type}, User={user_id}, Group={group_id}")
            
            # 2. Process based on document type
            if doc_type == "personal":
                # Get document from personal workspace
                try:
                    doc_item = documents_container.read_item(
                        item=doc_id,
                        partition_key=doc_id
                    )
                    
                    # Check if document belongs to user
                    if doc_item.get('user_id') != user_id:
                        return jsonify({"error": "Document not found or access denied"}), 403
                    
                    # Create response with document info
                    response_data = {
                        "document_source": {
                            "name": doc_item.get('file_name', 'Document'),
                            "page": 1,
                            "workspace_type": "personal",
                            "file_type": get_file_type(doc_item.get('file_name', '')),
                            "is_viewable": is_viewable_file_type(doc_item.get('file_name', ''))
                        },
                        "document_url": doc_item.get('storage_url'),
                        "document_proxy_url": f"/document-proxy?url={urllib.parse.quote(doc_item.get('storage_url', ''))}",
                        "download_url": f"/api/documents/{doc_id}/download"
                    }
                    
                    # Add document viewer URL for viewable documents
                    if response_data["document_source"]["is_viewable"]:
                        file_name = urllib.parse.quote(doc_item.get('file_name', 'Document'))
                        response_data["document_viewer_url"] = f"/document-viewer?file={response_data['document_proxy_url']}&name={file_name}&type={response_data['document_source']['file_type']}"
                    
                    return jsonify(response_data), 200
                    
                except CosmosResourceNotFoundError:
                    return jsonify({"error": "Document not found"}), 404
                except Exception as e:
                    print(f"Error retrieving personal document: {str(e)}")
                    traceback.print_exc()
                    return jsonify({"error": f"Error retrieving document: {str(e)}"}), 500
                
            elif doc_type == "group":
                # Get document from group workspace
                if not group_id:
                    return jsonify({"error": "Group ID is required for group documents"}), 400
                
                try:
                    # Check if user is member of the group
                    group_doc = find_group_by_id(group_id)
                    if not group_doc:
                        return jsonify({"error": "Group not found"}), 404
                    
                    if not is_user_in_group(group_doc, user_id):
                        return jsonify({"error": "Access denied - not a member of this group"}), 403
                    
                    # Get document
                    doc_item = get_group_document(group_id, doc_id)
                    if not doc_item:
                        return jsonify({"error": "Document not found in group"}), 404
                    
                    # Check different possible URL fields in the document
                    doc_url = (doc_item.get('blob_url') or 
                              doc_item.get('document_source_url') or 
                              doc_item.get('storage_url'))
                    
                    if not doc_url:
                        return jsonify({"error": "Document URL not found in database"}), 500
                    
                    response_data = {
                        "document_source": {
                            "name": doc_item.get('file_name', 'Document'),
                            "page": 1,
                            "workspace_type": "group",
                            "file_type": get_file_type(doc_item.get('file_name', '')),
                            "is_viewable": is_viewable_file_type(doc_item.get('file_name', '')),
                            "group_id": group_id
                        },
                        "document_url": doc_url,
                        "download_url": f"/api/group_documents/{doc_id}/download?group_id={group_id}"
                    }
                    
                    # Add document proxy URL with URL encoding for safety
                    if response_data["document_url"]:
                        response_data["document_proxy_url"] = f"/document-proxy?url={urllib.parse.quote(doc_url)}"
                    
                    # Add document viewer URL for viewable documents
                    if response_data["document_source"]["is_viewable"] and response_data.get("document_proxy_url"):
                        file_name = urllib.parse.quote(doc_item.get('file_name', 'Document'))
                        response_data["document_viewer_url"] = f"/document-viewer?file={response_data['document_proxy_url']}&name={file_name}&type={response_data['document_source']['file_type']}"
                    
                    return jsonify(response_data), 200
                
                except Exception as e:
                    print(f"Error fetching group document: {str(e)}")
                    traceback.print_exc()
                    return jsonify({"error": f"Error retrieving group document: {str(e)}"}), 500
            
            elif doc_type == "default":
                # Get document from default documents
                try:
                    doc_item = default_documents_container.read_item(
                        item=doc_id,
                        partition_key=doc_id
                    )
                    
                    # Create response with document info
                    response_data = {
                        "document_source": {
                            "name": doc_item.get('file_name', 'Document'),
                            "page": 1,
                            "workspace_type": "default",
                            "file_type": get_file_type(doc_item.get('file_name', '')),
                            "is_viewable": is_viewable_file_type(doc_item.get('file_name', ''))
                        },
                        "document_url": doc_item.get('storage_url'),
                        "document_proxy_url": f"/document-proxy?url={urllib.parse.quote(doc_item.get('storage_url', ''))}"
                    }
                    
                    # Add document viewer URL for viewable documents
                    if response_data["document_source"]["is_viewable"]:
                        file_name = urllib.parse.quote(doc_item.get('file_name', 'Document'))
                        response_data["document_viewer_url"] = f"/document-viewer?file={response_data['document_proxy_url']}&name={file_name}&type={response_data['document_source']['file_type']}"
                    
                    return jsonify(response_data), 200
                    
                except CosmosResourceNotFoundError:
                    return jsonify({"error": "Document not found"}), 404
                except Exception as e:
                    print(f"Error retrieving default document: {str(e)}")
                    traceback.print_exc()
                    return jsonify({"error": f"Error retrieving document: {str(e)}"}), 500
            
            else:
                return jsonify({"error": "Invalid document type"}), 400
                
        except Exception as e:
            print(f"Error in get_document_view: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "error": "Server error processing document view request",
                "details": str(e)
            }), 500

    # Helper functions
    def get_file_type(filename):
        """Determine file type from filename"""
        if not filename:
            return None
            
        extension = filename.split('.')[-1].lower() if '.' in filename else ''
        
        if extension in ['pdf']:
            return 'pdf'
        elif extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
            return 'image'
        elif extension in ['docx', 'doc']:
            return 'docx'
        elif extension in ['xlsx', 'xls']:
            return 'xlsx'
        elif extension in ['pptx', 'ppt']:
            return 'pptx'
        elif extension in ['txt', 'log', 'md']:
            return 'text'
        elif extension in ['csv']:
            return 'csv'
        
        return None

    def is_viewable_file_type(filename):
        """Check if file can be viewed in the browser"""
        file_type = get_file_type(filename)
        return file_type in ['pdf', 'image', 'text', 'csv']