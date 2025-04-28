# route_backend_group_documents.py:

from config import *
from functions_authentication import *
from functions_settings import *
from functions_group import *
from functions_group_documents import *
from functions_blob_storage import download_from_blob_storage

def register_route_backend_group_documents(app):
    """
    Provides backend routes for group-level document management:
    - GET /api/group_documents      (list)
    - POST /api/group_documents/upload
    - DELETE /api/group_documents/<doc_id>
    - GET /api/group_documents/<doc_id>/download
    """

    @app.route('/api/group_documents', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def api_get_group_documents():
        """
        Return the list of documents for the user's *active* group.
        """
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
    
        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")

        if not active_group_id:
            return jsonify({'error': 'No active group selected'}), 400

        group_doc = find_group_by_id(active_group_id)
        if not group_doc:
            return jsonify({'error': 'Active group not found'}), 404

        role = get_user_role_in_group(group_doc, user_id)
        if not role:
            return jsonify({'error': 'You are not a member of the active group'}), 403

        try:
            docs = get_group_documents(active_group_id)
            return jsonify({'documents': docs}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


    @app.route('/api/group_documents/upload', methods=['POST'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def api_upload_group_document():
        """
        Upload a new document into the active group's collection, if user role
        is Owner/Admin/Document Manager.
        """
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        if not active_group_id:
            return jsonify({'error': 'No active group selected'}), 400

        group_doc = find_group_by_id(active_group_id)
        if not group_doc:
            return jsonify({'error': 'Active group not found'}), 404

        role = get_user_role_in_group(group_doc, user_id)
        if role not in ["Owner", "Admin", "DocumentManager"]:
            return jsonify({'error': 'You do not have permission to upload documents'}), 403

        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No selected file'}), 400

        try:
            document_id = process_group_document_upload(file, active_group_id, user_id)
            return jsonify({'message': 'Document uploaded successfully', 'document_id': document_id}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/group_documents/<doc_id>/download', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def api_download_group_document(doc_id):
        """Download the original document from Blob Storage"""
        user_id = get_current_user_id()
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
            
        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        
        if not active_group_id:
            return jsonify({'error': 'No active group selected'}), 400
            
        group_doc = find_group_by_id(active_group_id)
        if not group_doc:
            return jsonify({'error': 'Active group not found'}), 404
            
        role = get_user_role_in_group(group_doc, user_id)
        if not role:
            return jsonify({'error': 'You are not a member of the active group'}), 403
            
        try:
            # Get the document from Cosmos DB
            document = get_group_document(active_group_id, doc_id)
            if not document or not document.get('blob_url'):
                return jsonify({'error': 'Document not found or no blob URL available'}), 404
                
            blob_url = document.get('blob_url')
            file_name = document.get('file_name')
            
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
            print(f"Error downloading group document: {str(e)}")
            return jsonify({'error': f'Error downloading document: {str(e)}'}), 500


    @app.route('/api/group_documents/<doc_id>', methods=['DELETE'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def api_delete_group_document(doc_id):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        group_id = request.args.get('group_id')
        if not group_id:
            return jsonify({'error': 'No group_id provided'}), 400

        group_doc = find_group_by_id(group_id)
        if not group_doc:
            return jsonify({'error': 'Group not found'}), 404

        role = get_user_role_in_group(group_doc, user_id)
        if role not in ["Owner", "Admin", "DocumentManager"]:
            return jsonify({'error': 'You do not have permission to delete...'}), 403

        try:
            delete_group_document(group_id, doc_id)
            return jsonify({'message': 'Document deleted successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/all_group_documents', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def api_get_all_group_documents():
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        try:
            print(f"Getting documents from ALL groups for user: {user_id}")
            
            # First, get all groups the user is a member of
            # Update the query to fetch all needed fields
            all_groups_query = """
            SELECT c.id, c.name, c.users, c.owner
            FROM c
            WHERE c.type = 'group' OR NOT IS_DEFINED(c.type)
            """
            
            all_groups = list(groups_container.query_items(
                query=all_groups_query,
                enable_cross_partition_query=True
            ))
            
            # Now determine which groups the user is a member of using proper field names
            user_group_ids = []
            for group in all_groups:
                group_id = group.get('id')
                group_name = group.get('name', 'Unknown Group')
                
                # Check if user is owner
                owner = group.get('owner', {})
                if owner and owner.get('id') == user_id:
                    user_group_ids.append({
                        'id': group_id,
                        'name': group_name
                    })
                    print(f"User is owner of group: {group_name} ({group_id})")
                    continue
                
                # Check users array instead of members
                users = group.get('users', [])
                for user in users:
                    if user.get('userId') == user_id:  # Using userId not user_id
                        user_group_ids.append({
                            'id': group_id,
                            'name': group_name
                        })
                        print(f"User is member of group: {group_name} ({group_id})")
                        break
            
            print(f"User belongs to {len(user_group_ids)} groups")
            
            # Remove hardcoded groups fallback - only show groups user is actually a member of
            # (If you need to keep this fallback for testing, you can uncomment it)
            """
            if len(user_group_ids) < 1:
                print("No groups found. Looking for default groups...")
                hardcoded_groups = ["marketing", "Manufacturing Department", "new"]
                for group in all_groups:
                    if group.get('name') in hardcoded_groups:
                        group_id = group.get('id')
                        group_name = group.get('name')
                        user_group_ids.append({
                            'id': group_id,
                            'name': group_name
                        })
                        print(f"Adding default group: {group_name} ({group_id})")
            """
            
            # Get documents for each group using the functions_group_documents.py utility
            all_docs = []
            
            for group in user_group_ids:
                group_id = group['id']
                group_name = group['name']
                
                try:
                    print(f"Getting documents for group {group_name} ({group_id})")
                    
                    # Use the get_group_documents() function which properly handles
                    # version filtering and is consistent with what's shown in the UI
                    docs = get_group_documents(group_id)
                    
                    # Add group name to each document
                    for doc in docs:
                        doc['group_name'] = group_name
                    
                    print(f"Found {len(docs)} documents in group {group_name}")
                    all_docs.extend(docs)
                except Exception as e:
                    print(f"Error getting documents for group {group_id}: {e}")
            
            # Return user groups and documents
            user_groups_info = [{'id': g['id'], 'name': g['name']} for g in user_group_ids]
            
            print(f"Total documents from all user's groups: {len(all_docs)}")
            
            return jsonify({
                'documents': all_docs,
                'user_groups': user_groups_info
            }), 200
            
        except Exception as e:
            print(f"Error in api_get_all_group_documents: {e}")
            traceback.print_exc()
            return jsonify({
                'error': str(e)
            }), 500