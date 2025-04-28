# functions_content.py

from config import *
from functions_settings import *
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

def extract_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Update extract_content_with_azure_di in functions_content.py

def extract_content_with_azure_di(file_path):
    """
    Extract content from document using Azure Document Intelligence.
    """
    try:
        print(f"Extracting content with Azure Document Intelligence: {file_path}")
        
        with open(file_path, "rb") as f:
            document_intelligence_client = CLIENTS['document_intelligence_client']
            poller = document_intelligence_client.begin_analyze_document(
                model_id="prebuilt-read",
                document=f
            )
        
        max_wait_time = 1600
        start_time = time.time()

        while True:
            status = poller.status()
            if status in ["succeeded", "failed", "canceled"]:
                break
            if time.time() - start_time > max_wait_time:
                raise TimeoutError("Document analysis took too long.")
            time.sleep(5)

        result = poller.result()
        
        # Process each page separately with its page number
        pages_content = []
        
        if hasattr(result, 'pages') and result.pages:
            # Handle multi-page documents
            for page_idx, page in enumerate(result.pages):
                page_number = page_idx + 1
                page_text = ""
                
                for line in page.lines:
                    page_text += line.content + "\n"
                
                if page_text.strip():
                    pages_content.append({
                        "page_number": page_number,
                        "text": page_text
                    })
                    print(f"Extracted page {page_number}")
        
        # If no pages were processed but there's content, create a single page
        if not pages_content and result.content:
            # Split the content into multiple artificial pages
            full_text = result.content
            words = full_text.split()
            total_words = len(words)
            
            # Create multiple pages (approx. 500 words per page)
            words_per_page = 500
            num_pages = max(1, (total_words + words_per_page - 1) // words_per_page)
            
            for i in range(num_pages):
                start_idx = i * words_per_page
                end_idx = min(start_idx + words_per_page, total_words)
                page_text = " ".join(words[start_idx:end_idx])
                
                pages_content.append({
                    "page_number": i + 1,
                    "text": page_text
                })
                print(f"Created artificial page {i+1}")
        
        # Fallback for empty documents
        if not pages_content:
            pages_content.append({
                "page_number": 1,
                "text": "No text content could be extracted from this document."
            })
            print("No content extracted, created fallback page")
        
        return {
            "content": pages_content,
            "pages_info": pages_content
        }

    except Exception as e:
        print(f"Error extracting content: {str(e)}")
        traceback.print_exc()
        
        # Return minimal valid result
        return {
            "content": [{
                "page_number": 1,
                "text": "Error processing document."
            }],
            "pages_info": [{
                "page_number": 1,
                "text": "Error processing document."
            }]
        }
    
def chunk_text(pages_content, pages_info=None, chunk_size=2000, overlap=200):
    """
    Split text into chunks with accurate tracking of original page numbers.
    Improved for better handling of Azure Document Intelligence results.
    
    Args:
        pages_content: List of dicts with page number and text
        pages_info: Not used, kept for compatibility
        chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of tuples: (chunk_text, page_number)
    """
    all_chunks = []
    
    if not pages_content:
        print("Warning: No content to chunk")
        return [("No content was extracted from this document.", 1)]
    
    print(f"Chunking {len(pages_content)} pages")
    
    # Process each page independently to maintain page number association
    for page_data in pages_content:
        page_number = page_data["page_number"]
        page_text = page_data.get("text", "")
        
        if not page_text or not page_text.strip():
            print(f"Skipping empty page {page_number}")
            continue
        
        print(f"Processing page {page_number}: {len(page_text)} chars")
        
        # If page text is very small, just use it as is
        if len(page_text) < chunk_size // 2:
            all_chunks.append((page_text, page_number))
            print(f"Added entire page {page_number} as single chunk ({len(page_text)} chars)")
            continue
            
        # Create chunks for larger pages
        position = 0
        chunks_from_page = 0
        
        while position < len(page_text):
            end = min(position + chunk_size, len(page_text))
            
            # Try to find a natural break point (period, newline, etc.)
            if end < len(page_text) and end - position > chunk_size // 2:
                # Look for sentence endings, then for line breaks, then for word boundaries
                natural_break = page_text.rfind('. ', position, end)
                if natural_break == -1 or natural_break < position + chunk_size // 2:
                    natural_break = page_text.rfind('\n', position, end)
                if natural_break == -1 or natural_break < position + chunk_size // 2:
                    natural_break = page_text.rfind(' ', position, end)
                if natural_break != -1 and natural_break > position + chunk_size // 2:
                    end = natural_break + 1  # Include the period or space
            
            chunk_text = page_text[position:end].strip()
            
            # Only add non-empty chunks
            if chunk_text:
                all_chunks.append((chunk_text, page_number))
                chunks_from_page += 1
                print(f"Created chunk {chunks_from_page} from page {page_number}: {len(chunk_text)} chars")
            
            # Move to next chunk with overlap
            position = end - overlap if end < len(page_text) else len(page_text)
    
    # If we still have no chunks, create a minimal one to prevent downstream errors
    if not all_chunks:
        print("Warning: No chunks created, adding a minimal chunk")
        all_chunks.append(("Document processing completed, but no usable content was found.", 1))
    
    print(f"Generated {len(all_chunks)} total chunks across all pages")
    return all_chunks


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
        
