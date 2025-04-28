# route_frontend_chats.py

from config import *
from functions_authentication import *
from functions_content import *
from functions_settings import *

def register_route_frontend_chats(app):
    @app.route('/chats', methods=['GET'])
    @login_required
    @user_required
    def chats():
        user_id = get_current_user_id()
        settings = get_settings()
        user_settings = get_user_settings(user_id)
        public_settings = sanitize_settings_for_user(settings)
        enable_user_feedback = public_settings.get("enable_user_feedback", False)
        active_group_id = user_settings["settings"].get("activeGroupOid", "")
        if not user_id:
            return redirect(url_for('login'))
        return render_template('chats.html', settings=public_settings, enable_user_feedback=enable_user_feedback, active_group_id=active_group_id)
    
    @app.route('/upload', methods=['POST'])
    @login_required
    @user_required
    def upload_file():
        settings = get_settings()
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        conversation_id = request.form.get('conversation_id')

        if not file.filename:
            return jsonify({'error': 'No selected file'}), 400

        if not conversation_id or conversation_id.strip() == '':
            conversation_id = str(uuid.uuid4())
            conversation_item = {
                'id': conversation_id,
                'user_id': user_id,
                'messages': [],
                'last_updated': datetime.utcnow().isoformat()
            }
        else:
            try:
                conversation_item = container.read_item(
                    item=conversation_id,
                    partition_key=conversation_id
                )
            except Exception:
                conversation_id = str(uuid.uuid4())
                conversation_item = {
                    'id': conversation_id,
                    'user_id': user_id,
                    'messages': [],
                    'last_updated': datetime.utcnow().isoformat()
                }
        
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        max_file_size_bytes = settings.get('max_file_size_mb', 16) * 1024 * 1024
        if file_length > max_file_size_bytes:
            return jsonify({'error': 'File size exceeds maximum allowed size'}), 400
        file.seek(0)

        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file.save(tmp_file.name)
            temp_file_path = tmp_file.name

        extracted_content  = ''
        is_table = False 

        try:
            if file_ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.html', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heif']:
                extracted_content  = extract_content_with_azure_di(temp_file_path)
            elif file_ext == '.txt':
                extracted_content  = extract_text_file(temp_file_path)
            elif file_ext == '.md':
                extracted_content  = extract_markdown_file(temp_file_path)
            elif file_ext == '.json':
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    parsed_json = json.load(f)
                    extracted_content  = json.dumps(parsed_json, indent=2)
            elif file_ext in ['.csv', '.xls', '.xlsx']:
                extracted_content = extract_table_file(temp_file_path, file_ext)
                is_table = True
            else:
                return jsonify({'error': 'Unsupported file type'}), 400

        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        finally:
            os.remove(temp_file_path)

        try:
            file_message = {
                'role': 'file',
                'filename': filename,
                'file_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'file_content': extracted_content,
                'is_table': is_table,
                'model_deployment_name': None
            }

            conversation_item['messages'].append(file_message)
            conversation_item['last_updated'] = datetime.utcnow().isoformat()
            container.upsert_item(conversation_item)

        except Exception as e:
            return jsonify({'error': f'Error adding file to conversation: {str(e)}'}), 500

        response_data = {
            'message': 'File added to the conversation successfully',
            'conversation_id': conversation_id
        }

        return jsonify(response_data), 200