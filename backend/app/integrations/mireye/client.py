import httpx
from app.config.settings import settings


class MireyeClient:
    def __init__(self, api_key: str, base_url: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=60.0
        )

    async def get_fields(self):
        response = await self.client.get("/v1/meta/fields")
        response.raise_for_status()
        return response.json()

    async def fetch(self, payload: dict):
        response = await self.client.post("/v1/fetch", json=payload)
        response.raise_for_status()
        return response.json()

    async def proximity(self, payload: dict):
        response = await self.client.post("/v1/proximity", json=payload)
        response.raise_for_status()
        return response.json()

mireye_client = MireyeClient(
    api_key=settings.mireye_api_key,
    base_url=settings.mireye_base_url
)