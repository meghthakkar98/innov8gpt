# functions_group_documents.py

from config import *
from functions_content import *
from functions_blob_storage import upload_to_blob_storage, download_from_blob_storage, delete_blob

def get_group_documents(group_id):
    """
    List the *latest* version of each file_name that belongs to this group.
    Similar to your user docs approach:
      1) We query all metadata docs for the group
      2) For each file_name, keep the doc with the highest version
    """
    query = """
        SELECT c.file_name, c.id, c.upload_date, c.group_id, c.num_chunks, c.version, c.blob_url
        FROM c
        WHERE c.group_id = @group_id
          AND c.type = "document_metadata"
    """
    parameters = [{"name": "@group_id", "value": group_id}]

    items = list(group_documents_container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    latest_by_filename = {}
    for doc in items:
        fname = doc['file_name']
        if fname not in latest_by_filename or doc['version'] > latest_by_filename[fname]['version']:
            latest_by_filename[fname] = doc

    return list(latest_by_filename.values())


def get_group_document(group_id, document_id):
    """
    Return the *latest version* of a specific document by ID, 
    verifying it belongs to the group.
    We do a TOP 1 query, ordered by version DESC.
    """
    try:
        query = """
            SELECT TOP 1 *
            FROM c
            WHERE c.id = @document_id
              AND c.group_id = @group_id
            ORDER BY c.version DESC
        """
        params = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id",   "value": group_id}
        ]
        results = list(group_documents_container.query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        ))
        if not results:
            return None
        return results[0]
    except Exception as ex:
        print(f"Error in get_group_document: {ex}")
        return None


def get_group_document_version(group_id, document_id, version):
    """
    Return the *specific version* of a group doc in Cosmos.
    """
    try:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
              AND c.group_id = @group_id
              AND c.version = @version
        """
        params = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id",    "value": group_id},
            {"name": "@version",     "value": version}
        ]
        results = list(group_documents_container.query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        ))
        return results[0] if results else None
    except Exception as ex:
        print(f"Error in get_group_document_version: {ex}")
        return None


def get_group_document_versions(group_id, document_id):
    """
    Return *all versions* of the doc in descending order by version.
    """
    try:
        query = """
            SELECT c.id, c.file_name, c.version, c.upload_date, c.blob_url
            FROM c
            WHERE c.id = @document_id
              AND c.group_id = @group_id
            ORDER BY c.version DESC
        """
        params = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id",    "value": group_id}
        ]
        results = list(group_documents_container.query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        ))
        return results
    except Exception as ex:
        print(f"Error retrieving group doc versions: {ex}")
        return []


def get_latest_group_doc_version(group_id, document_id):
    """
    Return the *latest version number* of the doc. 
    If not found, returns None.
    """
    try:
        docs = get_group_document_versions(group_id, document_id)
        if not docs:
            return None
        return max(d['version'] for d in docs)
    except:
        return None


def process_group_document_upload(file, group_id, user_id):
    """
    Process a document uploaded to a group
    """
    settings = get_settings()

    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext.replace('.', '') not in ALLOWED_EXTENSIONS:
        raise Exception("Unsupported file extension")

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    max_bytes = settings.get('max_file_size_mb', 16) * 1024 * 1024
    if file_length > max_bytes:
        raise Exception("File size exceeds maximum allowed size")
    file.seek(0)
    
    # Read the file content
    file_content = file.read()
    
    # Upload to Blob Storage with appropriate content type
    content_type = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain'
    }.get(file_ext, 'application/octet-stream')
        
    try:
        # Upload file to blob storage
        blob_url = upload_to_blob_storage(file_content, filename, content_type)
        print(f"Group file uploaded to blob storage: {blob_url}")
        
        # Extract content based on file type
        extraction_result = None
        try:
            # Create a temporary file to process
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(file_content)
                temp_file_path = tmp_file.name
            
            try:
                if file_ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.html', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heif']:
                    extraction_result = extract_content_with_azure_di(temp_file_path)
                elif file_ext == '.txt':
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        extraction_result = {
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
                        extraction_result = {
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
                        extraction_result = {
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
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        except Exception as content_extract_error:
            print(f"Content extraction error: {str(content_extract_error)}")
            # Clean up blob
            try:
                delete_blob(blob_url)
            except Exception as cleanup_err:
                print(f"Error cleaning up blob: {str(cleanup_err)}")
            raise

        if not extraction_result:
            raise Exception("Failed to extract content")

        # Process document chunks
        pages_content = extraction_result["content"]
        
        chunks_with_pages = chunk_text(pages_content)

        # Query to find existing document versions
        existing_query = """
            SELECT c.version
            FROM c
            WHERE c.file_name = @file_name
              AND c.group_id = @group_id
              AND c.type = "document_metadata"
        """
        params = [
            {"name": "@file_name", "value": filename},
            {"name": "@group_id",  "value": group_id}
        ]
        existing_docs = list(group_documents_container.query_items(
            query=existing_query, parameters=params, enable_cross_partition_query=True
        ))
        version = max(d['version'] for d in existing_docs) + 1 if existing_docs else 1

        # Create document ID and metadata
        document_id = str(uuid4())
        now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        doc_metadata = {
            "id": document_id,
            "group_id": group_id,
            "file_name": filename,
            "uploaded_by_user_id": user_id,
            "upload_date": now_utc,
            "version": version,
            "num_chunks": len(chunks_with_pages),
            "type": "document_metadata",
            "document_source_url": blob_url
        }
        group_documents_container.upsert_item(doc_metadata)

        # Create and store chunk documents
        chunk_docs = []
        search_client_group = CLIENTS['search_client_group']

        for idx, (text_chunk, page_number) in enumerate(chunks_with_pages):
            chunk_id = f"{document_id}_{idx}"

            try:
                embedding = generate_embedding(text_chunk)
            except Exception as e:
                print(f"Error generating embedding for chunk {idx}: {e}")
                embedding = None

            # Ensure page_number is an integer
            try:
                page_num_int = int(page_number)
                if page_num_int < 1:
                    page_num_int = 1
            except (ValueError, TypeError):
                print(f"Warning: Invalid page number, using 1")
                page_num_int = 1

            chunk_docs.append({
                "id": chunk_id,
                "document_id": document_id,
                "chunk_id": str(idx),
                "chunk_text": text_chunk,
                "embedding": embedding,
                "file_name": filename,
                "group_id": group_id,
                "chunk_sequence": idx,
                "page_number": page_num_int,  # Store as integer
                "upload_date": now_utc,
                "version": version,
                "blob_url": blob_url
            })

        # Upload chunks to search index
        try:
            search_client_group.upload_documents(documents=chunk_docs)
        except Exception as search_index_error:
            print(f"Error uploading group doc chunks to search index: {search_index_error}")
            raise

        return document_id
        
    except Exception as e:
        print(f"Error in process_group_document_upload: {str(e)}")
        # Clean up blob if it was uploaded but processing failed
        if 'blob_url' in locals():
            try:
                delete_blob(blob_url)
                print(f"Cleaned up blob after processing error: {blob_url}")
            except Exception as cleanup_err:
                print(f"Error cleaning up blob: {str(cleanup_err)}")
        raise


def delete_group_document(group_id, document_id):
    """
    Deletes *all versions* of the group doc from Cosmos 
    AND all chunk docs from the group search index.
    Also deletes the blob from Azure Blob Storage.
    
    If you only want to delete the *latest version*, use delete_group_document_version instead.
    """
    doc_item = get_group_document(group_id, document_id)
    if not doc_item:
        raise Exception("Document not found or group mismatch")

    doc_versions = get_group_document_versions(group_id, document_id)
    for ver_doc in doc_versions:
        try:
            # If the document has a blob URL, delete the blob
            if ver_doc.get('blob_url'):
                try:
                    delete_blob(ver_doc.get('blob_url'))
                    print(f"Deleted blob: {ver_doc.get('blob_url')}")
                except Exception as blob_err:
                    print(f"Error deleting blob: {str(blob_err)}")
                    
            group_documents_container.delete_item(
                item=ver_doc['id'],
                partition_key=ver_doc['id']
            )
        except exceptions.CosmosResourceNotFoundError:
            pass

    delete_group_document_chunks(document_id)

    return True


def delete_group_document_chunks(document_id):
    """
    Remove from Azure Search index all chunks whose 'document_id' == document_id
    """
    try:
        search_client_group = CLIENTS['search_client_group']
        results = search_client_group.search(
            search_text="*",
            filter=f"document_id eq '{document_id}'",
            select=["id"]
        )
        chunk_ids = [doc["id"] for doc in results]

        if not chunk_ids:
            return

        docs_to_delete = [{"id": cid} for cid in chunk_ids]
        batch = IndexDocumentsBatch()
        batch.add_delete_actions(docs_to_delete)
        search_client_group.index_documents(batch)
    except AzureError as ex:
        print("Error deleting group doc chunks from search:", ex)
        raise


def delete_group_document_version(group_id, document_id, version):
    """
    Deletes exactly one version from Cosmos, plus those chunk docs from search index.
    Also deletes the blob from Azure Blob Storage.
    Does not remove older/newer versions.
    """
    version_doc = get_group_document_version(group_id, document_id, version)
    if not version_doc:
        raise Exception("Document version not found or group mismatch")

    # If the document has a blob URL, delete the blob
    if version_doc.get('blob_url'):
        try:
            delete_blob(version_doc.get('blob_url'))
            print(f"Deleted blob for version {version}: {version_doc.get('blob_url')}")
        except Exception as blob_err:
            print(f"Error deleting blob for version {version}: {str(blob_err)}")

    group_documents_container.delete_item(
        item=version_doc['id'],
        partition_key=version_doc['id']
    )

    delete_group_document_version_chunks(document_id, version)


def delete_group_document_version_chunks(document_id, version):
    """
    Remove all chunk docs from the Azure Search index that match
    document_id eq {document_id} AND version eq {version}.
    """
    try:
        search_client_group = CLIENTS['search_client_group']
        search_results = search_client_group.search(
            search_text="*",
            filter=f"document_id eq '{document_id}' and version eq {version}",
            select=["id"]
        )
        chunk_ids = [doc["id"] for doc in search_results]
        if not chunk_ids:
            return
        batch_docs = [{"id": cid} for cid in chunk_ids]

        batch = IndexDocumentsBatch()
        batch.add_delete_actions(batch_docs)
        search_client_group.index_documents(batch)
    except AzureError as ex:
        print("Error deleting chunk docs for version from group index:", ex)
        raise