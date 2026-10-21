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


@pytest.mark.asyncio
async def test_content_server_custom_site_hosting_and_web_dir(tmp_path):
    # Create temp web_dir with custom website files
    web_dir = tmp_path / "sites"
    web_dir.mkdir()

    site1 = web_dir / "anonsite.html"
    site1.write_text("<h1>Welcome to Anon Site</h1>", encoding="utf-8")

    site2 = web_dir / "secret.spec"
    site2.write_text("<h1>Top Secret Spec Document</h1>", encoding="utf-8")

    forbidden = tmp_path / "forbidden.txt"
    forbidden.write_text("SECRET DATA", encoding="utf-8")

    server = SpectreContentServer(host="127.0.0.1", port=19089, web_dir=str(web_dir))
    server.register_page("dynamic.spec", "<h1>Dynamic Registered Site</h1>")

    # Register via file
    single_file = tmp_path / "single_site.html"
    single_file.write_text("<h1>Single Hosted Site File</h1>", encoding="utf-8")
    server.register_site_file("single.spec", str(single_file))

    await server.start()

    try:
        # Request dynamic registered page
        r1, w1 = await asyncio.open_connection("127.0.0.1", 19089)
        await send_frame(w1, b"GET dynamic.spec")
        resp1 = (await read_frame(r1)).decode("utf-8")
        w1.close()
        assert "200 OK" in resp1
        assert "Dynamic Registered Site" in resp1

        # Request single site file
        r2, w2 = await asyncio.open_connection("127.0.0.1", 19089)
        await send_frame(w2, b"GET single.spec")
        resp2 = (await read_frame(r2)).decode("utf-8")
        w2.close()
        assert "200 OK" in resp2
        assert "Single Hosted Site File" in resp2

        # Request file from web_dir using .spec extension for anonsite.html
        r3, w3 = await asyncio.open_connection("127.0.0.1", 19089)
        await send_frame(w3, b"GET anonsite.spec")
        resp3 = (await read_frame(r3)).decode("utf-8")
        w3.close()
        assert "200 OK" in resp3
        assert "Welcome to Anon Site" in resp3

        # Request secret.spec directly
        r4, w4 = await asyncio.open_connection("127.0.0.1", 19089)
        await send_frame(w4, b"GET secret.spec")
        resp4 = (await read_frame(r4)).decode("utf-8")
        w4.close()
        assert "200 OK" in resp4
        assert "Top Secret Spec Document" in resp4

        # Path traversal attack attempt check
        r5, w5 = await asyncio.open_connection("127.0.0.1", 19089)
        await send_frame(w5, b"GET ../forbidden.txt")
        resp5 = (await read_frame(r5)).decode("utf-8")
        w5.close()
        assert "404 Not Found" in resp5

    finally:
        await server.stop()
