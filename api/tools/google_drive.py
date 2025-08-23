import io
import json
from langchain.agents import tool
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

@tool("read_google_drive_file")
def read_google_drive(settings: dict, file_id: str) -> str:
    """
    Reads the content of a specific file from Google Drive. 
    This is best for text-based files like .txt, .csv, .md, etc.

    Args:
        settings (dict): A dictionary containing service account credentials from Google Cloud.
        file_id (str): The unique ID of the Google Drive file to read.

    Returns:
        str: The content of the file as a string.
    """
    try:
        creds_info = settings
        if not creds_info:
            return "Error: Service account information not found in connector settings."

        if isinstance(creds_info, str):
            try:
                creds_info = json.loads(creds_info)
            except json.JSONDecodeError:
                return "Error: The provided settings string is not valid JSON."

        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)

        service = build('drive', 'v3', credentials=creds)

        request = service.files().get_media(fileId=file_id)
        
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_buffer.seek(0)
        try:
            content = file_buffer.read().decode('utf-8')
            return f"Content from Google Drive file '{file_id}':\n{content}"
        except UnicodeDecodeError:
            return f"Error: Could not decode the file '{file_id}' using UTF-8. It may be a binary file or have a different text encoding."

    except HttpError as err:
        if err.resp.status == 403:
            return f"Error: Permission denied. Make sure the service account has been granted access to the Google Drive file '{file_id}'."
        if err.resp.status == 404:
            return f"Error: File not found. Please check the file_id '{file_id}'."
        return f"An API error occurred: {err}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"