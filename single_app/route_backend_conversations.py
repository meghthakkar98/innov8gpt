# route_backend_conversations.py

from config import *
from functions_authentication import *
from functions_settings import *

def register_route_backend_conversations(app):

    @app.route('/api/get_messages', methods=['GET'])
    @login_required
    @user_required
    def api_get_messages():
        conversation_id = request.args.get('conversation_id')
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        if not conversation_id:
            return jsonify({'error': 'No conversation_id provided'}), 400
        try:
            conversation_item = container.read_item(
                item=conversation_id,
                partition_key=conversation_id
            )
            messages = conversation_item.get('messages', [])
            return jsonify({'messages': messages})
        except CosmosResourceNotFoundError:
            return jsonify({'messages': []})
        except Exception:
            return jsonify({'error': 'Conversation not found'}), 404
        
    @app.route('/api/get_conversations', methods=['GET'])
    @login_required
    @user_required
    def get_conversations():
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        query = f"SELECT c.id, c.title, c.last_updated FROM c WHERE c.user_id = '{user_id}' ORDER BY c.last_updated DESC"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        return jsonify({'conversations': items})


    @app.route('/api/create_conversation', methods=['POST'])
    @login_required
    @user_required
    def create_conversation():
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        conversation_id = str(uuid.uuid4())
        conversation_item = {
            'id': conversation_id,
            'user_id': user_id,
            'messages': [],
            'last_updated': datetime.utcnow().isoformat(),
            'title': 'New Conversation'
        }
        container.upsert_item(conversation_item)

        return jsonify({'conversation_id': conversation_id}), 200
    
    @app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
    @login_required
    @user_required
    def delete_conversation(conversation_id):
        """
        Delete a conversation. If archiving is enabled, copy it to archived_conversations first.
        """
        settings = get_settings()
        archiving_enabled = settings.get('enable_conversation_archiving', False)

        try:
            # 1) Fetch the conversation item
            conversation_item = container.read_item(
                item=conversation_id,
                partition_key=conversation_id
            )
        except CosmosResourceNotFoundError:
            return jsonify({"error": f"Conversation {conversation_id} not found."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        if archiving_enabled:
            # 2) Copy conversation to archived_conversations
            #    You can store a timestamp or other metadata if desired
            archived_item = dict(conversation_item)  # shallow copy
            archived_item["archived_at"] = datetime.utcnow().isoformat()
            
            # Make sure 'id' is still unique in the archived container.
            # Usually it's the same ID, which is fine, but you can change if needed.
            archived_conversations_container.upsert_item(archived_item)
            #print(f"Conversation {conversation_id} archived.")
        
        # 3) Permanently remove from main 'conversations' container
        try:
            container.delete_item(
                item=conversation_id,
                partition_key=conversation_id
            )
            #print(f"Conversation {conversation_id} deleted from active container.")
        except Exception as e:
            # If archiving was enabled and we already inserted into archived container,
            # you might choose to handle partial success/failure here.
            return jsonify({"error": str(e)}), 500

        return jsonify({"success": True}), 200