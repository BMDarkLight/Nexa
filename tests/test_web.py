import subprocess
import time
import httpx
import pytest

BASE_URL = "http://localhost:3000"
SERVER_PROCESS = None

@pytest.fixture(scope="session", autouse=True)
def build_and_start_nextjs():
    # Build Next.js app first
    subprocess.run(["npm", "install"], cwd="web", check=True)
    subprocess.run(["npm", "run", "build"], cwd="web", check=True)

    global SERVER_PROCESS
    SERVER_PROCESS = subprocess.Popen(
        ["npm", "run", "start"],
        cwd="web",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)
    yield
    SERVER_PROCESS.terminate()

@pytest.mark.asyncio
async def test_nextjs_root():
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL)
        assert response.status_code == 200
        assert "html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_nextjs_custom_route():
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, timeout=10.0)
        assert response.status_code in [200, 404]