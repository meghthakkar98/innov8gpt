# route_backend_users.py

from config import *
from functions_authentication import *
from functions_settings import *

def register_route_backend_users(app):
    """
    This route will expose GET /api/userSearch?query=<searchTerm> which calls
    Microsoft Graph to find users by displayName, mail, userPrincipalName, etc.
    """

    @app.route("/api/userSearch", methods=["GET"])
    @login_required
    @user_required
    def api_user_search():
        query = request.args.get("query", "").strip()
        if not query:
            return jsonify([]), 200

        token = session.get("access_token")
        if not token:
            return jsonify({"error": "No access token in session"}), 401

        user_endpoint = "https://graph.microsoft.com/v1.0/users"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        filter_str = (
            f"startswith(displayName, '{query}') "
            f"or startswith(mail, '{query}') "
            f"or startswith(userPrincipalName, '{query}')"
        )
        params = {
            "$filter": filter_str,
            "$top": 10,
            "$select": "id,displayName,mail,userPrincipalName"
        }

        response = requests.get(user_endpoint, headers=headers, params=params)
        if response.status_code != 200:
            return jsonify({
                "error": "Graph API error",
                "status": response.status_code,
                "details": response.text
            }), 500

        user_results = response.json().get("value", [])
        results = []
        for user in user_results:
            email = user.get("mail") or user.get("userPrincipalName") or ""
            results.append({
                "id": user.get("id"),
                "displayName": user.get("displayName", "(no name)"),
                "email": email
            })

        return jsonify(results), 200
    
    @app.route('/api/user/settings', methods=['GET', 'POST'])
    @login_required
    @user_required
    def user_settings():
        user_id = get_current_user_id()
        
        if request.method == 'POST':
            active_group_oid = request.form.get('activeGroupOid', '') or request.json.get('activeGroupOid', '')
            
            new_settings = {
                "settings": {
                    "activeGroupOid": active_group_oid
                },
                "lastUpdated": datetime.utcnow().isoformat()
            }
            
            update_user_settings(user_id, new_settings)
            return jsonify({"message": "User settings updated successfully"}), 200

        user_settings_data = get_user_settings(user_id)
        return jsonify(user_settings_data if user_settings_data else {})
    

    @app.route("/api/user/profile", methods=["GET"])
    @login_required
    @user_required
    def get_user_profile():
        user_info = get_current_user_info()
        user_id = user_info["userId"]
        
        # Check if user is admin
        is_admin = False
        if "user" in session:
            user_roles = session["user"].get("roles", [])
            is_admin = "Admin" in user_roles
        
        return jsonify({
            "userId": user_id,
            "displayName": user_info.get("displayName", ""),
            "email": user_info.get("email", ""),
            "isAdmin": is_admin
        })




