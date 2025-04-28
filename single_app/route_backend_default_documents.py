# route_backend_default_documents.py

from config import *
from functions_authentication import *
from functions_documents import *
from functions_settings import *
from functions_content import extract_content_with_azure_di, chunk_text, generate_embedding
import os
import tempfile

def register_route_backend_default_documents(app):
    @app.route('/api/default_documents', methods=['GET'])
    @login_required
    @user_required
    def get_default_documents():
        """Get a list of all available default documents."""
        try:
            query = """
                SELECT c.file_name, c.id, c.upload_date, c.num_chunks, c.version, c.storage_url
                FROM c
                WHERE c.type = 'document_metadata'
            """
            items = list(default_documents_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            # Get latest version of each document
            latest_documents = {}
            for doc in items:
                file_name = doc['file_name']
                if file_name not in latest_documents or doc['version'] > latest_documents[file_name]['version']:
                    latest_documents[file_name] = doc
                    
            return jsonify({"documents": list(latest_documents.values())}), 200
        except Exception as e:
            return jsonify({'error': f'Error retrieving default documents: {str(e)}'}), 500
    
    @app.route('/api/default_documents/upload', methods=['POST'])
    @login_required
    @admin_required
    def upload_default_document():
        """Admin-only route to upload a default document."""
        try:
            print("🔵 Route hit: /api/default_documents/upload")
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['file']
            if not file.filename:
                return jsonify({'error': 'No selected file'}), 400

            # Store the document in a similar way to personal documents
            document_id = process_default_document(file)
            
            return jsonify({'message': 'Default document uploaded successfully', 'document_id': document_id}), 200
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Error uploading default document: {str(e)}'}), 500
    
    @app.route('/api/default_documents/<document_id>', methods=['DELETE'])
    @login_required
    @admin_required
    def delete_default_document(document_id):
        """Admin-only route to delete a default document."""
        try:
            delete_default_document_by_id(document_id)
            delete_default_document_chunks(document_id)
            return jsonify({'message': 'Default document deleted successfully'}), 200
        except Exception as e:
            return jsonify({'error': f'Error deleting document: {str(e)}'}), 500

def process_default_document(file):
    """Process and store a default document, similar to personal documents."""
    settings = get_settings()
    filename = secure_filename(file.filename)
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    max_bytes = settings.get('max_file_size_mb', 16) * 1024 * 1024
    if file_length > max_bytes:
        raise Exception("File size exceeds maximum allowed size")
    file.seek(0)
    
    # Read file content and create a temporary file
    file_content = file.read()
    
    # Upload to Blob Storage
    content_type = get_content_type_from_extension(filename)
    blob_url = upload_to_blob_storage(file_content, filename, content_type)
    
    # Process with appropriate content extraction method
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(file_content)
        temp_file_path = tmp_file.name
    
    try:
        file_ext = os.path.splitext(filename)[1].lower()
        extraction_result = extract_file_content(temp_file_path, file_ext)
        
        if not extraction_result:
            raise Exception("Failed to extract content")
    
        # Process the document and store chunks
        document_id = process_default_document_chunks(extraction_result, filename, blob_url)
        return document_id
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def extract_file_content(temp_file_path, file_ext):
    """Extract content from the uploaded file based on its type."""
    if file_ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.html', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heif']:
        return extract_content_with_azure_di(temp_file_path)
    elif file_ext == '.txt':
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return {
                "content": [{
                    "page_number": 1,
                    "text": content
                }],
                "pages_info": [{
                    "page_number": 1,
                    "text": content
                }]
            }
    elif file_ext == '.md':
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return {
                "content": [{
                    "page_number": 1,
                    "text": content
                }],
                "pages_info": [{
                    "page_number": 1,
                    "text": content
                }]
            }
    elif file_ext == '.json':
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
            content = json.dumps(json_content, indent=2)
            return {
                "content": [{
                    "page_number": 1,
                    "text": content
                }],
                "pages_info": [{
                    "page_number": 1,
                    "text": content
                }]
            }
    else:
        raise Exception("Unsupported file type")

def get_content_type_from_extension(filename):
    """Determine content type based on file extension."""
    file_ext = os.path.splitext(filename)[1].lower()
    content_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.json': 'application/json',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.heif': 'image/heif'
    }
    return content_types.get(file_ext, 'application/octet-stream')

def process_default_document_chunks(extraction_result, file_name, blob_url):
    """Process the content and create chunks for the search index."""
    # Generate chunks with page information
    pages_content = extraction_result["content"]
    chunks_with_pages = chunk_text(pages_content)
    
    document_id = str(uuid.uuid4())
    num_chunks = len(chunks_with_pages)
    version = 1
    
    # Check for existing document with the same name
    existing_query = """
        SELECT c.version 
        FROM c 
        WHERE c.file_name = @file_name AND c.type='document_metadata'
    """
    parameters = [{"name": "@file_name", "value": file_name}]
    
    existing_document = list(default_documents_container.query_items(
        query=existing_query, 
        parameters=parameters, 
        enable_cross_partition_query=True
    ))
    
    if existing_document:
        version = max(existing_document[0]['version'] + 1, 1)
    
    current_time = datetime.now(timezone.utc)
    formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Create metadata document
    document_metadata = {
        "id": document_id,
        "num_chunks": num_chunks,
        "file_name": file_name,
        "upload_date": formatted_time,
        "version": version,
        "type": "document_metadata",
        "storage_url": blob_url  
    }
    
    default_documents_container.upsert_item(document_metadata)
    
    # Add chunks to search index
    chunk_documents = []
    search_client = CLIENTS["search_client_user"]  # Reuse the same search client as personal docs
    
    for idx, (chunk_text_content, page_number) in enumerate(chunks_with_pages):
        chunk_id = f"{document_id}_{idx}"
        
        try:
            embedding = generate_embedding(chunk_text_content)
        except Exception as e:
            print(f"Error generating embedding for chunk {idx}: {e}")
            embedding = None
        
        # Ensure page_number is always stored as an integer
        try:
            page_num_int = int(page_number)
            if page_num_int < 1:
                page_num_int = 1
        except (ValueError, TypeError):
            print(f"Warning: Could not convert page_number {page_number} to integer, using 1")
            page_num_int = 1
            
        chunk_document = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_id": str(idx),
            "chunk_text": chunk_text_content,
            "embedding": embedding,
            "file_name": file_name,
            "chunk_sequence": idx,
            "page_number": page_num_int,
            "upload_date": formatted_time,
            "version": version,
            "storage_url": blob_url,
            "is_default": True  
        }
        
        chunk_documents.append(chunk_document)
    
    try:
        # Upload chunks to the search index
        print(f"Uploading {len(chunk_documents)} chunks to search index")
        search_client.upload_documents(documents=chunk_documents)
        print("Upload to search index complete")
    except Exception as e:
        print(f"Error uploading document chunks to search index: {e}")
        traceback.print_exc()
        raise
    
    return document_id

def delete_default_document_by_id(document_id):
    """Delete a default document from Cosmos DB."""
    try:
        document_item = default_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )
        
        # If the document has a blob URL, delete the blob
        if document_item.get('storage_url'):
            try:
                from functions_blob_storage import delete_blob
                delete_blob(document_item.get('storage_url'))
                print(f"Deleted blob: {document_item.get('storage_url')}")
            except Exception as blob_err:
                print(f"Error deleting blob: {str(blob_err)}")
        
        default_documents_container.delete_item(
            item=document_id,
            partition_key=document_id
        )
    except CosmosResourceNotFoundError:
        raise Exception("Document not found")
    except Exception as e:
        raise

def delete_default_document_chunks(document_id):
    """Delete document chunks from Azure Cognitive Search index."""
    try:
        search_client = CLIENTS["search_client_user"]
        results = search_client.search(
            search_text="*",
            filter=f"document_id eq '{document_id}'",
            select=["id"]
        )
        
        ids_to_delete = [doc['id'] for doc in results]
        
        if not ids_to_delete:
            return
        
        documents_to_delete = [{"id": doc_id} for doc_id in ids_to_delete]
        batch = IndexDocumentsBatch()
        batch.add_delete_actions(documents_to_delete)
        result = search_client.index_documents(batch)
    except Exception as e:
        raise