import asyncio
from app.integrations.mireye.client import mireye_client


async def main():
    result = await mireye_client.get_fields()
    print(result)


asyncio.run(main())