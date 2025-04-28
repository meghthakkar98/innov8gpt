# functions_documents.py

from config import *
from functions_content import *
from functions_settings import *
from functions_blob_storage import upload_to_blob_storage, download_from_blob_storage
from azure.search.documents import SearchClient

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential


def allowed_file(filename, allowed_extensions=None):
    if not allowed_extensions:
        allowed_extensions = ALLOWED_EXTENSIONS
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def add_system_message_to_conversation(conversation_id, user_id, content):
    try:
        conversation_item = container.read_item(
            item=conversation_id,
            partition_key=conversation_id
        )

        conversation_item['messages'].append({
            "role": "system",
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation_item['last_updated'] = datetime.utcnow().isoformat()

        container.upsert_item(conversation_item)

    except Exception as e:
        raise e
    
def process_document_and_store_chunks(extraction_result, file_name, user_id, blob_url=None):
    """
    Process extracted content from a document and store it in chunks
    with accurate page number tracking and improved error handling
    """
    settings = get_settings()

    # Get the per-page content
    pages_content = extraction_result["content"]
    
    print(f"Processing document: {file_name} with {len(pages_content)} pages")

    # Generate chunks with page information
    chunks_with_pages = chunk_text(pages_content)
    
    print(f"Generated {len(chunks_with_pages)} chunks")

    document_id = str(uuid.uuid4())
    num_chunks = len(chunks_with_pages)

    # Check for existing document
    existing_document_query = """
        SELECT c.version 
        FROM c 
        WHERE c.file_name = @file_name AND c.user_id = @user_id
    """
    parameters = [{"name": "@file_name", "value": file_name}, {"name": "@user_id", "value": user_id}]
    
    existing_document = list(documents_container.query_items(
        query=existing_document_query, 
        parameters=parameters, 
        enable_cross_partition_query=True
    ))

    version = 1
    if existing_document:
        try:
            version = existing_document[0]['version'] + 1
        except (KeyError, IndexError, TypeError):
            # Handle case where version is missing or invalid
            print(f"Warning: Could not determine previous version for {file_name}")
            version = 1

    current_time = datetime.now(timezone.utc)
    formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    document_metadata = {
        "id": document_id,
        "num_chunks": num_chunks,
        "file_name": file_name,
        "user_id": user_id,
        "upload_date": formatted_time,
        "version": version,
        "type": "document_metadata",
        "storage_url": blob_url  
    }
    
    documents_container.upsert_item(document_metadata)
    chunk_documents = []

    search_client_user = CLIENTS.get("search_client_user")
    if not search_client_user:
        print("ERROR: search_client_user not found in CLIENTS dictionary")
        return document_id

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
            "user_id": user_id,
            "chunk_sequence": idx,
            "page_number": page_num_int,  # Store the actual page number from the original document
            "upload_date": formatted_time,
            "version": version,
            "storage_url": blob_url
        }
        
        print(f"Chunk {idx}: from page {page_num_int}")
        chunk_documents.append(chunk_document)

    try:
        # Only upload if we have chunks and a valid search client
        if chunk_documents and search_client_user:
            print(f"Uploading {len(chunk_documents)} chunks to search index")
            # Upload chunks in batches to prevent timeout issues
            batch_size = 100  # Adjust as needed
            for i in range(0, len(chunk_documents), batch_size):
                batch = chunk_documents[i:i+batch_size]
                search_client_user.upload_documents(documents=batch)
                print(f"Uploaded batch {i//batch_size + 1} with {len(batch)} chunks")
            
            print("Upload to search index complete")
        else:
            print(f"Warning: No chunks to upload or search client invalid - document will have limited searchability")
    except Exception as e:
        print(f"Error uploading document chunks to search index: {e}")
        traceback.print_exc()
        # Don't raise the exception - we still want to return the document ID
        # so the user can at least see their document in the list
    
    return document_id

# Update process_file_with_blob_storage in functions_documents.py

def process_file_with_blob_storage(file, user_id):
    """
    Process an uploaded file using Azure Blob Storage before Document Intelligence
    with improved error handling
    """
    settings = get_settings()
    
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    print(f"Processing file: {filename} with extension {file_ext}")
    
    if not allowed_file(filename):
        raise Exception(f"Unsupported file type: {file_ext}")
    
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    max_bytes = settings.get('max_file_size_mb', 16) * 1024 * 1024
    if file_length > max_bytes:
        raise Exception(f"File size exceeds maximum allowed size ({file_length} > {max_bytes})")
    
    file.seek(0)
    file_content = file.read()
    
    # Upload to Blob Storage with appropriate content type
    content_type = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.csv': 'text/csv'
    }.get(file_ext, 'application/octet-stream')
    
    blob_url = None
    temp_file_path = None
    
    try:
        # Upload file to blob storage
        print(f"Uploading {filename} to blob storage")
        blob_url = upload_to_blob_storage(file_content, filename, content_type)
        print(f"File uploaded to blob storage: {blob_url}")
        
        # Process with Azure Document Intelligence
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(file_content)
            temp_file_path = tmp_file.name
            print(f"Created temporary file: {temp_file_path}")
        
        try:
            # Extract content using Azure Document Intelligence
            print(f"Extracting content with Azure DI from {filename}")
            extraction_result = extract_content_with_azure_di(temp_file_path)
                
            # Process document and store chunks
            print(f"Processing document chunks for {filename}")
            document_id = process_document_and_store_chunks(extraction_result, filename, user_id, blob_url)
            
            if not document_id:
                print("Warning: No document ID returned from processing")
                raise Exception("Document processing failed")
                
            print(f"Document processing completed successfully: {document_id}")
            return document_id
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"Removed temporary file: {temp_file_path}")
    
    except Exception as processing_error:
        # Clean up blob if uploaded but processing failed
        if blob_url:
            try:
                from functions_blob_storage import delete_blob
                delete_blob(blob_url)
                print(f"Deleted blob after processing error: {blob_url}")
            except Exception as cleanup_err:
                print(f"Error during blob cleanup: {str(cleanup_err)}")
        
        # Clean up temp file if still exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"Removed temporary file during error handling: {temp_file_path}")
            except Exception as cleanup_err:
                print(f"Error removing temp file: {str(cleanup_err)}")
                
        print(f"Document processing error: {str(processing_error)}")
        raise
        
def get_user_documents(user_id):
    try:
        query = """
            SELECT c.file_name, c.id, c.upload_date, c.user_id, c.num_chunks, c.version, c.blob_url
            FROM c
            WHERE c.user_id = @user_id
        """
        parameters = [{"name": "@user_id", "value": user_id}]
        
        documents = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        latest_documents = {}

        for doc in documents:
            file_name = doc['file_name']
            if file_name not in latest_documents or doc['version'] > latest_documents[file_name]['version']:
                latest_documents[file_name] = doc
                
        return jsonify({"documents": list(latest_documents.values())}), 200
    except Exception as e:
        return jsonify({'error': f'Error retrieving documents: {str(e)}'}), 500

def get_user_document(user_id, document_id):
    try:
        latest_version_query = """
            SELECT TOP 1 *
            FROM c 
            WHERE c.id = @document_id AND c.user_id = @user_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

        document_results = list(documents_container.query_items(
            query=latest_version_query, 
            parameters=parameters, 
            enable_cross_partition_query=True
        ))

        if not document_results:
            return jsonify({'error': 'Document not found or access denied'}), 404

        return jsonify(document_results[0]), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving document: {str(e)}'}), 500

def get_latest_version(document_id, user_id):
    query = """
        SELECT c.version
        FROM c 
        WHERE c.id = @document_id AND c.user_id = @user_id
    """
    parameters = [
        {"name": "@document_id", "value": document_id},
        {"name": "@user_id", "value": user_id}
    ]

    try:
        results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        if results:
            max_version = max(item['version'] for item in results)
            return max_version
        else:
            return None

    except Exception as e:
        return None
    
def get_user_document_version(user_id, document_id, version):
    try:
        query = """
            SELECT *
            FROM c 
            WHERE c.id = @document_id AND c.user_id = @user_id AND c.version = @version
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id},
            {"name": "@version", "value": version}
        ]
        
        document_results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        if not document_results:
            return jsonify({'error': 'Document version not found'}), 404

        return jsonify(document_results[0]), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving document version: {str(e)}'}), 500

def delete_user_document(user_id, document_id):
    """Delete a document from the user's documents in Cosmos DB."""
    try:
        document_item = documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        if document_item.get('user_id') != user_id:
            raise Exception("Unauthorized access to document")
        
        # If the document has a blob URL, delete the blob
        if document_item.get('storage_url'):  # Changed from blob_url
            try:
                from functions_blob_storage import delete_blob
                delete_blob(document_item.get('storage_url'))  # Changed from blob_url
                print(f"Deleted blob: {document_item.get('storage_url')}")  # Changed from blob_url
            except Exception as blob_err:
                print(f"Error deleting blob: {str(blob_err)}")

        documents_container.delete_item(
            item=document_id,
            partition_key=document_id
        )
    except CosmosResourceNotFoundError:
        raise Exception("Document not found")
    except Exception as e:
        raise

def delete_user_document_chunks(document_id):
    """Delete document chunks from Azure Cognitive Search index."""
    try:
        search_client_user = CLIENTS["search_client_user"]
        results = search_client_user.search(
            search_text="*",
            filter=f"document_id eq '{document_id}'",
            select=["id"]
        )

        ids_to_delete = [doc['id'] for doc in results]

        if not ids_to_delete:
            return

        # Create a list of documents to delete (each one just needs an id)
        documents_to_delete = [{"id": doc_id} for doc_id in ids_to_delete]
        
        # Use the delete_documents method directly instead of IndexDocumentsBatch
        result = search_client_user.delete_documents(documents=documents_to_delete)
        
        print(f"Deleted {len(documents_to_delete)} document chunks")
    except Exception as e:
        print(f"Error deleting document chunks: {str(e)}")
        raise

def delete_user_document_version(user_id, document_id, version):
    query = """
        SELECT c.id, c.blob_url
        FROM c 
        WHERE c.id = @document_id AND c.user_id = @user_id AND c.version = @version
    """
    parameters = [
        {"name": "@document_id", "value": document_id},
        {"name": "@user_id", "value": user_id},
        {"name": "@version", "value": version}
    ]
    documents = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    for doc in documents:
        # If the document has a blob URL, delete the blob
        if doc.get('blob_url'):
            try:
                from functions_blob_storage import delete_blob
                delete_blob(doc.get('blob_url'))
                print(f"Deleted blob for version {version}: {doc.get('blob_url')}")
            except Exception as blob_err:
                print(f"Error deleting blob for version {version}: {str(blob_err)}")
                
        documents_container.delete_item(doc['id'], partition_key=doc['id'])

def delete_user_document_version_chunks(document_id, version):
    search_client_user = CLIENTS["search_client_user"]
    search_client_user.delete_documents(
        actions=[
            {"@search.action": "delete", "id": chunk['id']} for chunk in 
            search_client_user.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and version eq {version}",
                select="id"
            )
        ]
    )

def get_document_versions(user_id, document_id):
    try:
        query = """
            SELECT c.id, c.file_name, c.version, c.upload_date, c.blob_url
            FROM c 
            WHERE c.id = @document_id AND c.user_id = @user_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

        versions_results = list(documents_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        if not versions_results:
            return []
        return versions_results

    except Exception as e:
        return []
    
def detect_doc_type(document_id, user_id=None):
    """
    Check Cosmos to see if this doc belongs to the user's docs (has user_id)
    or the group's docs (has group_id).
    Returns one of: "user", "group", or None if not found.
    Optionally checks if user_id matches (for user docs).
    """

    try:
        doc_item = documents_container.read_item(document_id, partition_key=document_id)
        if user_id and doc_item.get('user_id') != user_id:
            pass
        else:
            return "user"
    except:
        pass

    try:
        group_doc_item = group_documents_container.read_item(document_id, partition_key=document_id)
        return "group"
    except:
        pass

    return None
