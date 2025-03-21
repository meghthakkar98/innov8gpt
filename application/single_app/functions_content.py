# functions_content.py

from config import *
from functions_settings import *

def extract_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_content_with_azure_di(file_path):
    try:
        with open(file_path, "rb") as f:
            document_intelligence_client = CLIENTS['document_intelligence_client']
            poller = document_intelligence_client.begin_analyze_document(
                model_id="prebuilt-read",
                document=f
            )
        
        max_wait_time = 600
        start_time = time.time()

        while True:
            status = poller.status()
            if status in ["succeeded", "failed", "canceled"]:
                break
            if time.time() - start_time > max_wait_time:
                raise TimeoutError("Document analysis took too long.")
            time.sleep(5)

        result = poller.result()
        extracted_content = ""

        if result.content:
            extracted_content = result.content
        else:
            for page in result.pages:
                for line in page.lines:
                    extracted_content += line.content + "\n"
                extracted_content += "\n"

        return extracted_content

    except Exception as e:
        raise

def extract_table_file(file_path, file_ext):
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file extension for table extraction.")
        
        table_html = df.to_html(index=False, classes='table table-striped table-bordered')
        return table_html
    except Exception as e:
        raise

def chunk_text(text, chunk_size=2000, overlap=200):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def generate_embedding(
    text,
    max_retries=5,
    initial_delay=1.0,
    delay_multiplier=2.0
):
    settings = get_settings()

    retries = 0
    current_delay = initial_delay

    enable_image_gen_apim = settings.get('enable_image_gen_apim', False)

    if enable_image_gen_apim:
        embedding_model = settings.get('azure_apim_embedding_deployment')
        embedding_client = AzureOpenAI(
            api_version = settings.get('azure_apim_embedding_api_version'),
            azure_endpoint = settings.get('azure_apim_embedding_endpoint'),
            api_key=settings.get('azure_apim_embedding_subscription_key'))
    else:
        if (settings.get('azure_openai_embedding_authentication_type') == 'managed_identity'):
            token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
            embedding_client = AzureOpenAI(
                api_version=settings.get('azure_openai_embedding_api_version'),
                azure_endpoint=settings.get('azure_openai_embedding_endpoint'),
                azure_ad_token_provider=token_provider
            )
        
            embedding_model_obj = settings.get('embedding_model', {})
            if embedding_model_obj and embedding_model_obj.get('selected'):
                selected_embedding_model = embedding_model_obj['selected'][0]
                embedding_model = selected_embedding_model['deploymentName']
        else:
            embedding_client = AzureOpenAI(
                api_version=settings.get('azure_openai_embedding_api_version'),
                azure_endpoint=settings.get('azure_openai_embedding_endpoint'),
                api_key=settings.get('azure_openai_embedding_key')
            )
            
            embedding_model_obj = settings.get('embedding_model', {})
            if embedding_model_obj and embedding_model_obj.get('selected'):
                selected_embedding_model = embedding_model_obj['selected'][0]
                embedding_model = selected_embedding_model['deploymentName']

    while True:
        random_delay = random.uniform(0.5, 2.0)
        time.sleep(random_delay)

        try:
            response = embedding_client.embeddings.create(
                model=embedding_model,
                input=text
            )

            embedding = response.data[0].embedding
            return embedding

        except RateLimitError as e:
            retries += 1
            if retries > max_retries:
                return None

            wait_time = current_delay * random.uniform(1.0, 1.5)
            time.sleep(wait_time)
            current_delay *= delay_multiplier

        except Exception as e:
            return None