# functions_search.py

from config import *
from functions_content import *
from functions_documents import *
from functions_content import generate_embedding
from functions_content import *


# Update this function in functions_search.py

# Update this function in functions_search.py

def hybrid_search(query, user_id, document_id=None, top_n=3, doc_scope="all", active_group_id=None, doc_group_id=None, document_group_id=None):
    """
    Hybrid search that queries the user doc index or the group doc index
    depending on doc type. Now also includes default documents.
    
    Parameters:
    - doc_group_id: Optional parameter for the specific group ID a document belongs to
    - document_group_id: Alternative name for doc_group_id (for API compatibility)
    """
    try:
        # Handle parameter name compatibility
        if document_group_id is not None and doc_group_id is None:
            doc_group_id = document_group_id
            
        print(f"Executing hybrid search: query='{query}', doc_scope={doc_scope}")
        if document_id:
            print(f"Searching for document_id: {document_id}")
            if doc_group_id:
                print(f"Document belongs to group_id: {doc_group_id}")
                
        query_embedding = generate_embedding(query)
        if query_embedding is None:
            print("Warning: Failed to generate embedding for query")
            return []
        
        search_client_user = CLIENTS.get('search_client_user')
        search_client_group = CLIENTS.get('search_client_group')

        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_n,
            fields="embedding"
        )

        # Continue with the rest of the function as before
        # Ensure page_number is included in select fields for all searches
        user_select_fields = ["id", "chunk_text", "chunk_id", "file_name", "user_id", "version", 
                            "chunk_sequence", "page_number", "upload_date", "storage_url", "is_default"]
        group_select_fields = ["id", "chunk_text", "chunk_id", "file_name", "group_id", "version", 
                            "chunk_sequence", "page_number", "upload_date", "blob_url"]
        
        results = []
        
        if doc_scope == "all" or doc_scope == "personal":
            # Filter for specific document ID if provided
            doc_filter = ""
            if document_id:
                doc_filter = f" and document_id eq '{document_id}'"
            
            # First search for user's documents
            if doc_scope != "default_only":
                # Only search personal docs if we're not specifically looking for a group document
                if not (document_id and doc_group_id):
                    user_filter = f"user_id eq '{user_id}'{doc_filter}"
                    user_results = search_client_user.search(
                        search_text=query,
                        vector_queries=[vector_query],
                        filter=user_filter,
                        select=user_select_fields
                    )
                    user_results_final = extract_search_results(user_results, top_n)
                    results.extend(user_results_final)
            
            # Then search for default documents (they're also in user search index)
            # Only search default docs if we're not specifically looking for a group document
            if not (document_id and doc_group_id):
                default_filter = f"is_default eq true{doc_filter}"
                default_results = search_client_user.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=default_filter,
                    select=user_select_fields
                )
                default_results_final = extract_search_results(default_results, top_n)
                results.extend(default_results_final)
        
        if doc_scope == "all" or doc_scope == "group":
            # If we have a specific document and its group ID, search in that group
            if document_id and doc_group_id:
                group_filter = f"group_id eq '{doc_group_id}' and document_id eq '{document_id}'"
                print(f"Searching with filter: {group_filter}")
                
                group_results = search_client_group.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=group_filter,
                    select=group_select_fields
                )
                group_results_final = extract_search_results(group_results, top_n)
                results.extend(group_results_final)
                
            # Otherwise, search in the active group if available
            elif active_group_id:
                group_filter = f"group_id eq '{active_group_id}'"
                if document_id:
                    group_filter += f" and document_id eq '{document_id}'"
                    
                group_results = search_client_group.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=group_filter,
                    select=group_select_fields
                )
                group_results_final = extract_search_results(group_results, top_n)
                results.extend(group_results_final)
        
        # Sort combined results by relevance score
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Limit to top_n results overall
        results = results[:top_n]
        
        # Log the search results with page numbers
        print(f"Search returned {len(results) if results else 0} results")
        if results:
            for i, r in enumerate(results):
                page = r.get('page_number')
                page_info = f"page {page}" if page is not None else "no page"
                print(f"  Result {i+1}: {r['file_name']}, {page_info}, score={r.get('score')}")
        
        return results
    except Exception as e:
        print(f"Error in hybrid_search: {str(e)}")
        return []  # Return empty results instead of crashing

def extract_search_results(paged_results, top_n):
    """
    Extract relevant fields from search results into a serializable format.
    Ensures page_number is properly included in the results.
    """
    extracted = []
    for i, r in enumerate(paged_results):
        if i >= top_n:
            break
            
        # Build the core result dict with all standard fields
        result_dict = {
            "id": r["id"],
            "chunk_text": r["chunk_text"],
            "chunk_id": r["chunk_id"],
            "file_name": r["file_name"],
            "version": r["version"],
            "chunk_sequence": r["chunk_sequence"],
            "upload_date": r["upload_date"],
            "score": r["@search.score"]
        }
        
        # Always include page_number if available - this is critical
        if "page_number" in r:
            # Try to convert to int if possible, but keep original value if that fails
            try:
                result_dict["page_number"] = int(r["page_number"])
            except (ValueError, TypeError):
                result_dict["page_number"] = r["page_number"]
        
        # Add group_id or user_id based on availability
        if "group_id" in r:
            result_dict["group_id"] = r["group_id"]
        if "user_id" in r:
            result_dict["user_id"] = r["user_id"]
            
        # Add storage URLs
        if "storage_url" in r:
            result_dict["storage_url"] = r["storage_url"]
        if "blob_url" in r:
            result_dict["blob_url"] = r["blob_url"]
            
        extracted.append(result_dict)
    
    return extracted