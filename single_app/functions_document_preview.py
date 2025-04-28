# functions_document_preview.py

from config import *
import msal
import requests
from urllib.parse import urlparse
import tempfile
import os

def get_graph_token():
    """
    Get a Microsoft Graph API access token using app credentials.
    Uses the same app registration as your authentication.
    """
    try:
        # Create an MSAL app for token acquisition
        app = msal.ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=AUTHORITY
        )
        
        # Get token for Microsoft Graph API
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            return result["access_token"]
        else:
            print(f"Error getting Graph token: {result.get('error')}")
            print(f"Error description: {result.get('error_description')}")
            return None
    except Exception as e:
        print(f"Exception getting Graph token: {str(e)}")
        return None

def upload_temp_file_to_graph(file_content, file_name):
    """
    Upload a file to Microsoft Graph OneDrive for temporary storage and preview.
    
    Args:
        file_content: The binary file content
        file_name: Name of the file (including extension)
        
    Returns:
        Tuple of (item_id, preview_url) if successful, (None, None) if failed
    """
    try:
        token = get_graph_token()
        if not token:
            return None, None
        
        # Step 1: Create upload session
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Use the app's OneDrive for temporary storage in a 'TempDocViewer' folder
        # Create this folder in your app's OneDrive before using
        session_url = "https://graph.microsoft.com/v1.0/me/drive/root:/TempDocViewer/{file_name}:/createUploadSession"
        session_url = session_url.format(file_name=file_name)
        
        session_response = requests.post(
            session_url,
            headers=headers,
            json={}
        )
        
        if session_response.status_code != 200:
            print(f"Error creating upload session: {session_response.text}")
            return None, None
        
        upload_url = session_response.json().get("uploadUrl")
        
        # Step 2: Upload the file
        headers = {
            "Content-Length": str(len(file_content)),
            "Content-Range": f"bytes 0-{len(file_content)-1}/{len(file_content)}"
        }
        
        upload_response = requests.put(
            upload_url,
            headers=headers,
            data=file_content
        )
        
        if upload_response.status_code not in [200, 201, 202]:
            print(f"Error uploading file: {upload_response.text}")
            return None, None
        
        # Get the item ID from the response
        item_id = upload_response.json().get("id")
        
        # Step 3: Get a preview URL
        preview_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/preview"
        preview_response = requests.post(
            preview_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if preview_response.status_code != 200:
            print(f"Error getting preview URL: {preview_response.text}")
            return item_id, None
        
        # Get the preview URL from the response
        get_url = preview_response.json().get("getUrl")
        
        return item_id, get_url
    
    except Exception as e:
        print(f"Exception in upload_temp_file_to_graph: {str(e)}")
        return None, None

def get_office_preview_url(blob_url, file_name):
    """
    Get a Microsoft Graph preview URL for an Office document.
    
    Args:
        blob_url: The blob storage URL of the document
        file_name: The name of the file
        
    Returns:
        A preview URL if successful, None if failed
    """
    try:
        # Download the document from blob storage
        file_content = download_from_blob_storage(blob_url)
        
        # Upload to Graph and get preview URL
        item_id, preview_url = upload_temp_file_to_graph(file_content, file_name)
        
        # Schedule cleanup of temporary file (in a production app)
        # This would typically be done with a background task
        
        return preview_url
    
    except Exception as e:
        print(f"Exception in get_office_preview_url: {str(e)}")
        return None