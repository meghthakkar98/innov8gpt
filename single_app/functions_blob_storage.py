# functions_blob_storage.py - KEEP THIS FILE AS IS
import config
import uuid
from azure.storage.blob import ContentSettings

def upload_to_blob_storage(file_content, file_name, content_type=None):
    """
    Upload file content to Azure Blob Storage
    """
    try:
        # Access CLIENTS through the config module
        blob_service_client = config.CLIENTS.get("blob_service_client")
        container_client = config.CLIENTS.get("blob_container_client")
        
        if not blob_service_client or not container_client:
            raise Exception("Blob storage client not initialized")
        
        # Get the container name from config
        blob_container_name = config.blob_container_name
        
        # Create a unique blob name using UUID
        blob_name = f"{str(uuid.uuid4())}/{file_name}"
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=blob_container_name,
            blob=blob_name
        )
        
        # Set content settings if content type is provided
        content_settings = None
        if content_type:
            content_settings = ContentSettings(content_type=content_type)
        
        # Upload the file
        blob_client.upload_blob(file_content, content_settings=content_settings)
        
        # Return the blob URL
        return blob_client.url
        
    except Exception as e:
        print(f"Error uploading to blob storage: {str(e)}")
        raise

def download_from_blob_storage(blob_url):
    """
    Download file content from Azure Blob Storage
    """
    try:
        # Get the client from config
        blob_service_client = config.CLIENTS.get("blob_service_client")
        if not blob_service_client:
            raise Exception("Blob storage client not initialized")
        
        # Parse URL to get container and blob name
        url_parts = blob_url.replace("https://", "").split("/")
        container_name = url_parts[1]
        blob_name = "/".join(url_parts[2:])  # Handle blobs with / in name
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Download the blob
        download_stream = blob_client.download_blob()
        return download_stream.readall()
        
    except Exception as e:
        print(f"Error downloading from blob storage: {str(e)}")
        raise

def get_blob_properties(blob_url):
    """
    Get properties of a blob
    
    Args:
        blob_url: The full URL of the blob
        
    Returns:
        The blob properties
    """
    try:
        # Extract container name and blob name from URL
        blob_service_client = config.CLIENTS.get("blob_service_client")
        if not blob_service_client:
            raise Exception("Blob storage client not initialized")
        
        # Parse URL to get container and blob name
        url_parts = blob_url.replace("https://", "").split("/")
        container_name = url_parts[1]
        blob_name = "/".join(url_parts[2:])
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Get properties
        return blob_client.get_blob_properties()
        
    except Exception as e:
        print(f"Error getting blob properties: {str(e)}")
        raise

def delete_blob(blob_url):
    """
    Delete a blob from Azure Blob Storage
    
    Args:
        blob_url: The full URL of the blob
    """
    try:
        # Extract container name and blob name from URL
        blob_service_client = config.CLIENTS.get("blob_service_client")
        if not blob_service_client:
            raise Exception("Blob storage client not initialized")
        
        # Parse URL to get container and blob name
        url_parts = blob_url.replace("https://", "").split("/")
        container_name = url_parts[1]
        blob_name = "/".join(url_parts[2:])
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Delete the blob
        blob_client.delete_blob()
        
    except Exception as e:
        print(f"Error deleting blob: {str(e)}")
        raise