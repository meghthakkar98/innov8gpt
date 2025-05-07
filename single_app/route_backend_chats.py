# route_backend_chats.py

from config import *
from functions_authentication import *
from functions_search import *
from functions_bing_search import *
from functions_settings import *

def register_route_backend_chats(app):
    @app.route('/api/chat', methods=['POST'])
    @login_required
    @user_required
    def chat_api():
        try:
            settings = get_settings()
            data = request.get_json()
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401

            print(f"Received chat request from user {user_id} with data: {data}")  # Log the request

            # Extract from request
            user_message = data.get('message', '')
            conversation_id = data.get('conversation_id')
            use_open_ai = data.get('use_open_ai', True)  # New parameter for Open AI knowledge
            hybrid_search_enabled = data.get('hybrid_search')
            selected_document_id = data.get('selected_document_id')
            document_group_id = data.get('document_group_id') 
            bing_search_enabled = data.get('bing_search')
            image_gen_enabled = data.get('image_generation')
            streaming_enabled = data.get('streaming', True)
            document_scope = data.get('doc_scope')
            active_group_id = data.get('active_group_id')

            # Convert toggles from string -> bool if needed
            if isinstance(use_open_ai, str):
                use_open_ai = use_open_ai.lower() == 'true'
            if isinstance(hybrid_search_enabled, str):
                hybrid_search_enabled = hybrid_search_enabled.lower() == 'true'
            if isinstance(bing_search_enabled, str):
                bing_search_enabled = bing_search_enabled.lower() == 'true'
            if isinstance(streaming_enabled, str):
                streaming_enabled = streaming_enabled.lower() == 'true'

            # GPT & Image generation APIM or direct
            enable_gpt_apim = settings.get('enable_gpt_apim', False)
            enable_image_gen_apim = settings.get('enable_image_gen_apim', False)

            # ---------------------------------------------------------------------
            # 1) Load or create conversation
            # ---------------------------------------------------------------------
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
                conversation_item = {
                    'id': conversation_id,
                    'user_id': user_id,
                    'messages': [],
                    'last_updated': datetime.utcnow().isoformat(),
                    'title': 'New Conversation'
                }
            else:
                try:
                    conversation_item = container.read_item(
                        item=conversation_id,
                        partition_key=conversation_id
                    )
                except CosmosResourceNotFoundError:
                    conversation_id = str(uuid.uuid4())
                    conversation_item = {
                        'id': conversation_id,
                        'user_id': user_id,
                        'messages': [],
                        'last_updated': datetime.utcnow().isoformat(),
                        'title': 'New Conversation'
                    }


            # ---------------------------------------------------------------------
            # 2) Append the user message to conversation immediately
            # ---------------------------------------------------------------------
            user_message_id = f"{conversation_id}_user_{int(time.time())}_{random.randint(1000,9999)}"
            conversation_item['messages'].append({
                'role': 'user',
                'content': user_message,
                'model_deployment_name': None,
                'message_id': user_message_id
            })

            # Set conversation title if it's still the default
            if conversation_item.get('title', 'New Conversation') == 'New Conversation':
                new_title = (user_message[:30] + '...') if len(user_message) > 30 else user_message
                conversation_item['title'] = new_title

            # If first message, optionally add default system prompt
            if len(conversation_item['messages']) == 1 and settings.get('default_system_prompt'):
                conversation_item['messages'].insert(0, {
                    'role': 'system',
                    'content': settings.get('default_system_prompt'),
                    'model_deployment_name': None
                })

            conversation_item['last_updated'] = datetime.utcnow().isoformat()
            container.upsert_item(body=conversation_item)

            # ---------------------------------------------------------------------
            # 3) Check Content Safety (but DO NOT return 403).
            #    If blocked, add a "safety" role message & skip GPT.
            # ---------------------------------------------------------------------
            blocked = False
            block_reasons = []
            triggered_categories = []
            blocklist_matches = []

            if settings.get('enable_content_safety') and "content_safety_client" in CLIENTS:
                try:
                    content_safety_client = CLIENTS["content_safety_client"]
                    request_obj = AnalyzeTextOptions(text=user_message)
                    cs_response = content_safety_client.analyze_text(request_obj)

                    max_severity = 0
                    for cat_result in cs_response.categories_analysis:
                        triggered_categories.append({
                            "category": cat_result.category,
                            "severity": cat_result.severity
                        })
                        if cat_result.severity > max_severity:
                            max_severity = cat_result.severity

                    if cs_response.blocklists_match:
                        for match in cs_response.blocklists_match:
                            blocklist_matches.append({
                                "blocklistName": match.blocklist_name,
                                "blocklistItemId": match.blocklist_item_id,
                                "blocklistItemText": match.blocklist_item_text
                            })

                    # Example: If severity >=4 or blocklist, we call it "blocked"
                    if max_severity >= 4:
                        blocked = True
                        block_reasons.append("Max severity >= 4")
                    if len(blocklist_matches) > 0:
                        blocked = True
                        block_reasons.append("Blocklist match")

                    if blocked:
                        # Upsert to safety container
                        safety_item = {
                            'id': str(uuid.uuid4()),
                            'user_id': user_id,
                            'conversation_id': conversation_id,
                            'message': user_message,
                            'triggered_categories': triggered_categories,
                            'blocklist_matches': blocklist_matches,
                            'timestamp': datetime.utcnow().isoformat(),
                            'reason': "; ".join(block_reasons)
                        }
                        safety_container.upsert_item(safety_item)

                        # Instead of 403, we'll add a "safety" message
                        blocked_msg_content = (
                            "Your message was blocked by Content Safety.\n\n"
                            f"**Reason**: {', '.join(block_reasons)}\n"
                            "Triggered categories:\n"
                        )
                        for cat in triggered_categories:
                            blocked_msg_content += (
                                f" - {cat['category']} (severity={cat['severity']})\n"
                            )
                        if blocklist_matches:
                            blocked_msg_content += (
                                "\nBlocklist Matches:\n" +
                                "\n".join([f" - {m['blocklistItemText']} (in {m['blocklistName']})"
                                           for m in blocklist_matches])
                            )

                        # Insert a special "role": "safety" or "blocked"
                        safety_message_id = f"{conversation_id}_safety_{int(time.time())}_{random.randint(1000,9999)}"
                        conversation_item['messages'].append({
                            'role': 'safety',
                            'content': blocked_msg_content.strip(),
                            'model_deployment_name': None,
                            'message_id': safety_message_id
                        })
                        conversation_item['last_updated'] = datetime.utcnow().isoformat()
                        container.upsert_item(body=conversation_item)

                        # Return a normal 200 with a special field: blocked=True
                        return jsonify({
                            'reply': "Your message was blocked by content safety.",
                            'blocked': True,
                            'triggered_categories': triggered_categories,
                            'blocklist_matches': blocklist_matches,
                            'conversation_id': conversation_id,
                            'conversation_title': conversation_item['title'],
                            'message_id': safety_message_id
                        }), 200

                except HttpResponseError as e:
                    print(f"[Content Safety Error] {e}")
                except Exception as ex:
                    print(f"[Content Safety] Unexpected error: {ex}")

            # ---------------------------------------------------------------------
            # 4) If not blocked, continue your normal logic (hybrid search, Bing, etc.)
            # ---------------------------------------------------------------------

            # Hybrid Search
            if use_open_ai and not hybrid_search_enabled:
                system_prompt = (
                    "You are an AI assistant named Claude. Answer this question based on your general knowledge.\n"
                    "If you don't know the answer, just say that you don't know, don't try to make up an answer.\n"
                    "Always cite your sources when referring to studies, statistics, or specific information."
                )
                
                system_message_id = f"{conversation_id}_system_{int(time.time())}_{random.randint(1000,9999)}"
                conversation_item['messages'].append({
                    'role': 'system',
                    'content': system_prompt,
                    'model_deployment_name': None,
                    'message_id': system_message_id
                })
                conversation_item['last_updated'] = datetime.utcnow().isoformat()
                container.upsert_item(body=conversation_item)

            # Hybrid Search - only execute if hybrid_search_enabled is True
            if hybrid_search_enabled:
                if selected_document_id:
                    search_results = hybrid_search(
                        user_message, 
                        user_id, 
                        document_id=selected_document_id, 
                        top_n=5, 
                        doc_scope=document_scope, 
                        active_group_id=active_group_id,
                        document_group_id=document_group_id  # Pass document_group_id to hybrid_search
                    )
                else:
                    search_results = hybrid_search(
                        user_message, 
                        user_id, 
                        top_n=5, 
                        doc_scope=document_scope, 
                        active_group_id=active_group_id
                    )
                if search_results:
                    retrieved_texts = []
                    # In the hybrid_search section where citations are created:
                    for doc in search_results:
                        chunk_text = doc['chunk_text']
                        file_name = doc['file_name']
                        
                        # Ensure page_number is an integer and valid
                        page_number = 1  # Default fallback
                        
                        if 'page_number' in doc and doc['page_number'] is not None:
                            try:
                                page_number = int(doc['page_number'])
                                if page_number < 1:  # Ensure page is positive
                                    page_number = 1
                            except (ValueError, TypeError):
                                print(f"Warning: Could not convert page number '{doc['page_number']}' to integer for citation")
                        
                        citation_id = doc['id']
                        citation = f"(Source: {file_name}, Page: {page_number}) [#{citation_id}]"
                        retrieved_texts.append(f"{chunk_text}\n{citation}")

                    retrieved_content = "\n\n".join(retrieved_texts)
                    system_prompt = (
                        "You are an AI assistant provided with the following document excerpts and their sources.\n"
                        "When you answer the user's question, please cite the sources by including the citations provided after each excerpt.\n"
                        "Use the format (Source: filename, Page: page number) [#ID] for citations, where ID is the unique identifier provided.\n"
                        "Ensure your response is informative and includes citations using this format.\n\n"
                        "For example:\n"
                        "User: What is the policy on double dipping?\n"
                        "Assistant: The policy prohibits entities from using federal funds received through one program to apply for additional \n"
                        "funds through another program, commonly known as 'double dipping' (Source: PolicyDocument.pdf, Page: 12) [#123abc].\n\n"
                        f"{retrieved_content}"
                    )

                    system_message_id = f"{conversation_id}_system_{int(time.time())}_{random.randint(1000,9999)}"
                    conversation_item['messages'].append({
                        'role': 'system',
                        'content': system_prompt,
                        'model_deployment_name': None,
                        'message_id': system_message_id
                    })
                    conversation_item['last_updated'] = datetime.utcnow().isoformat()
                    container.upsert_item(body=conversation_item)

            # Bing Search
            if bing_search_enabled:
                bing_results = process_query_with_bing_and_llm(user_message)
                if bing_results:
                    retrieved_texts = []
                    for r in bing_results:
                        title = r["name"]
                        snippet = r["snippet"]
                        url = r["url"]
                        citation = f"(Source: {title}) [{url}]"
                        retrieved_texts.append(f"{snippet}\n{citation}")

                    retrieved_content = "\n\n".join(retrieved_texts)
                    system_prompt = (
                        "You are an AI assistant provided with the following web search results.\n"
                        "When you answer the user's question, cite the sources by including the citations:\n"
                        "Use the format (Source: page_title) [url].\n\n"
                        "For example:\n"
                        "User: What is the capital of France?\n"
                        "Assistant: The capital of France is Paris (Source: OfficialFrancePage) [https://url.com].\n\n"
                        f"{retrieved_content}"
                    )
                    system_message_id = f"{conversation_id}_system_{int(time.time())}_{random.randint(1000,9999)}"
                    conversation_item['messages'].append({
                        'role': 'system',
                        'content': system_prompt,
                        'model_deployment_name': None,
                        'message_id': system_message_id
                    })
                    conversation_item['last_updated'] = datetime.utcnow().isoformat()
                    container.upsert_item(body=conversation_item)

            # Image Generation
            if image_gen_enabled:
                if enable_image_gen_apim:
                    image_gen_model = settings.get('azure_apim_image_gen_deployment')
                    image_gen_client = AzureOpenAI(
                        api_version=settings.get('azure_apim_image_gen_api_version'),
                        azure_endpoint=settings.get('azure_apim_image_gen_endpoint'),
                        api_key=settings.get('azure_apim_image_gen_subscription_key')
                    )
                else:
                    if (settings.get('azure_openai_image_gen_authentication_type') == 'managed_identity'):
                        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
                        image_gen_client = AzureOpenAI(
                            api_version=settings.get('azure_openai_image_gen_api_version'),
                            azure_endpoint=settings.get('azure_openai_image_gen_endpoint'),
                            azure_ad_token_provider=token_provider
                        )
                        image_gen_model_obj = settings.get('image_gen_model', {})

                        if image_gen_model_obj and image_gen_model_obj.get('selected'):
                            selected_image_gen_model = image_gen_model_obj['selected'][0]
                            image_gen_model = selected_image_gen_model['deploymentName']
                    else:
                        image_gen_client = AzureOpenAI(
                            api_version=settings.get('azure_openai_image_gen_api_version'),
                            azure_endpoint=settings.get('azure_openai_image_gen_endpoint'),
                            api_key=settings.get('azure_openai_image_gen_key')
                        )
                        image_gen_obj = settings.get('image_gen_model', {})
                        if image_gen_obj and image_gen_obj.get('selected'):
                            selected_image_gen_model = image_gen_obj['selected'][0]
                            image_gen_model = selected_image_gen_model['deploymentName']

                try:
                    image_response = image_gen_client.images.generate(
                        prompt=user_message,
                        n=1,
                        model=image_gen_model
                    )
                    generated_image_url = json.loads(image_response.model_dump_json())['data'][0]['url']

                    image_message_id = f"{conversation_id}_image_{int(time.time())}_{random.randint(1000,9999)}"
                    conversation_item['messages'].append({
                        'role': 'image',
                        'content': generated_image_url,
                        'prompt': user_message,
                        'created_at': datetime.utcnow().isoformat(),
                        'model_deployment_name': image_gen_model,
                        'message_id': image_message_id
                    })

                    conversation_item['last_updated'] = datetime.utcnow().isoformat()
                    container.upsert_item(body=conversation_item)

                    return jsonify({
                        'reply': f"Here's your generated image: {generated_image_url}",
                        'image_url': generated_image_url,
                        'conversation_id': conversation_id,
                        'conversation_title': conversation_item['title'],
                        'model_deployment_name': image_gen_model,
                        'message_id': image_message_id
                    }), 200
                except Exception as e:
                    return jsonify({'error': f'Image generation failed: {str(e)}'}), 500

            # ---------------------------------------------------------------------
            # 5) GPT logic with streaming support
            # ---------------------------------------------------------------------
            conversation_history_limit = settings.get('conversation_history_limit', 10)
            conversation_history = conversation_item['messages'][-conversation_history_limit:]

            allowed_roles = ['system', 'assistant', 'user', 'function', 'tool']
            conversation_history_for_api = []
            for msg in conversation_history:
                if msg['role'] in allowed_roles:
                    conversation_history_for_api.append(msg)
                elif msg['role'] == 'file':
                    file_content = msg.get('file_content', '')
                    filename = msg.get('filename', 'uploaded_file')
                    max_file_content_length = 50000
                    if len(file_content) > max_file_content_length:
                        file_content = file_content[:max_file_content_length] + '...'

                    system_message = {
                        'role': 'system',
                        'content': f"The user uploaded a file named '{filename}' with the following content:\n\n{file_content}\n\nPlease use this information to assist the user.",
                        'model_deployment_name': None
                    }
                    conversation_history_for_api.append(system_message)
                else:
                    # e.g. skip 'safety' messages from the prompt to GPT
                    continue

            # Decide GPT model
            if enable_gpt_apim:
                gpt_model = settings.get('azure_apim_gpt_deployment')
                gpt_client = AzureOpenAI(
                    api_version=settings.get('azure_apim_gpt_api_version'),
                    azure_endpoint=settings.get('azure_apim_gpt_endpoint'),
                    api_key=settings.get('azure_apim_gpt_subscription_key')
                )
            else:
                if (settings.get('azure_openai_gpt_authentication_type') == 'managed_identity'):
                    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
                    gpt_client = AzureOpenAI(
                        api_version=settings.get('azure_openai_gpt_api_version'),
                        azure_endpoint=settings.get('azure_openai_gpt_endpoint'),
                        azure_ad_token_provider=token_provider
                    )
                    gpt_model_obj = settings.get('gpt_model', {})
                    if gpt_model_obj and gpt_model_obj.get('selected'):
                        selected_gpt_model = gpt_model_obj['selected'][0]
                        gpt_model = selected_gpt_model['deploymentName']
                else:
                    gpt_client = AzureOpenAI(
                        api_version=settings.get('azure_openai_gpt_api_version'),
                        azure_endpoint=settings.get('azure_openai_gpt_endpoint'),
                        api_key=settings.get('azure_openai_gpt_key')
                    )
                    gpt_model_obj = settings.get('gpt_model', {})
                    if gpt_model_obj and gpt_model_obj.get('selected'):
                        selected_gpt_model = gpt_model_obj['selected'][0]
                        gpt_model = selected_gpt_model['deploymentName']

            # Generate a message ID now so it's consistent for both streaming and non-streaming
            assistant_message_id = f"{conversation_id}_assistant_{int(time.time())}_{random.randint(1000,9999)}"
            
            # Handle streaming vs non-streaming based on parameter
            if streaming_enabled:
                # Streaming response function
                def generate_streaming_response():
                    full_response = ""
                    
                    try:
                        # Send the conversation_id and message_id first
                        yield f"data: {json.dumps({'conversation_id': conversation_id, 'message_id': assistant_message_id, 'conversation_title': conversation_item['title'], 'type': 'info'})}\n\n"
                        
                        # Request a streaming response from the model
                        stream = gpt_client.chat.completions.create(
                            model=gpt_model,
                            messages=conversation_history_for_api,
                            stream=True  # Enable streaming
                        )
                        
                        # Stream each chunk as it arrives
                        for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                full_response += content
                                
                                # Send the chunk to the client
                                yield f"data: {json.dumps({'content': content, 'type': 'chunk'})}\n\n"
                        
                        # Save the complete response to the database
                        conversation_item['messages'].append({
                            'role': 'assistant',
                            'content': full_response,
                            'model_deployment_name': gpt_model,
                            'message_id': assistant_message_id
                        })
                        conversation_item['last_updated'] = datetime.utcnow().isoformat()
                        container.upsert_item(body=conversation_item)
                        
                        # Signal that the streaming is complete
                        yield f"data: {json.dumps({'type': 'done', 'model_deployment_name': gpt_model})}\n\n"
                        
                    except Exception as e:
                        print(f"Streaming error: {str(e)}")
                        error_message = f"Error generating model response: {str(e)}"
                        yield f"data: {json.dumps({'error': error_message, 'type': 'error'})}\n\n"
                
                # Return a streaming response
                return Response(
                    generate_streaming_response(),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'X-Accel-Buffering': 'no'  # Important for nginx
                    }
                )
            
            else:
                # Non-streaming (original) implementation
                try:
                    response = gpt_client.chat.completions.create(
                        model=gpt_model,
                        messages=conversation_history_for_api
                    )
                    ai_message = response.choices[0].message.content
                except Exception as e:
                    print(str(e))
                    return jsonify({'error': f'Error generating model response: {str(e)}'}), 500

                # Save GPT response
                conversation_item['messages'].append({
                    'role': 'assistant',
                    'content': ai_message,
                    'model_deployment_name': gpt_model,
                    'message_id': assistant_message_id
                })
                conversation_item['last_updated'] = datetime.utcnow().isoformat()
                container.upsert_item(body=conversation_item)

                # Return final success
                return jsonify({
                    'reply': ai_message,
                    'conversation_id': conversation_id,
                    'conversation_title': conversation_item['title'],
                    'model_deployment_name': gpt_model,
                    'message_id': assistant_message_id
                }), 200
                
        except Exception as e:
            print(f"Error in chat_api: {str(e)}")  # Log any exceptions
            return jsonify({'error': 'Internal server error'}), 500