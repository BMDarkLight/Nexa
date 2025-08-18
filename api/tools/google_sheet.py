from langchain.agents import tool
from langchain_community.tools import DuckDuckGoSearchRun


@tool("read_google_sheet", return_direct=True)
def read_google_sheet(query: str) -> str:
    """Read data from a Google Sheet."""
    return "This tool is not implemented yet."