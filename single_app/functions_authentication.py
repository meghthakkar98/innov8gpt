# functions_authentication.py

from config import *

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            #print("User not logged in. Redirecting to login page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user', {})
        # If 'roles' is not in user or 'User' is not part of role or 'Admin' is not part of role, block access
        if 'roles' not in user or ('User' not in user['roles'] and 'Admin' not in user['roles']):
            return "Unauthorized", 403
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user', {})
        # If 'roles' is not in user or 'Admin' is not part of roles, block access
        if 'roles' not in user or 'Admin' not in user['roles']:
            return jsonify({"error": "Only administrators can perform this action"}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    user = session.get('user')
    if user:
        return user.get('oid')
    return None

def get_current_user_info():
    user = session.get("user")
    if not user:
        return None
    return {
        "userId": user.get("oid"), 
        "email": user.get("preferred_username"),
        "displayName": user.get("name")
    }
