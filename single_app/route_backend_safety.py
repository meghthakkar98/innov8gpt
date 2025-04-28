# route_backend_safety.py

from config import *
from functions_authentication import *
from functions_settings import *

def register_route_backend_safety(app):
    @app.route('/api/safety/logs', methods=['GET'])
    @login_required
    @admin_required
    @enabled_required("enable_content_safety")
    def get_safety_logs():
        """
        Returns all safety logs.
        """        
        query = "SELECT * FROM c"
        items = list(safety_container.query_items(query=query, enable_cross_partition_query=True))
        return jsonify({"logs": items}), 200

    @app.route('/api/safety/logs/<string:log_id>', methods=['PATCH'])
    @login_required
    @admin_required
    @enabled_required("enable_content_safety")
    def update_safety_log(log_id):
        """
        Updates status, action, and notes on a safety log.
        Also sets timestamps (created_at if missing, and last_updated).
        """
        data = request.json
        status = data.get("status")
        action = data.get("action")
        notes = data.get("notes")
        
        try:
            item = safety_container.read_item(item=log_id, partition_key=log_id)

            if not item.get("created_at"):
                item["created_at"] = datetime.utcnow().isoformat()

            if status:
                item["status"] = status
            if action:
                item["action"] = action

            if notes is not None:
                item["notes"] = notes

            item["last_updated"] = datetime.utcnow().isoformat()

            safety_container.upsert_item(item)

            return jsonify({"message": "Safety log updated successfully."}), 200
        except exceptions.CosmosHttpResponseError as e:
            return jsonify({"error": str(e)}), 404
        
    @app.route('/api/safety/logs/my', methods=['GET'])
    @login_required
    @user_required
    @enabled_required("enable_content_safety")
    def get_my_safety_logs():
        """
        Returns only the current user's safety logs.
        """
        user_id = None
        if "user" in session:
            user_id = session["user"].get("oid") or session["user"].get("sub")
        if not user_id:
            return jsonify({"error": "No user ID found in session"}), 403
        
        query = f"SELECT * FROM c WHERE c.user_id = '{user_id}'"
        items = list(safety_container.query_items(query=query, enable_cross_partition_query=True))

        return jsonify({"logs": items}), 200

    @app.route('/api/safety/logs/my/<string:log_id>', methods=['PATCH'])
    @login_required
    @user_required
    @enabled_required("enable_content_safety")
    def update_my_safety_log(log_id):
        """
        Allows the user to update only their own safety log, 
        specifically the user_notes field (separate from admin notes).
        """
        data = request.json
        user_notes = data.get("user_notes")

        user_id = None
        if "user" in session:
            user_id = session["user"].get("oid") or session["user"].get("sub")
        if not user_id:
            return jsonify({"error": "No user ID found in session"}), 403

        try:
            item = safety_container.read_item(item=log_id, partition_key=log_id)

            if item.get("user_id") != user_id:
                return jsonify({"error": "You do not have permission to update this record."}), 403

            if not item.get("created_at"):
                item["created_at"] = datetime.utcnow().isoformat()

            if user_notes is not None:
                item["user_notes"] = user_notes

            item["last_updated"] = datetime.utcnow().isoformat()
            safety_container.upsert_item(item)

            return jsonify({"message": "Safety log updated successfully."}), 200
        except exceptions.CosmosHttpResponseError as e:
            return jsonify({"error": str(e)}), 404