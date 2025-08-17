from langchain.agents import tool
from langchain_community.tools import DuckDuckGoSearchRun

search = DuckDuckGoSearchRun()

@tool("search_web", return_direct=True)
def search_web(query: str) -> str:
    """Search the internet using DuckDuckGo."""
    return search.run(query)
    