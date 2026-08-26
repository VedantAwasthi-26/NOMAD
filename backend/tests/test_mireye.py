import asyncio

from app.integrations.mireye.client import mireye_client


async def main():
    result = await mireye_client.get_fields()

    assert result is not None

    print("Mireye fields test: PASSED")


asyncio.run(main())