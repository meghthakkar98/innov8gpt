# route_backend_prompts.py

from config import *
from functions_authentication import *
from functions_settings import *

def register_route_backend_prompts(app):
    @app.route('/api/prompts', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def get_prompts():
        user_id = get_current_user_id()
        query = f"SELECT * FROM c WHERE c.user_id = '{user_id}' AND c.type = 'user_prompt'"
        items = list(prompts_container.query_items(query=query, enable_cross_partition_query=True))
        return jsonify({"prompts": items}), 200

    @app.route('/api/prompts', methods=['POST'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def create_prompt():
        user_id = get_current_user_id()
        data = request.get_json()
        name = data.get("name")
        content = data.get("content")

        if not name or not content:
            return jsonify({"error": "Missing 'name' or 'content'"}), 400

        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        prompt_doc = {
            "id": new_id,
            "user_id": user_id,
            "name": name,
            "content": content,
            "type": "user_prompt",
            "created_at": now,
            "updated_at": now
        }

        prompts_container.create_item(body=prompt_doc)
        return jsonify(prompt_doc), 200

    @app.route('/api/prompts/<prompt_id>', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def get_prompt(prompt_id):
        user_id = get_current_user_id()
        # read by direct ID read if your partition key matches, or do a query
        query = f"SELECT * FROM c WHERE c.id = '{prompt_id}' AND c.user_id = '{user_id}' AND c.type='user_prompt'"
        items = list(prompts_container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            return jsonify({"error": "Prompt not found"}), 404
        return jsonify(items[0]), 200

    @app.route('/api/prompts/<prompt_id>', methods=['PATCH'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def update_prompt(prompt_id):
        user_id = get_current_user_id()
        data = request.get_json()
        name = data.get("name")
        content = data.get("content")

        # find existing doc
        query = f"SELECT * FROM c WHERE c.id = '{prompt_id}' AND c.user_id = '{user_id}' AND c.type='user_prompt'"
        items = list(prompts_container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            return jsonify({"error": "Prompt not found"}), 404

        doc = items[0]
        doc["name"] = name or doc["name"]
        doc["content"] = content or doc["content"]
        doc["updated_at"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        prompts_container.upsert_item(doc)
        return jsonify(doc), 200

    @app.route('/api/prompts/<prompt_id>', methods=['DELETE'])
    @login_required
    @user_required
    @enabled_required("enable_user_workspace")
    def delete_prompt(prompt_id):
        user_id = get_current_user_id()
        # same approach, find the doc, then delete by doc['id'] and partition key if needed
        query = f"SELECT * FROM c WHERE c.id = '{prompt_id}' AND c.user_id = '{user_id}' AND c.type='user_prompt'"
        items = list(prompts_container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            return jsonify({"error": "Prompt not found"}), 404
        
        doc = items[0]
        prompts_container.delete_item(item=doc["id"], partition_key=doc["id"])
        return jsonify({"message": "Prompt deleted"}), 200