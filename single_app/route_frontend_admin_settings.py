# route_frontend_admin_settings.py

from config import *
from functions_documents import *
from functions_authentication import *
from functions_settings import *
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def register_route_frontend_admin_settings(app):
    @app.route('/admin/settings', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_settings():
        settings = get_settings()

        if 'gpt_model' not in settings or not settings['gpt_model']:
            settings['gpt_model'] = {'selected': [], 'all': []}
        if 'embedding_model' not in settings or not settings['embedding_model']:
            settings['embedding_model'] = {'selected': [], 'all': []}
        if 'image_gen_model' not in settings or not settings['image_gen_model']:
            settings['image_gen_model'] = {'selected': [], 'all': []}

        if request.method == 'GET':
            gpt_deployments = []
            embedding_deployments = []
            image_deployments = []
            try:
                gpt_endpoint = settings.get("azure_openai_gpt_endpoint", "").strip()
                gpt_api_version = settings.get("azure_openai_gpt_api_version", "2023-12-01-preview").strip()
                gpt_key = settings.get("azure_openai_gpt_key", "").strip()
                if gpt_endpoint:
                    client_gpt = AzureOpenAI(
                        azure_endpoint=gpt_endpoint.rstrip("/"),
                        api_version=gpt_api_version,
                        api_key=gpt_key
                    )
                    all_deployments = client_gpt.deployments.list().data
                    gpt_deployments = [
                        dep for dep in all_deployments if "gpt" in dep.model.lower()
                    ]
            except Exception as e:
                print(f"Error retrieving GPT deployments: {e}")

            try:
                embed_endpoint = settings.get("azure_openai_embedding_endpoint", "").strip()
                embed_api_version = settings.get("azure_openai_embedding_api_version", "2023-12-01-preview").strip()
                embed_key = settings.get("azure_openai_embedding_key", "").strip()
                if embed_endpoint:
                    client_embeddings = AzureOpenAI(
                        azure_endpoint=embed_endpoint.rstrip("/"),
                        api_version=embed_api_version,
                        api_key=embed_key
                    )
                    all_deployments = client_embeddings.deployments.list().data
                    embedding_deployments = [
                        dep for dep in all_deployments
                        if "embedding" in dep.model.lower() or "ada" in dep.model.lower()
                    ]
            except Exception as e:
                print(f"Error retrieving Embeddings deployments: {e}")

            try:
                if settings.get("enable_image_generation"):
                    image_endpoint = settings.get("azure_openai_image_gen_endpoint", "").strip()
                    image_api_version = settings.get("azure_openai_image_gen_api_version", "2023-12-01-preview").strip()
                    image_key = settings.get("azure_openai_image_gen_key", "").strip()
                    if image_endpoint:
                        client_image = AzureOpenAI(
                            azure_endpoint=image_endpoint.rstrip("/"),
                            api_version=image_api_version,
                            api_key=image_key
                        )
                        all_deployments = client_image.deployments.list().data
                        image_deployments = [
                            dep for dep in all_deployments if "dall-e" in dep.model.lower()
                        ]
            except Exception as e:
                print(f"Error retrieving Image deployments: {e}")

            update_settings(settings)
            return render_template(
                'admin_settings.html',
                settings=settings,
                gpt_deployments=gpt_deployments,
                embedding_deployments=embedding_deployments,
                image_deployments=image_deployments
            )

        if request.method == 'POST':
            app_title = request.form.get('app_title', 'AI Chat Application')
            max_file_size_mb = int(request.form.get('max_file_size_mb', 16))
            conversation_history_limit = int(request.form.get('conversation_history_limit', 10))
            default_system_prompt = request.form.get('default_system_prompt', '')
            enable_conversation_archiving = request.form.get('enable_conversation_archiving') == 'on'
            show_logo = request.form.get('show_logo') == 'on'
            enable_user_workspace = request.form.get('enable_user_workspace') == 'on'
            enable_group_workspaces = request.form.get('enable_group_workspaces') == 'on'
            enable_content_safety = request.form.get('enable_content_safety') == 'on'
            enable_user_feedback = request.form.get('enable_user_feedback') == 'on'
            content_safety_endpoint = request.form.get('content_safety_endpoint', '')
            content_safety_key = request.form.get('content_safety_key', '')
            content_safety_authentication_type = request.form.get('content_safety_authentication_type', 'key')
            azure_ai_search_endpoint = request.form.get('azure_ai_search_endpoint', '')
            azure_ai_search_key = request.form.get('azure_ai_search_key', '')
            azure_ai_search_authentication_type = request.form.get('azure_ai_search_authentication_type', 'key')
            azure_document_intelligence_endpoint = request.form.get('azure_document_intelligence_endpoint', '')
            azure_document_intelligence_key = request.form.get('azure_document_intelligence_key', '')
            azure_document_intelligence_authentication_type = request.form.get('azure_document_intelligence_authentication_type', 'key')

            # Email settings handling - add to the POST request handling
            smtp_server = request.form.get('smtp_server', 'smtp.gmail.com')
            smtp_port = request.form.get('smtp_port', '587')
            smtp_username = request.form.get('smtp_username', 'innov8gpt@gmail.com')
            smtp_password = request.form.get('smtp_password', 'emhfzanfshusuhla')
            smtp_from_email = request.form.get('smtp_from_email', 'innov8gpt@gmail.com')
            app_url = request.form.get('app_url', 'https://innov8gpt-test-app.azurewebsites.net')

            # GPT
            azure_openai_gpt_endpoint = request.form.get('azure_openai_gpt_endpoint', '')
            azure_openai_gpt_api_version = request.form.get('azure_openai_gpt_api_version', '')
            azure_openai_gpt_authentication_type = request.form.get('azure_openai_gpt_authentication_type', 'key')
            azure_openai_gpt_subscription_id = request.form.get('azure_openai_gpt_subscription_id', '')
            azure_openai_gpt_resource_group = request.form.get('azure_openai_gpt_resource_group', '')
            azure_openai_gpt_key = request.form.get('azure_openai_gpt_key', '')

            # Embedding
            azure_openai_embedding_endpoint = request.form.get('azure_openai_embedding_endpoint', '')
            azure_openai_embedding_api_version = request.form.get('azure_openai_embedding_api_version', '')
            azure_openai_embedding_authentication_type = request.form.get('azure_openai_embedding_authentication_type', 'key')
            azure_openai_embedding_subscription_id = request.form.get('azure_openai_embedding_subscription_id', '')
            azure_openai_embedding_resource_group = request.form.get('azure_openai_embedding_resource_group', '')
            azure_openai_embedding_key = request.form.get('azure_openai_embedding_key', '')

            # Image Generation
            enable_image_generation = request.form.get('enable_image_generation') == 'on'
            azure_openai_image_gen_endpoint = request.form.get('azure_openai_image_gen_endpoint', '')
            azure_openai_image_gen_api_version = request.form.get('azure_openai_image_gen_api_version', '')
            azure_openai_image_gen_authentication_type = request.form.get('azure_openai_image_gen_authentication_type', 'key')
            azure_openai_image_gen_subscription_id = request.form.get('azure_openai_image_gen_subscription_id', '')
            azure_openai_image_gen_resource_group = request.form.get('azure_openai_image_gen_resource_group', '')
            azure_openai_image_gen_key = request.form.get('azure_openai_image_gen_key', '')

            enable_web_search = request.form.get('enable_web_search') == 'on'
            bing_search_key = request.form.get('bing_search_key', '')
            landing_page_text = request.form.get('landing_page_text', '')

            # Model JSONs
            gpt_model_json = request.form.get('gpt_model_json', '')
            embedding_model_json = request.form.get('embedding_model_json', '')
            image_gen_model_json = request.form.get('image_gen_model_json', '')

            # APIM toggles/fields
            enable_gpt_apim = request.form.get('enable_gpt_apim') == 'on'
            azure_apim_gpt_endpoint = request.form.get('azure_apim_gpt_endpoint', '')
            azure_apim_gpt_subscription_key = request.form.get('azure_apim_gpt_subscription_key', '')
            azure_apim_gpt_api_version = request.form.get('azure_apim_gpt_api_version', '')
            azure_apim_gpt_deployment = request.form.get('azure_apim_gpt_deployment', '')

            enable_embedding_apim = request.form.get('enable_embedding_apim') == 'on'
            azure_apim_embedding_endpoint = request.form.get('azure_apim_embedding_endpoint', '')
            azure_apim_embedding_subscription_key = request.form.get('azure_apim_embedding_subscription_key', '')
            azure_apim_embedding_api_version = request.form.get('azure_apim_embedding_api_version', '')
            azure_apim_embedding_deployment = request.form.get('azure_apim_embedding_deployment', '')

            enable_image_gen_apim = request.form.get('enable_image_gen_apim') == 'on'
            azure_apim_image_gen_endpoint = request.form.get('azure_apim_image_gen_endpoint', '')
            azure_apim_image_gen_subscription_key = request.form.get('azure_apim_image_gen_subscription_key', '')
            azure_apim_image_gen_api_version = request.form.get('azure_apim_image_gen_api_version', '')
            azure_apim_image_gen_deployment = request.form.get('azure_apim_image_gen_deployment', '')

            enable_content_safety_apim = request.form.get('enable_content_safety_apim') == 'on'
            azure_apim_content_safety_endpoint = request.form.get('azure_apim_content_safety_endpoint', '')
            azure_apim_content_safety_subscription_key = request.form.get('azure_apim_content_safety_subscription_key', '')

            enable_web_search_apim = request.form.get('enable_web_search_apim') == 'on'
            azure_apim_web_search_endpoint = request.form.get('azure_apim_web_search_endpoint', '')
            azure_apim_web_search_subscription_key = request.form.get('azure_apim_web_search_subscription_key', '')

            enable_ai_search_apim = request.form.get('enable_ai_search_apim') == 'on'
            azure_apim_ai_search_endpoint = request.form.get('azure_apim_ai_search_endpoint', '')
            azure_apim_ai_search_subscription_key = request.form.get('azure_apim_ai_search_subscription_key', '')

            enable_document_intelligence_apim = request.form.get('enable_document_intelligence_apim') == 'on'
            azure_apim_document_intelligence_endpoint = request.form.get('azure_apim_document_intelligence_endpoint', '')
            azure_apim_document_intelligence_subscription_key = request.form.get('azure_apim_document_intelligence_subscription_key', '')

            try:
                gpt_model_obj = json.loads(gpt_model_json) if gpt_model_json else {'selected': [], 'all': []}
            except:
                gpt_model_obj = {'selected': [], 'all': []}

            try:
                embedding_model_obj = json.loads(embedding_model_json) if embedding_model_json else {'selected': [], 'all': []}
            except:
                embedding_model_obj = {'selected': [], 'all': []}

            try:
                image_gen_model_obj = json.loads(image_gen_model_json) if image_gen_model_json else {'selected': [], 'all': []}
            except:
                image_gen_model_obj = {'selected': [], 'all': []}

            logo_path_relative = settings.get('logo_path', 'images/logo.svg')

            logo_file = request.files.get('logo_file')
            if logo_file and allowed_file(logo_file.filename, allowed_extensions={'png', 'jpg', 'jpeg'}):
                filename = secure_filename(logo_file.filename)
                logo_path = os.path.join(app.root_path, 'static', 'images', 'custom_logo.png')
                os.makedirs(os.path.dirname(logo_path), exist_ok=True)
                logo_file.save(logo_path)
                logo_path_relative = 'images/custom_logo.png'

            new_settings = {
                'app_title': app_title,
                'max_file_size_mb': max_file_size_mb,
                'conversation_history_limit': conversation_history_limit,
                'default_system_prompt': default_system_prompt,
                'enable_conversation_archiving': enable_conversation_archiving,
                'show_logo': show_logo,
                'logo_path': logo_path_relative,
                'enable_web_search': enable_web_search,
                'bing_search_key': bing_search_key,
                'landing_page_text': landing_page_text,
                'enable_user_workspace': enable_user_workspace,
                'enable_group_workspaces': enable_group_workspaces,
                'azure_ai_search_endpoint': azure_ai_search_endpoint.strip(),
                'azure_ai_search_key': azure_ai_search_key.strip(),
                'azure_ai_search_authentication_type': azure_ai_search_authentication_type,
                'azure_document_intelligence_endpoint': azure_document_intelligence_endpoint.strip(),
                'azure_document_intelligence_key': azure_document_intelligence_key.strip(),
                'azure_document_intelligence_authentication_type': azure_document_intelligence_authentication_type,
                'enable_content_safety': enable_content_safety,
                'enable_user_feedback': enable_user_feedback,
                'content_safety_endpoint': content_safety_endpoint.strip(),
                'content_safety_key': content_safety_key.strip(),
                'content_safety_authentication_type': content_safety_authentication_type,

                # GPT
                'azure_openai_gpt_endpoint': azure_openai_gpt_endpoint,
                'azure_openai_gpt_api_version': azure_openai_gpt_api_version,
                'azure_openai_gpt_authentication_type': azure_openai_gpt_authentication_type,
                'azure_openai_gpt_key': azure_openai_gpt_key,
                'gpt_model': gpt_model_obj,
                'azure_openai_gpt_subscription_id': azure_openai_gpt_subscription_id,
                'azure_openai_gpt_resource_group': azure_openai_gpt_resource_group,

                # Embeddings
                'azure_openai_embedding_endpoint': azure_openai_embedding_endpoint,
                'azure_openai_embedding_api_version': azure_openai_embedding_api_version,
                'azure_openai_embedding_authentication_type': azure_openai_embedding_authentication_type,
                'azure_openai_embedding_key': azure_openai_embedding_key,
                'embedding_model': embedding_model_obj,
                'azure_openai_embedding_subscription_id': azure_openai_embedding_subscription_id,
                'azure_openai_embedding_resource_group': azure_openai_embedding_resource_group,

                # Image Generation
                'enable_image_generation': enable_image_generation,
                'azure_openai_image_gen_endpoint': azure_openai_image_gen_endpoint,
                'azure_openai_image_gen_api_version': azure_openai_image_gen_api_version,
                'azure_openai_image_gen_authentication_type': azure_openai_image_gen_authentication_type,
                'azure_openai_image_gen_key': azure_openai_image_gen_key,
                'image_gen_model': image_gen_model_obj,
                'azure_openai_image_gen_subscription_id': azure_openai_image_gen_subscription_id,
                'azure_openai_image_gen_resource_group': azure_openai_image_gen_resource_group,

                #  APIM toggles/fields for GPT, Embedding, Image Gen
                'enable_gpt_apim': enable_gpt_apim,
                'azure_apim_gpt_endpoint': azure_apim_gpt_endpoint,
                'azure_apim_gpt_subscription_key': azure_apim_gpt_subscription_key,
                'azure_apim_gpt_api_version': azure_apim_gpt_api_version,
                'azure_apim_gpt_deployment': azure_apim_gpt_deployment,

                'enable_embedding_apim': enable_embedding_apim,
                'azure_apim_embedding_endpoint': azure_apim_embedding_endpoint,
                'azure_apim_embedding_subscription_key': azure_apim_embedding_subscription_key,
                'azure_apim_embedding_api_version': azure_apim_embedding_api_version,
                'azure_apim_embedding_deployment': azure_apim_embedding_deployment,

                'enable_image_gen_apim': enable_image_gen_apim,
                'azure_apim_image_gen_endpoint': azure_apim_image_gen_endpoint,
                'azure_apim_image_gen_subscription_key': azure_apim_image_gen_subscription_key,
                'azure_apim_image_gen_api_version': azure_apim_image_gen_api_version,
                'azure_apim_image_gen_deployment': azure_apim_image_gen_deployment,

                # Content Safety
                'enable_content_safety_apim': enable_content_safety_apim,
                'azure_apim_content_safety_endpoint': azure_apim_content_safety_endpoint,
                'azure_apim_content_safety_subscription_key': azure_apim_content_safety_subscription_key,

                # Web Search
                'enable_web_search_apim': enable_web_search_apim,
                'azure_apim_web_search_endpoint': azure_apim_web_search_endpoint,
                'azure_apim_web_search_subscription_key': azure_apim_web_search_subscription_key,

                # Azure AI Search
                'enable_ai_search_apim': enable_ai_search_apim,
                'azure_apim_ai_search_endpoint': azure_apim_ai_search_endpoint,
                'azure_apim_ai_search_subscription_key': azure_apim_ai_search_subscription_key,

                # Document Intelligence
                'enable_document_intelligence_apim': enable_document_intelligence_apim,
                'azure_apim_document_intelligence_endpoint': azure_apim_document_intelligence_endpoint,
                'azure_apim_document_intelligence_subscription_key': azure_apim_document_intelligence_subscription_key,

                # Email settings
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_username': smtp_username,
                'smtp_password': smtp_password,
                'smtp_from_email': smtp_from_email,
                'app_url': app_url
 }

            update_settings(new_settings)
            settings.update(new_settings)
            initialize_clients(settings)

            print("Admin settings updated successfully.")
            return redirect(url_for('admin_settings'))