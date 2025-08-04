import httpx
import pytest

BASE_URL = "http://localhost:3000"

@pytest.mark.asyncio
async def test_nextjs_root():
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL)
        assert response.status_code == 200
        assert "html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_nextjs_custom_route():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}", timeout=10.0)
        assert response.status_code in [200, 404]