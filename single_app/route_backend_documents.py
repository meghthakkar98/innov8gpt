from config import *
from functions_authentication import *
from functions_documents import *
from functions_settings import *
import os
import tempfile
import json
import traceback
from werkzeug.utils import secure_filename
from functions_blob_storage import *


def register_route_backend_documents(app):
    @app.route('/api/get_file_content', methods=['POST'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def get_file_content():
        data = request.get_json()
        user_id = get_current_user_id()
        conversation_id = data.get('conversation_id')
        file_id = data.get('file_id')

        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not conversation_id or not file_id:
            return jsonify({'error': 'Missing conversation_id or file_id'}), 400

        try:
            conversation_item = container.read_item(
                item=conversation_id,
                partition_key=conversation_id
            )
            messages = conversation_item.get('messages', [])
            for message in messages:
                if message.get('role') == 'file' and message.get('file_id') == file_id:
                    file_content = message.get('file_content')
                    filename = message.get('filename')
                    is_table = message.get('is_table', False)
                    if file_content:
                        return jsonify({
                            'file_content': file_content,
                            'filename': filename,
                            'is_table': is_table
                        }), 200
                    else:
                        return jsonify({'error': 'File content not found'}), 404

            return jsonify({'error': 'File not found in conversation'}), 404

        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': 'Error retrieving file content'}), 500

    

    @app.route('/api/documents/upload', methods=['POST'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def upload_document():
        print("🔵 Route hit: /api/documents/upload")
        try:
            print("🟡 Processing document upload request")
            user_id = get_current_user_id()
            settings = get_settings()

            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401
            
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['file']
            if not file.filename:
                return jsonify({'error': 'No selected file'}), 400

            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            max_file_size_bytes = settings.get('max_file_size_mb', 16) * 1024 * 1024
            if file_length > max_file_size_bytes:
                return jsonify({'error': 'File size exceeds maximum allowed size'}), 400
            file.seek(0)
            
            # Log file information for debugging
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            print(f"Processing file: {filename}, type: {file_ext}, size: {file_length} bytes")
            
            # Check file type
            if not allowed_file(filename):
                return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
            
            try:
                # Use the process_file_with_blob_storage function
                document_id = process_file_with_blob_storage(file, user_id)
                
                if not document_id:
                    return jsonify({'error': 'Failed to process document - no document ID returned'}), 500
                    
                return jsonify({
                    'message': 'Document uploaded and processed successfully', 
                    'document_id': document_id
                }), 200
                
            except Exception as e:
                print(f"🔴 Document processing error: {str(e)}")
                traceback.print_exc()
                
                # Provide a more detailed error message
                error_details = str(e)
                
                # Check for common error patterns
                if "MissingIndexDocumentsActions" in error_details:
                    error_message = "Failed to create document chunks. The document may be empty or in an unsupported format."
                elif "Unauthorized" in error_details:
                    error_message = "Authorization error accessing Azure services. Please contact your administrator."
                elif "Content extraction failed" in error_details:
                    error_message = "Could not extract text from document. Please try a different file format."
                else:
                    error_message = f"Error processing document: {error_details}"
                    
                return jsonify({'error': error_message}), 500

        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


    @app.route('/api/documents', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def api_get_user_documents():
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        return get_user_documents(user_id)

    @app.route('/api/documents/<document_id>', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def api_get_user_document(document_id):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        return get_user_document(user_id, document_id)
    
    @app.route('/api/documents/<document_id>/download', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def api_download_document(document_id):
        """Download the original document from Blob Storage"""
        user_id = get_current_user_id()
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
            
        try:
            # Get document metadata
            query = """
                SELECT c.blob_url, c.file_name
                FROM c 
                WHERE c.id = @document_id AND c.user_id = @user_id
            """
            parameters = [
                {"name": "@document_id", "value": document_id},
                {"name": "@user_id", "value": user_id}
            ]
            
            results = list(documents_container.query_items(
                query=query, 
                parameters=parameters, 
                enable_cross_partition_query=True
            ))
            
            if not results or not results[0].get('blob_url'):
                return jsonify({'error': 'Document not found or no blob URL available'}), 404
                
            blob_url = results[0]['blob_url']
            file_name = results[0]['file_name']
            
            # Download the blob
            file_content = download_from_blob_storage(blob_url)
            
            # Create a temporary file to serve
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(file_content)
                temp_file_path = tmp_file.name
                
            response = send_file(
                temp_file_path,
                as_attachment=True,
                download_name=file_name,
                max_age=0
            )
            
            # Delete the temporary file after sending
            @response.call_on_close
            def cleanup():
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
            return response
            
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Error downloading document: {str(e)}'}), 500

    @app.route('/api/documents/<document_id>', methods=['DELETE'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def api_delete_user_document(document_id):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        try:
            delete_user_document(user_id, document_id)
            delete_user_document_chunks(document_id)
            return jsonify({'message': 'Document deleted successfully'}), 200
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Error deleting document: {str(e)}'}), 500


    @app.route("/api/get_citation", methods=["POST"])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def get_citation():
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid request data - missing JSON body"}), 400
                    
            user_id = get_current_user_id()
            
            # Get citation ID and expected details
            citation_id = data.get("citation_id")
            expected_filename = data.get("expected_filename")
            expected_page = data.get("expected_page", 1)
            doc_group_id = data.get("doc_group_id")  # Get the specific group ID if provided
            
            if not citation_id:
                return jsonify({"error": "Missing citation ID"}), 400
            
            print(f"Citation request: ID={citation_id}, User={user_id}, Group={doc_group_id}, Expected filename={expected_filename}")
            
            # Try to parse citation ID to get document ID and chunk sequence
            try:
                parts = citation_id.split('_')
                if len(parts) >= 2:
                    document_id = '_'.join(parts[:-1])  # Everything except the last part
                    chunk_sequence = parts[-1]          # Last part is the chunk sequence
                    print(f"Parsed citation ID: document_id={document_id}, chunk_sequence={chunk_sequence}")
                else:
                    # If we can't parse the citation ID, set these to None 
                    document_id = None
                    chunk_sequence = None
                    print(f"Warning: Could not parse citation ID {citation_id} into document_id and chunk_sequence")
            except Exception as e:
                print(f"Error parsing citation ID: {str(e)}")
                document_id = None
                chunk_sequence = None
            
            # First: If a specific group ID was provided, look there first
            if doc_group_id and document_id:
                print(f"Searching in specific group: {doc_group_id}")
                search_client_group = CLIENTS.get("search_client_group")
                if search_client_group:
                    try:
                        # Try to find the chunk directly in that group's index
                        direct_chunk_results = list(search_client_group.search(
                            search_text="*",
                            filter=f"document_id eq '{document_id}' and group_id eq '{doc_group_id}'",
                            select=["id", "chunk_text", "file_name", "page_number", "document_id", "blob_url", "group_id"],
                            top=1
                        ))
                        
                        if direct_chunk_results:
                            chunk_data = direct_chunk_results[0]
                            found_doc_id = chunk_data.get("document_id")
                            group_id = chunk_data.get("group_id")
                            
                            print(f"DIRECT MATCH in specified group: Found chunk for document {found_doc_id}, group {group_id}")
                            
                            # Get document URL and metadata
                            file_name = chunk_data.get("file_name", "Document")
                            page_number = chunk_data.get("page_number", 1)
                            
                            try:
                                doc_results = list(group_documents_container.query_items(
                                    query="SELECT c.id, c.file_name, c.document_source_url, c.blob_url, c.storage_url FROM c WHERE c.id = @id AND c.group_id = @group_id",
                                    parameters=[
                                        {"name": "@id", "value": found_doc_id},
                                        {"name": "@group_id", "value": group_id}
                                    ],
                                    enable_cross_partition_query=True
                                ))
                                
                                document_url = None
                                if doc_results:
                                    document_url = (doc_results[0].get("document_source_url") or 
                                                doc_results[0].get("blob_url") or 
                                                doc_results[0].get("storage_url"))
                                    file_name = doc_results[0].get("file_name", file_name)
                                else:
                                    # If document not found in metadata, try using storage URL from chunk
                                    document_url = chunk_data.get("storage_url") or chunk_data.get("blob_url")
                                
                                # Detect file type
                                file_type = None
                                if file_name:
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
                                
                                # Check if document is viewable in browser
                                is_viewable = file_type in ['pdf', 'image', 'text', 'csv']
                                
                                # Use document-proxy for the URL
                                document_proxy_url = f"/document-proxy?url={document_url}" if document_url else None
                                
                                # Set document viewer URL for viewable documents
                                document_viewer_url = None
                                download_url = None
                                
                                if document_url:
                                    if is_viewable:
                                        document_viewer_url = f"/document-viewer?file={document_proxy_url}&page={page_number}&name={file_name}"
                                        if file_type:
                                            document_viewer_url += f"&type={file_type}"
                                    
                                    # Create a download URL for documents
                                    download_url = f"/api/group_documents/{found_doc_id}/download?group_id={group_id}"
                                
                                response_data = {
                                    "document_source": {
                                        "name": file_name,
                                        "page": page_number,
                                        "workspace_type": "group",
                                        "file_type": file_type,
                                        "is_viewable": is_viewable,
                                        "group_id": group_id
                                    },
                                    "cited_text": chunk_data.get("chunk_text", "Text not available"),
                                    "document_url": document_url,
                                    "document_proxy_url": document_proxy_url,
                                    "document_viewer_url": document_viewer_url,
                                    "download_url": download_url
                                }
                                
                                print(f"RETURNING DATA FOR SPECIFIC GROUP DOCUMENT: {file_name}")
                                return jsonify(response_data), 200
                                    
                            except Exception as e:
                                print(f"Error getting group document URL: {str(e)}")
                                traceback.print_exc()
                    except Exception as e:
                        print(f"Error in direct citation search for specific group: {str(e)}")
                        traceback.print_exc()
            
            # Second attempt: If we have a filename, try filename-based search
            if expected_filename:
                print(f"Prioritizing search for documents matching filename: {expected_filename}")
                
                # Direct search for the expected filename in both indexes
                search_clients = [
                    ("user", CLIENTS.get("search_client_user")),
                    ("group", CLIENTS.get("search_client_group"))
                ]
                
                for type_name, client in search_clients:
                    if not client:
                        continue
                    
                    try:
                        # Use top=100 to ensure we get a good sample
                        filename_results = list(client.search(
                            search_text=expected_filename,
                            select=["id", "chunk_text", "file_name", "chunk_sequence", "page_number", "document_id", "is_default", "storage_url", "group_id"],
                            top=100
                        ))
                        
                        # Filter for exact filename matches
                        exact_matches = [r for r in filename_results if r.get("file_name", "").lower() == expected_filename.lower()]
                        
                        if exact_matches:
                            # We found documents with the exact expected filename - use the first one
                            chunk_data = exact_matches[0]
                            document_id = chunk_data.get("document_id")
                            
                            print(f"FILENAME MATCH SUCCESS: Found exact match for {expected_filename} in {type_name} index")
                            print(f"Using document_id={document_id}, filename={chunk_data.get('file_name')}")
                            
                            # Process this document
                            client_type = type_name
                            is_default_document = chunk_data.get('is_default', False)
                            group_id = chunk_data.get('group_id')
                            
                            # Get document URL based on document type and make sure we use the right metadata
                            document_url = None
                            file_type = None
                            file_name = chunk_data.get('file_name', 'Document')
                            storage_url = chunk_data.get('storage_url', None)
                            page_number = chunk_data.get("page_number", expected_page)
                            
                            # Convert page number to integer
                            try:
                                page_number = int(page_number)
                                if page_number < 1:
                                    page_number = 1
                            except (ValueError, TypeError):
                                page_number = expected_page
                            
                            # Fetch document URL based on type
                            if is_default_document:
                                # Default document
                                try:
                                    doc_results = list(default_documents_container.query_items(
                                        query="SELECT c.id, c.file_name, c.storage_url FROM c WHERE c.id = @id",
                                        parameters=[{"name": "@id", "value": document_id}],
                                        enable_cross_partition_query=True
                                    ))
                                    
                                    if doc_results:
                                        document_url = doc_results[0].get("storage_url") or storage_url
                                        file_name = doc_results[0].get("file_name", file_name)
                                except Exception as e:
                                    print(f"Error getting default document URL: {str(e)}")
                            
                            elif client_type == "user":
                                # User document
                                try:
                                    doc_results = list(documents_container.query_items(
                                        query="SELECT c.id, c.file_name, c.storage_url FROM c WHERE c.id = @id",
                                        parameters=[{"name": "@id", "value": document_id}],
                                        enable_cross_partition_query=True
                                    ))
                                    
                                    if doc_results:
                                        document_url = doc_results[0].get("storage_url") or storage_url
                                        file_name = doc_results[0].get("file_name", file_name)
                                except Exception as e:
                                    print(f"Error getting user document URL: {str(e)}")
                            
                            elif client_type == "group":
                                # Group document
                                try:
                                    doc_results = list(group_documents_container.query_items(
                                        query="SELECT c.id, c.file_name, c.document_source_url, c.blob_url, c.storage_url FROM c WHERE c.id = @id",
                                        parameters=[{"name": "@id", "value": document_id}],
                                        enable_cross_partition_query=True
                                    ))
                                    
                                    if doc_results:
                                        document_url = (doc_results[0].get("document_source_url") or 
                                                    doc_results[0].get("blob_url") or 
                                                    doc_results[0].get("storage_url") or 
                                                    storage_url)
                                        file_name = doc_results[0].get("file_name", file_name)
                                except Exception as e:
                                    print(f"Error getting group document URL: {str(e)}")
                            
                            # If document_url is still None but storage_url exists in chunk_data, use that
                            if not document_url and storage_url:
                                document_url = storage_url
                            
                            # FINAL VERIFICATION: Make sure file_name matches expected_filename
                            if file_name.lower() != expected_filename.lower():
                                print(f"WARNING: Final filename {file_name} doesn't match expected {expected_filename}")
                                print(f"Looking for alternative documents...")
                                
                                # Try one more search to find a better match
                                try:
                                    # Direct search in the document metadata table
                                    if client_type == "user":
                                        direct_doc_results = list(documents_container.query_items(
                                            query="SELECT c.id, c.file_name, c.storage_url FROM c WHERE CONTAINS(c.file_name, @filename)",
                                            parameters=[{"name": "@filename", "value": expected_filename}],
                                            enable_cross_partition_query=True
                                        ))
                                        
                                        if direct_doc_results:
                                            document_id = direct_doc_results[0].get("id")
                                            document_url = direct_doc_results[0].get("storage_url")
                                            file_name = direct_doc_results[0].get("file_name")
                                            print(f"Found better document match: {file_name}")
                                    elif client_type == "group":
                                        direct_doc_results = list(group_documents_container.query_items(
                                            query="SELECT c.id, c.file_name, c.document_source_url, c.blob_url, c.storage_url FROM c WHERE CONTAINS(c.file_name, @filename)",
                                            parameters=[{"name": "@filename", "value": expected_filename}],
                                            enable_cross_partition_query=True
                                        ))
                                        
                                        if direct_doc_results:
                                            document_id = direct_doc_results[0].get("id")
                                            document_url = (direct_doc_results[0].get("document_source_url") or 
                                                        direct_doc_results[0].get("blob_url") or 
                                                        direct_doc_results[0].get("storage_url"))
                                            file_name = direct_doc_results[0].get("file_name")
                                            print(f"Found better document match: {file_name}")
                                except Exception as e:
                                    print(f"Error in final verification search: {str(e)}")
                            
                            # Detect file type from file name
                            if file_name:
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
                            
                            workspace_type = "default" if is_default_document else client_type
                            
                            # Check if document is viewable in browser
                            is_viewable = file_type in ['pdf', 'image', 'text', 'csv']
                            
                            # Use document-proxy for the URL to support all file types
                            document_proxy_url = f"/document-proxy?url={document_url}" if document_url else None
                            
                            # Set document viewer URL for viewable documents
                            document_viewer_url = None
                            download_url = None
                            
                            if document_url:
                                if is_viewable:
                                    document_viewer_url = f"/document-viewer?file={document_proxy_url}&page={page_number}&name={file_name}"
                                    if file_type:
                                        document_viewer_url += f"&type={file_type}"
                                
                                # Create a download URL for documents
                                download_url = f"/api/documents/{document_id}/download"
                                if client_type == "group":
                                    # For group documents, include the group ID
                                    group_download_id = group_id if group_id else chunk_data.get('group_id')
                                    if group_download_id:
                                        download_url = f"/api/group_documents/{document_id}/download?group_id={group_download_id}"
                                    else:
                                        download_url = f"/api/group_documents/{document_id}/download"
                                elif is_default_document:
                                    # For default documents, use document-proxy as download URL
                                    download_url = document_proxy_url
                            
                            response_data = {
                                "document_source": {
                                    "name": file_name,
                                    "page": page_number,
                                    "workspace_type": workspace_type,
                                    "file_type": file_type,
                                    "is_viewable": is_viewable,
                                    "group_id": group_id
                                },
                                "cited_text": chunk_data.get("chunk_text", "Text not available"),
                                "document_url": document_url,
                                "document_proxy_url": document_proxy_url,
                                "document_viewer_url": document_viewer_url,
                                "download_url": download_url
                            }
                            
                            print(f"RETURNING DATA FOR FILE: {file_name}")
                            return jsonify(response_data), 200
                    except Exception as e:
                        print(f"Error in filename-based search: {str(e)}")
                        traceback.print_exc()

            # Third attempt: If we couldn't find by filename or if filename wasn't provided,
            # try direct citation ID lookup
            print("Looking up citation by ID:", citation_id)
            
            # Check if we have a valid document_id and chunk_sequence from parsing the citation_id
            if document_id and chunk_sequence:
                # First, check user documents
                search_client_user = CLIENTS.get("search_client_user")
                if search_client_user:
                    try:
                        # Try to find the chunk directly
                        direct_chunk_results = list(search_client_user.search(
                            search_text="*",
                            filter=f"id eq '{citation_id}'",
                            select=["id", "chunk_text", "file_name", "page_number", "document_id", "storage_url"],
                            top=1
                        ))
                        
                        if not direct_chunk_results:
                            # Try to find by document ID and chunk sequence
                            direct_chunk_results = list(search_client_user.search(
                                search_text="*",
                                filter=f"document_id eq '{document_id}' and chunk_sequence eq {chunk_sequence}",
                                select=["id", "chunk_text", "file_name", "page_number", "document_id", "storage_url"],
                                top=1
                            ))
                        
                        if direct_chunk_results:
                            chunk_data = direct_chunk_results[0]
                            found_doc_id = chunk_data.get("document_id")
                            
                            print(f"DIRECT MATCH: Found chunk for document {found_doc_id}")
                            
                            # Get document URL and metadata
                            file_name = chunk_data.get("file_name", "Document")
                            page_number = chunk_data.get("page_number", 1)
                            
                            try:
                                doc_results = list(documents_container.query_items(
                                    query="SELECT c.id, c.file_name, c.storage_url FROM c WHERE c.id = @id",
                                    parameters=[{"name": "@id", "value": found_doc_id}],
                                    enable_cross_partition_query=True
                                ))
                                
                                document_url = None
                                if doc_results:
                                    document_url = doc_results[0].get("storage_url") or chunk_data.get("storage_url")
                                    file_name = doc_results[0].get("file_name", file_name)
                                else:
                                    # If document not found in metadata, try using storage URL from chunk
                                    document_url = chunk_data.get("storage_url")
                                
                                # Detect file type
                                file_type = None
                                if file_name:
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
                                
                                # Check if document is viewable in browser
                                is_viewable = file_type in ['pdf', 'image', 'text', 'csv']
                                
                                # Use document-proxy for the URL
                                document_proxy_url = f"/document-proxy?url={document_url}" if document_url else None
                                
                                # Set document viewer URL for viewable documents
                                document_viewer_url = None
                                download_url = None
                                
                                if document_url:
                                    if is_viewable:
                                        document_viewer_url = f"/document-viewer?file={document_proxy_url}&page={page_number}&name={file_name}"
                                        if file_type:
                                            document_viewer_url += f"&type={file_type}"
                                    
                                    # Create a download URL for documents
                                    download_url = f"/api/documents/{found_doc_id}/download"
                                
                                response_data = {
                                    "document_source": {
                                        "name": file_name,
                                        "page": page_number,
                                        "workspace_type": "user",
                                        "file_type": file_type,
                                        "is_viewable": is_viewable
                                    },
                                    "cited_text": chunk_data.get("chunk_text", "Text not available"),
                                    "document_url": document_url,
                                    "document_proxy_url": document_proxy_url,
                                    "document_viewer_url": document_viewer_url,
                                    "download_url": download_url
                                }
                                
                                print(f"RETURNING DATA FOR USER DOCUMENT: {file_name}")
                                return jsonify(response_data), 200
                                
                            except Exception as e:
                                print(f"Error getting document URL: {str(e)}")
                                traceback.print_exc()
                                
                    except Exception as e:
                        print(f"Error in direct citation search (user docs): {str(e)}")
                        traceback.print_exc()
                
                # If not found in user documents, check group documents (in all groups)
                search_client_group = CLIENTS.get("search_client_group")
                if search_client_group:
                    try:
                        # Try to find the chunk directly
                        direct_chunk_results = list(search_client_group.search(
                            search_text="*",
                            filter=f"id eq '{citation_id}'",
                            select=["id", "chunk_text", "file_name", "page_number", "document_id", "group_id", "storage_url", "blob_url"],
                            top=1
                        ))
                        
                        if not direct_chunk_results:
                            # Try to find by document ID and chunk sequence (in any group)
                            direct_chunk_results = list(search_client_group.search(
                                search_text="*",
                                filter=f"document_id eq '{document_id}' and chunk_sequence eq {chunk_sequence}",
                                select=["id", "chunk_text", "file_name", "page_number", "document_id", "group_id", "storage_url", "blob_url"],
                                top=1
                            ))
                        
                        if direct_chunk_results:
                            chunk_data = direct_chunk_results[0]
                            found_doc_id = chunk_data.get("document_id")
                            group_id = chunk_data.get("group_id")
                            
                            print(f"DIRECT MATCH: Found group document chunk for document {found_doc_id}, group {group_id}")
                            
                            # Get document URL and metadata
                            file_name = chunk_data.get("file_name", "Document")
                            page_number = chunk_data.get("page_number", 1)
                            
                            try:
                                doc_results = list(group_documents_container.query_items(
                                    query="SELECT c.id, c.file_name, c.document_source_url, c.blob_url, c.storage_url FROM c WHERE c.id = @id",
                                    parameters=[{"name": "@id", "value": found_doc_id}],
                                    enable_cross_partition_query=True
                                ))
                                
                                document_url = None
                                if doc_results:
                                    document_url = (doc_results[0].get("document_source_url") or 
                                                doc_results[0].get("blob_url") or 
                                                doc_results[0].get("storage_url"))
                                    file_name = doc_results[0].get("file_name", file_name)
                                else:
                                    # If document not found in metadata, try using storage URL from chunk
                                    document_url = chunk_data.get("storage_url") or chunk_data.get("blob_url")
                                
                                # Detect file type
                                file_type = None
                                if file_name:
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
                                
                                # Check if document is viewable in browser
                                is_viewable = file_type in ['pdf', 'image', 'text', 'csv']
                                
                                # Use document-proxy for the URL
                                document_proxy_url = f"/document-proxy?url={document_url}" if document_url else None
                                
                                # Set document viewer URL for viewable documents
                                document_viewer_url = None
                                download_url = None
                                
                                if document_url:
                                    if is_viewable:
                                        document_viewer_url = f"/document-viewer?file={document_proxy_url}&page={page_number}&name={file_name}"
                                        if file_type:
                                            document_viewer_url += f"&type={file_type}"
                                    
                                    # Create a download URL for documents
                                    download_url = f"/api/group_documents/{found_doc_id}/download?group_id={group_id}"
                                
                                response_data = {
                                    "document_source": {
                                        "name": file_name,
                                        "page": page_number,
                                        "workspace_type": "group",
                                        "file_type": file_type,
                                        "is_viewable": is_viewable,
                                        "group_id": group_id
                                    },
                                    "cited_text": chunk_data.get("chunk_text", "Text not available"),
                                    "document_url": document_url,
                                    "document_proxy_url": document_proxy_url,
                                    "document_viewer_url": document_viewer_url,
                                    "download_url": download_url
                                }
                                
                                print(f"RETURNING DATA FOR GROUP DOCUMENT: {file_name}")
                                return jsonify(response_data), 200
                                
                            except Exception as e:
                                print(f"Error getting group document URL: {str(e)}")
                                traceback.print_exc()
                                
                    except Exception as e:
                        print(f"Error in direct citation search (group docs): {str(e)}")
                        traceback.print_exc()
            
            # If we got here, we couldn't find the document
            print(f"ERROR: Could not find document for citation ID {citation_id}")
            
            # Return a minimal response with just the cited text
            return jsonify({
                "document_source": {
                    "name": expected_filename or "Document",
                    "page": expected_page,
                    "workspace_type": "unknown",
                    "file_type": None,
                    "is_viewable": False
                },
                "cited_text": "The cited source cannot be found or accessed. The document may have been deleted or you may not have access to it."
            }), 200

        except Exception as e:
            print(f"Error in get_citation: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"Server error processing citation: {str(e)}"}), 500

    # Add this route to your Flask application
    @app.route("/api/debug_citation/<citation_id>", methods=["GET"])
    @login_required
    @user_required
    def debug_citation(citation_id):
        try:
            parts = citation_id.split('_')
            if len(parts) >= 2:
                document_id = '_'.join(parts[:-1])
                chunk_sequence = parts[-1]
                
                # Try to get the document
                try:
                    document = documents_container.read_item(
                        item=document_id,
                        partition_key=document_id
                    )
                    
                    # Try to get the chunk
                    search_client = CLIENTS.get('search_client_user')
                    results = list(search_client.search(
                        search_text="*",
                        filter=f"document_id eq '{document_id}' and chunk_sequence eq {chunk_sequence}",
                        select=["chunk_text", "file_name", "chunk_sequence", "document_id"]
                    ))
                    
                    return jsonify({
                        "document": document,
                        "has_blob_url": "blob_url" in document,
                        "chunk": results[0] if results else None
                    })
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    

    @app.route('/pdf-viewer')
    @login_required
    def pdf_viewer():
        """
        Serves a PDF viewer page that can load PDFs from blob storage.
        This route accepts a 'file' parameter with the blob URL.
        
        Optional parameters:
        - page: The page number to open (default is 1)
        - zoom: The zoom level (default is 'auto')
        """
        file_url = request.args.get('file', '')
        page = request.args.get('page', 1)
        # Make sure page is correctly converted to an integer
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
            
        zoom = request.args.get('zoom', 'auto')
        
        # Validate that the user has access to this file
        user_id = get_current_user_id()
        if not user_id:
            return "Unauthorized", 401
        
        # Serve the PDF viewer page with the explicit page number
        return render_template('pdf_viewer.html', 
                            file_url=file_url,
                            page=page,
                            zoom=zoom)
    
    
    @app.route('/document-proxy', endpoint='document_proxy_backend')
    @login_required
    def document_proxy():
        """
        Proxy for document requests to blob storage.
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
            
            # Get content type from the blob
            content_type = None
            try:
                properties = get_blob_properties(blob_url)
                content_type = properties.content_settings.content_type
            except:
                # If we can't get the content type, try to determine it from the URL
                if blob_url.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif blob_url.lower().endswith('.docx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif blob_url.lower().endswith('.xlsx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                else:
                    content_type = 'application/octet-stream'
            
            # Return the file as a response
            return Response(
                file_content,
                mimetype=content_type,
                headers={
                    'Content-Disposition': 'inline',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        except Exception as e:
            print(f"Error serving document: {str(e)}")