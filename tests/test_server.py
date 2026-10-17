import asyncio
import pytest
import pytest_asyncio
from server.host import SpectreContentServer
from core.node import send_frame, read_frame


@pytest.mark.asyncio
async def test_content_server_pages():
    server = SpectreContentServer(host="127.0.0.1", port=19088)
    await server.start()

    try:
        # Request spectre.spec (flagship home)
        reader0, writer0 = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer0, b"GET spectre.spec")
        resp0 = (await read_frame(reader0)).decode("utf-8")
        writer0.close()

        assert "200 OK" in resp0
        assert "Official Spectre Network Portal" in resp0

        # Request genesis.spec
        reader, writer = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer, b"GET genesis.spec")
        resp1 = (await read_frame(reader)).decode("utf-8")
        writer.close()

        assert "200 OK" in resp1
        assert "Welcome to Spectre Network Genesis Page" in resp1

        # Request manifesto.spec
        reader2, writer2 = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer2, b"GET manifesto.spec")
        resp2 = (await read_frame(reader2)).decode("utf-8")
        writer2.close()

        assert "200 OK" in resp2
        assert "The Spectre Cypherpunk Manifesto" in resp2

        # Request missing page
        reader3, writer3 = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer3, b"GET unknown.spec")
        resp3 = (await read_frame(reader3)).decode("utf-8")
        writer3.close()

        assert "404 Not Found" in resp3

    finally:
        await server.stop()
