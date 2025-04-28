# functions_settings.py

from config import *
from functions_authentication import *

def get_settings():
    try:
        settings_item = settings_container.read_item(
            item="app_settings",
            partition_key="app_settings"
        )
        print("Successfully retrieved settings.")
        return settings_item
    except CosmosResourceNotFoundError:
        default_settings = {
            'id': 'app_settings',

            # General Settings
            'app_title': 'Simple Chat',
            'landing_page_text': 'You can add text here and it supports Markdown. You agree to our [acceptable user policy](acceptable_use_policy.html) by using this service.',
            'show_logo': False,
            'logo_path': 'images/logo.svg',

            # GPT Settings
            'enable_gpt_apim': False,
            'azure_openai_gpt_endpoint': '',
            'azure_openai_gpt_api_version': '2024-05-01-preview',
            'azure_openai_gpt_authentication_type': 'key',
            'azure_openai_gpt_subscription_id': '',
            'azure_openai_gpt_resource_group': '',
            'azure_openai_gpt_key': '',
            'gpt_model': {
                "selected": [],
                "all": []
            },
            'azure_apim_gpt_endpoint': '',
            'azure_apim_gpt_subscription_key': '',
            'azure_apim_gpt_deployment': '',
            'azure_apim_gpt_api_version': '',

            # Embeddings Settings
            'enable_embedding_apim': False,
            'azure_openai_embedding_endpoint': '',
            'azure_openai_embedding_api_version': '2024-05-01-preview',
            'azure_openai_embedding_authentication_type': 'key',
            'azure_openai_embedding_subscription_id': '',
            'azure_openai_embedding_resource_group': '',
            'azure_openai_embedding_key': '',
            'embedding_model': {
                "selected": [],
                "all": []
            },
            'azure_apim_embedding_endpoint': '',
            'azure_apim_embedding_subscription_key': '',
            'azure_apim_embedding_deployment': '',
            'azure_apim_embedding_api_version': '',

            # Image Generation Settings
            'enable_image_generation': False,
            'enable_image_gen_apim': False,
            'azure_openai_image_gen_endpoint': '',
            'azure_openai_image_gen_api_version': '2024-05-01-preview',
            'azure_openai_image_gen_authentication_type': 'key',
            'azure_openai_image_gen_subscription_id': '',
            'azure_openai_image_gen_resource_group': '',
            'azure_openai_image_gen_key': '',
            'image_gen_model': {
                "selected": [],
                "all": []
            },
            'azure_apim_image_gen_endpoint': '',
            'azure_apim_image_gen_subscription_key': '',
            'azure_apim_image_gen_deployment': '',
            'azure_apim_image_gen_api_version': '',

            # Workspaces
            'enable_user_workspace': True,
            'enable_group_workspaces': True,

            # Safety (Content Safety) Settings
            'enable_content_safety': False,
            'content_safety_endpoint': '',
            'content_safety_key': '',
            'content_safety_authentication_type': 'key',
            'enable_content_safety_apim': False,
            'azure_apim_content_safety_endpoint': '',
            'azure_apim_content_safety_subscription_key': '',

            # User Feedback / Conversation Archiving
            'enable_user_feedback': True,
            'enable_conversation_archiving': False,

            # Search and Extract
            'enable_web_search': False,
            'bing_search_key': '',
            'enable_web_search_apim': False,
            'azure_apim_web_search_endpoint': '',
            'azure_apim_web_search_subscription_key': '',

            'azure_ai_search_endpoint': '',
            'azure_ai_search_key': '',
            'azure_ai_search_authentication_type': 'key',
            'enable_ai_search_apim': False,
            'azure_apim_ai_search_endpoint': '',
            'azure_apim_ai_search_subscription_key': '',

            'azure_document_intelligence_endpoint': '',
            'azure_document_intelligence_key': '',
            'azure_document_intelligence_authentication_type': 'key',
            'enable_document_intelligence_apim': False,
            'azure_apim_document_intelligence_endpoint': '',
            'azure_apim_document_intelligence_subscription_key': '',

            # Other Settings
            'max_file_size_mb': 150,
            'conversation_history_limit': 10,
            'default_system_prompt': ''
        }

        settings_container.create_item(body=default_settings)
        print("Default settings created and returned.")
        return default_settings
    except Exception as e:
        print(f"Error retrieving settings: {str(e)}")
        return None


def update_settings(new_settings):
    try:
        settings_item = get_settings()
        settings_item.update(new_settings)
        settings_container.upsert_item(settings_item)
        print("Settings updated successfully.")
        return True
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        return False

def encrypt_key(key):
    cipher_suite = Fernet(app.config['SECRET_KEY'])
    encrypted_key = cipher_suite.encrypt(key.encode())
    return encrypted_key.decode()

def decrypt_key(encrypted_key):
    cipher_suite = Fernet(app.config['SECRET_KEY'])
    try:
        encrypted_key_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted_key = cipher_suite.decrypt(encrypted_key_bytes).decode()
        return decrypted_key
    except InvalidToken:
        print("Decryption failed: Invalid token")
        return None

def get_user_settings(user_id):
    doc_id = str(user_id)
    try:
        return user_settings_container.read_item(item=doc_id, partition_key=doc_id)
    except exceptions.CosmosResourceNotFoundError:
        return {
            "id": user_id,
            "settings": {
                "activeGroupOid": ""
            },
            "lastUpdated": None
        }
    
def update_user_settings(user_id, new_settings):
    doc_id = str(user_id)
    try:
        doc = user_settings_container.read_item(item=doc_id, partition_key=doc_id)
        doc.update(new_settings)
        user_settings_container.upsert_item(doc)
    except exceptions.CosmosResourceNotFoundError:
        doc = {
            "id": doc_id,
            **new_settings
        }
        user_settings_container.upsert_item(doc)

def enabled_required(setting_key):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            settings = get_settings()
            if not settings.get(setting_key, False):
                setting_key_as_statement = setting_key.replace("_", " ").title()
                return jsonify({"error": f"{setting_key_as_statement} is disabled."}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator

import re

def sanitize_settings_for_user(full_settings: dict) -> dict:
    keys_to_exclude = {
        'azure_document_intelligence_key',
        'azure_ai_search_key',
        'azure_openai_gpt_key',
        'azure_openai_embedding_key',
        'azure_openai_image_gen_key',
        'bing_search_key',
        'azure_apim_gpt_subscription_key',
        'azure_apim_embedding_subscription_key',
        'azure_apim_image_gen_subscription_key',
        # any others that are secrets
    }
    return {k:v for k,v in full_settings.items() if k not in keys_to_exclude}