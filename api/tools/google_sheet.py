from langchain.agents import tool


@tool("read_google_sheet", return_direct=True)
def read_google_sheet(settings: dict, sheet_id: str, range_name: str):
    """Read data from a Google Sheet."""
    return "This tool is not implemented yet."