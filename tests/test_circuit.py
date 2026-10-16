import asyncio
import pytest
import pytest_asyncio
from core.node import SpectreNode, SpectreClientCircuit, send_frame, read_frame


@pytest.mark.asyncio
async def test_3hop_circuit_building_and_transmission():
    # Helper dummy echo server representing target content server
    async def echo_handler(reader, writer):
        data = await read_frame(reader)
        resp = b"SPECTRE/1.0 200 OK\r\n\r\nEcho: " + data
        await send_frame(writer, resp)
        writer.close()

    echo_server = await asyncio.start_server(echo_handler, "127.0.0.1", 19090)

    # Spin up Guard, Relay, Exit daemon nodes on distinct ports
    guard = SpectreNode("GuardNode", "127.0.0.1", 19001, role="guard")
    relay = SpectreNode("RelayNode", "127.0.0.1", 19002, role="relay")
    exit_node = SpectreNode("ExitNode", "127.0.0.1", 19003, role="exit")

    await guard.start()
    await relay.start()
    await exit_node.start()

    try:
        # Client creates circuit
        circuit = SpectreClientCircuit(
            guard_address=("127.0.0.1", 19001),
            relay_address=("127.0.0.1", 19002),
            exit_address=("127.0.0.1", 19003)
        )

        keys = await circuit.build_circuit()
        assert len(keys) == 3

        # Send request through onion network to echo server
        response = await circuit.send_request("127.0.0.1", 19090, "GET /index.spectre")
        assert "200 OK" in response
        assert "Echo: GET /index.spectre" in response

        await circuit.close()

    finally:
        await guard.stop()
        await relay.stop()
        await exit_node.stop()
        echo_server.close()
        await echo_server.wait_closed()
