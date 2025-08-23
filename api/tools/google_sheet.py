import json
from langchain.agents import tool
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

@tool("read_google_sheet")
def read_google_sheet(settings: dict, spreadsheet_id: str, range_name: str) -> str:
    """
    Reads data from a specific range within a Google Sheet.

    Args:
        settings (dict): A dictionary containing service account credentials from Google Cloud.
        spreadsheet_id (str): The unique ID of the Google Sheet to read from.
        range_name (str): The range of cells to read in A1 notation (e.g., 'Sheet1!A1:B10').

    Returns:
        str: The data from the specified range, formatted as a CSV string.
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

        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)

        service = build('sheets', 'v4', credentials=creds)

        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])

        if not values:
            return f"No data found in range '{range_name}' of spreadsheet '{spreadsheet_id}'."
        
        output_string = "\n".join([",".join(map(str, row)) for row in values])
        return f"Data from spreadsheet '{spreadsheet_id}', range '{range_name}':\n{output_string}"

    except HttpError as err:
        if err.resp.status == 403:
            return f"Error: Permission denied. Make sure the service account has been shared on the Google Sheet '{spreadsheet_id}'."
        if err.resp.status == 404:
            return f"Error: Spreadsheet not found. Please check the spreadsheet_id '{spreadsheet_id}'."
        return f"An API error occurred: {err}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

