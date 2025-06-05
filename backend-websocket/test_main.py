import pytest
import asyncio # For async operations in tests if needed
from main import ConnectionManager # Import your ConnectionManager
from fastapi import WebSocket # For type hinting and potentially mocking

# A simple mock WebSocket class for testing
class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_data = []
        self.received_data_queue = asyncio.Queue() # For simulating received messages
        self.client_disconnected = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        if self.client_disconnected: # Simulate error if trying to send to a "closed" socket
            raise RuntimeError("WebSocket is closed")
        self.sent_data.append(data)

    async def receive_json(self):
        if self.client_disconnected:
            # Simulate how FastAPI/websockets might raise an error or indicate disconnect
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect(code=1000)
        return await self.received_data_queue.get()

    async def close(self, code: int = 1000): # Simulate client closing connection
        self.client_disconnected = True
        # In a real scenario, this might trigger WebSocketDisconnect in the server's read loop

    # Helper to simulate client sending data
    async def simulate_client_send(self, data):
        await self.received_data_queue.put(data)


@pytest.fixture
def manager():
    """Provides a ConnectionManager instance for each test."""
    return ConnectionManager()

@pytest.mark.asyncio # Mark test as asynchronous
async def test_connect_new_group(manager: ConnectionManager):
    ws_alice = MockWebSocket()
    group_id = "test_group_1"
    user_name_alice = "Alice"

    await manager.connect(ws_alice, group_id, user_name_alice)

    assert ws_alice.accepted
    assert group_id in manager.active_connections
    assert ws_alice in manager.active_connections[group_id]
    # Check if "Alice joined" message was sent (it's the first message)
    assert len(ws_alice.sent_data) == 1
    assert ws_alice.sent_data[0]["type"] == "system"
    assert f"User '{user_name_alice}' joined" in ws_alice.sent_data[0]["message"]

@pytest.mark.asyncio
async def test_connect_existing_group(manager: ConnectionManager):
    ws_alice = MockWebSocket()
    ws_bob = MockWebSocket()
    group_id = "test_group_2"
    user_name_alice = "Alice"
    user_name_bob = "Bob"

    # Alice connects
    await manager.connect(ws_alice, group_id, user_name_alice)
    
    # Bob connects to the same group
    await manager.connect(ws_bob, group_id, user_name_bob)

    assert ws_bob.accepted
    assert group_id in manager.active_connections
    assert len(manager.active_connections[group_id]) == 2
    assert ws_alice in manager.active_connections[group_id]
    assert ws_bob in manager.active_connections[group_id]

    # Alice should receive Bob's join message
    # Alice's initial join message + Bob's join message
    assert len(ws_alice.sent_data) == 2
    assert ws_alice.sent_data[1]["type"] == "system"
    assert f"User '{user_name_bob}' joined" in ws_alice.sent_data[1]["message"]

    # Bob should receive his own join message (as per current broadcast logic)
    assert len(ws_bob.sent_data) == 1
    assert ws_bob.sent_data[0]["type"] == "system"
    assert f"User '{user_name_bob}' joined" in ws_bob.sent_data[0]["message"]


@pytest.mark.asyncio
async def test_disconnect_one_user(manager: ConnectionManager):
    ws_alice = MockWebSocket()
    group_id = "test_group_3"
    user_name_alice = "Alice"

    await manager.connect(ws_alice, group_id, user_name_alice)
    assert len(manager.active_connections[group_id]) == 1

    manager.disconnect(ws_alice, group_id, user_name_alice) # disconnect is synchronous

    assert group_id not in manager.active_connections # Group should be removed as it's empty

@pytest.mark.asyncio
async def test_disconnect_user_from_group_with_others(manager: ConnectionManager):
    ws_alice = MockWebSocket()
    ws_bob = MockWebSocket()
    group_id = "test_group_4"
    user_name_alice = "Alice"
    user_name_bob = "Bob"

    await manager.connect(ws_alice, group_id, user_name_alice)
    await manager.connect(ws_bob, group_id, user_name_bob)
    assert len(manager.active_connections[group_id]) == 2

    manager.disconnect(ws_bob, group_id, user_name_bob) # Bob disconnects

    assert group_id in manager.active_connections
    assert len(manager.active_connections[group_id]) == 1
    assert ws_alice in manager.active_connections[group_id]
    assert ws_bob not in manager.active_connections[group_id]

@pytest.mark.asyncio
async def test_broadcast_to_group(manager: ConnectionManager):
    ws_alice = MockWebSocket()
    ws_bob = MockWebSocket()
    ws_charlie = MockWebSocket() # In a different group
    group_id_1 = "test_group_5"
    group_id_2 = "test_group_6" # Different group
    user_alice = "Alice"
    user_bob = "Bob"
    user_charlie = "Charlie"

    await manager.connect(ws_alice, group_id_1, user_alice)
    await manager.connect(ws_bob, group_id_1, user_bob) # Bob in the same group as Alice
    await manager.connect(ws_charlie, group_id_2, user_charlie) # Charlie in a different group

    # Clear initial join messages for easier assertion of broadcast message
    ws_alice.sent_data.clear()
    ws_bob.sent_data.clear()
    ws_charlie.sent_data.clear()

    message_payload = {"type": "chat", "sender": user_alice, "message": "Hello everyone!"}
    # Alice sends a message, so she should be excluded from receiving it back
    await manager.broadcast_to_group(group_id_1, message_payload, exclude_self=ws_alice)

    # Alice (sender) should not have received her own message via this broadcast
    assert len(ws_alice.sent_data) == 0 
    
    # Bob (in same group) should have received the message
    assert len(ws_bob.sent_data) == 1
    assert ws_bob.sent_data[0] == message_payload

    # Charlie (in different group) should not have received the message
    assert len(ws_charlie.sent_data) == 0

@pytest.mark.asyncio
async def test_broadcast_to_empty_group_does_not_fail(manager: ConnectionManager):
    message_payload = {"type": "chat", "sender": "System", "message": "Test"}
    # No connections, should not raise error
    await manager.broadcast_to_group("non_existent_group", message_payload)
    # No assertion needed other than it doesn't crash

@pytest.mark.asyncio
async def test_broadcast_with_disconnected_socket_in_group(manager: ConnectionManager):
    ws_alice = MockWebSocket()
    ws_bob = MockWebSocket() # This one will be "disconnected" before send
    group_id = "test_group_7"
    user_alice = "Alice"
    user_bob = "Bob"

    await manager.connect(ws_alice, group_id, user_alice)
    await manager.connect(ws_bob, group_id, user_bob)

    ws_alice.sent_data.clear()
    ws_bob.sent_data.clear()

    # Simulate Bob's socket being closed before broadcast
    await ws_bob.close() # Sets client_disconnected = True in mock

    message_payload = {"type": "chat", "sender": "System", "message": "Important update"}
    await manager.broadcast_to_group(group_id, message_payload)

    # Alice should receive the message
    assert len(ws_alice.sent_data) == 1
    assert ws_alice.sent_data[0] == message_payload

    # Bob should not have received it, and his socket should be removed from active connections by the broadcast logic
    assert len(ws_bob.sent_data) == 0 
    assert ws_bob not in manager.active_connections.get(group_id, set())
    assert len(manager.active_connections.get(group_id, set())) == 1 # Only Alice remains