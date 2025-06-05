from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse # Optional: for a simple test page
from typing import Dict, List, Set

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        # Structure: { "group_id": {websocket_connection1, websocket_connection2} }
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_id: str, user_name: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = set()
        self.active_connections[group_id].add(websocket)
        # Announce user joining (optional, but good for UX)
        await self.broadcast_to_group(group_id, {"type": "system", "message": f"User '{user_name}' joined the chat."}, exclude_self=None)
        print(f"User '{user_name}' connected to group '{group_id}'. Connections in group: {len(self.active_connections[group_id])}")


    def disconnect(self, websocket: WebSocket, group_id: str, user_name: str):
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)
            print(f"User '{user_name}' disconnected from group '{group_id}'. Connections in group: {len(self.active_connections[group_id])}")
            if not self.active_connections[group_id]: # If group is empty, remove it
                del self.active_connections[group_id]
                print(f"Group '{group_id}' is now empty and removed.")
            # Announce user leaving (optional)
            # Note: We cannot broadcast through the 'websocket' that just disconnected.
            # So, this broadcast will go to remaining members.
            # For this to work reliably after disconnect, the broadcast needs to happen
            # before the actual removal, or triggered by it.
            # For simplicity, we might skip the "left" message or send it before remove.
            # Let's try sending it to the remaining members:
            # await self.broadcast_to_group(group_id, f"User '{user_name}' left the chat.", exclude_self=None) # This needs to be async if used

    async def broadcast_to_group(self, group_id: str, message_payload: dict, exclude_self: WebSocket = None):
        if group_id in self.active_connections:
            disconnected_sockets = set()
            for connection in self.active_connections[group_id]:
                if connection is not exclude_self:
                    try:
                        await connection.send_json(message_payload)
                    except RuntimeError as e: # Handles cases like sending to a closed socket
                        print(f"Error sending to a socket: {e}. Marking for removal.")
                        disconnected_sockets.add(connection)
            
            # Clean up any sockets that failed during broadcast
            if disconnected_sockets:
                self.active_connections[group_id] -= disconnected_sockets
                print(f"Cleaned up {len(disconnected_sockets)} disconnected sockets from group {group_id}")


manager = ConnectionManager()

@app.websocket("/ws/{group_id}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, group_id: str, user_name: str):
    await manager.connect(websocket, group_id, user_name)
    try:
        while True:
            data = await websocket.receive_json() # Expecting JSON messages like {"message": "Hello"}
            print(f"Received from {user_name} in {group_id}: {data}")
            
            message_payload = {
                "type": "chat",
                "sender": user_name,
                "groupId": group_id,
                "message": data.get("message", "") # Get message content
            }
            await manager.broadcast_to_group(group_id, message_payload) # No exclude_self

    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id, user_name)
        # Announce user leaving (if not handled in disconnect method)
        await manager.broadcast_to_group(group_id, {"type": "system", "message": f"User '{user_name}' left the chat."}, exclude_self=None) # exclude_self=None as the socket is already gone
        print(f"User '{user_name}' connection closed for group '{group_id}'.")
    except Exception as e:
        print(f"Error in websocket_endpoint for {user_name} in {group_id}: {e}")
        manager.disconnect(websocket, group_id, user_name) # Ensure disconnect on other errors too
        # Optionally broadcast a generic error or user left message


# Optional: A simple HTML page to test WebSocket from browser console
html_test_page = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat Test</h1>
        <p>Group ID: <input type="text" id="groupId" value="testgroup123"></p>
        <p>User Name: <input type="text" id="userName" value="testuser"></p>
        <button onclick="connect()">Connect</button>
        <hr>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws;
            function connect() {
                var groupId = document.getElementById("groupId").value;
                var userName = document.getElementById("userName").value;
                if (!groupId || !userName) {
                    alert("Group ID and User Name are required!");
                    return;
                }
                ws = new WebSocket(`ws://localhost:8000/ws/${groupId}/${userName}`);
                ws.onopen = function(event) {
                    var item = document.createElement('li');
                    item.textContent = "Connected to WebSocket!";
                    document.getElementById('messages').appendChild(item);
                };
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = JSON.parse(event.data);
                    if (content.type === "system") {
                        message.textContent = `SYSTEM: ${content.message}`;
                    } else {
                        message.textContent = `${content.sender}: ${content.message}`;
                    }
                    messages.appendChild(message);
                    window.scrollTo(0, document.body.scrollHeight);
                };
                ws.onerror = function(event) {
                    var item = document.createElement('li');
                    item.style.color = 'red';
                    item.textContent = "WebSocket error observed: " + event;
                    document.getElementById('messages').appendChild(item);
                };
                ws.onclose = function(event) {
                    var item = document.createElement('li');
                    item.textContent = "Disconnected from WebSocket. Reason: " + event.reason + " Code: " + event.code;
                    document.getElementById('messages').appendChild(item);
                    ws = null; // Clear ws variable
                };
            }
            function sendMessage(event) {
                if (!ws) {
                    alert("Not connected. Please connect first.");
                    event.preventDefault();
                    return;
                }
                var input = document.getElementById("messageText")
                ws.send(JSON.stringify({ "message": input.value })) // Send as JSON
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get_test_page():
    return HTMLResponse(html_test_page)