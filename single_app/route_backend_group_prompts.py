# route_backend_group_prompts.py

from config import *
from functions_authentication import *
from functions_settings import *

def register_route_backend_group_prompts(app):
    @app.route('/api/group_prompts', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")  # same gating as group docs
    def get_group_prompts():
        user_id = get_current_user_id()
        # find user's active group
        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        if not active_group_id:
            return jsonify({"error": "No active group selected"}), 400

        # ensure user is in that group
        # (re-use your group role logic)
        # ...
        # then fetch prompts
        query = f"SELECT * FROM c WHERE c.group_id = '{active_group_id}' AND c.type='group_prompt'"
        items = list(group_prompts_container.query_items(query=query, enable_cross_partition_query=True))
        return jsonify({"prompts": items}), 200

    @app.route('/api/group_prompts', methods=['POST'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def create_group_prompt():
        user_id = get_current_user_id()
        data = request.get_json()
        name = data.get("name")
        content = data.get("content")
        if not name or not content:
            return jsonify({"error": "Missing 'name' or 'content'"}), 400

        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        if not active_group_id:
            return jsonify({"error": "No active group selected"}), 400

        # check role is "Owner", "Admin", "DocumentManager", or "User" if you want.
        # Example: only let "Owner/Admin/DocumentManager" create if that is your policy
        # ...
        
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        prompt_doc = {
            "id": new_id,
            "group_id": active_group_id,
            "uploaded_by_user_id": user_id,
            "name": name,
            "content": content,
            "type": "group_prompt",
            "created_at": now,
            "updated_at": now
        }
        group_prompts_container.create_item(body=prompt_doc)
        return jsonify(prompt_doc), 200

    @app.route('/api/group_prompts/<prompt_id>', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def get_group_prompt(prompt_id):
        user_id = get_current_user_id()
        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        if not active_group_id:
            return jsonify({"error": "No active group selected"}), 400

        query = f"SELECT * FROM c WHERE c.id = '{prompt_id}' AND c.group_id = '{active_group_id}' AND c.type='group_prompt'"
        items = list(group_prompts_container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            return jsonify({"error": "Group prompt not found"}), 404
        return jsonify(items[0]), 200

    @app.route('/api/group_prompts/<prompt_id>', methods=['PATCH'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def update_group_prompt(prompt_id):
        user_id = get_current_user_id()
        data = request.get_json()
        name = data.get("name")
        content = data.get("content")

        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        if not active_group_id:
            return jsonify({"error": "No active group selected"}), 400

        # check role again if needed
        # ...
        
        query = f"SELECT * FROM c WHERE c.id = '{prompt_id}' AND c.group_id = '{active_group_id}' AND c.type='group_prompt'"
        items = list(group_prompts_container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            return jsonify({"error": "Group prompt not found"}), 404

        doc = items[0]
        if name: doc["name"] = name
        if content: doc["content"] = content
        doc["updated_at"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        group_prompts_container.upsert_item(doc)
        return jsonify(doc), 200

    @app.route('/api/group_prompts/<prompt_id>', methods=['DELETE'])
    @login_required
    @user_required
    @enabled_required("enable_group_workspaces")
    def delete_group_prompt(prompt_id):
        user_id = get_current_user_id()
        user_settings = get_user_settings(user_id)
        active_group_id = user_settings["settings"].get("activeGroupOid")
        if not active_group_id:
            return jsonify({"error": "No active group selected"}), 400

        # check role if needed
        # ...
        
        query = f"SELECT * FROM c WHERE c.id = '{prompt_id}' AND c.group_id = '{active_group_id}' AND c.type='group_prompt'"
        items = list(group_prompts_container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            return jsonify({"error": "Group prompt not found"}), 404
        
        doc = items[0]
        group_prompts_container.delete_item(doc["id"], partition_key=doc["id"])
        return jsonify({"message": "Group prompt deleted"}), 200