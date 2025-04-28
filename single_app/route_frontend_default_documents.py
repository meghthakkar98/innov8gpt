# route_frontend_default_documents.py

from config import *
from functions_authentication import *

def register_route_frontend_default_documents(app):
    @app.route('/admin/default_documents', methods=['GET'])
    @login_required
    @admin_required
    def admin_default_documents():
        """Admin interface for managing default documents."""
        return render_template('admin_default_documents.html')