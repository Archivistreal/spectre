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
        # Request genesis.spectre
        reader, writer = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer, b"GET genesis.spectre")
        resp1 = (await read_frame(reader)).decode("utf-8")
        writer.close()

        assert "200 OK" in resp1
        assert "Welcome to Spectre Network Genesis Page" in resp1

        # Request manifesto.spectre
        reader2, writer2 = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer2, b"GET manifesto.spectre")
        resp2 = (await read_frame(reader2)).decode("utf-8")
        writer2.close()

        assert "200 OK" in resp2
        assert "Privacy is a Fundamental Human Right" in resp2

        # Request missing page
        reader3, writer3 = await asyncio.open_connection("127.0.0.1", 19088)
        await send_frame(writer3, b"GET unknown.spectre")
        resp3 = (await read_frame(reader3)).decode("utf-8")
        writer3.close()

        assert "404 Not Found" in resp3

    finally:
        await server.stop()
