# test_blob_connection.py
import os

from config import *

# Print environment variables (without secrets)
print(f"Container name: {os.getenv('AZURE_STORAGE_CONTAINER_NAME')}")
print(f"Connection string exists: {'Yes' if os.getenv('AZURE_STORAGE_CONNECTION_STRING') else 'No'}")

# Try to create the client
try:
    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
    container_client = blob_service_client.get_container_client(os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'documents'))
    
    # Test if container exists
    if container_client.exists():
        print(f"Container {os.getenv('AZURE_STORAGE_CONTAINER_NAME')} exists!")
    else:
        print(f"Container {os.getenv('AZURE_STORAGE_CONTAINER_NAME')} does not exist!")
    
    # List some blobs if any
    blobs = list(container_client.list_blobs(max_results=5))
    print(f"Found {len(blobs)} blobs in container")
    
except Exception as e:
    print(f"Error initializing Blob Storage client: {str(e)}")