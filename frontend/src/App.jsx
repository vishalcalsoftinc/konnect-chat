import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import SetNameForm from './components/SetNameForm';
import GroupControls from './components/GroupControls';
import ChatWindow from './components/ChatWindow'; // Import ChatWindow
import './App.css';

const API_URL = 'http://localhost:5001/api';
const WS_URL = 'ws://localhost:8000/ws'; // Your FastAPI WebSocket URL

function App() {
  const [userName, setUserName] = useState(localStorage.getItem('konnect_userName') || '');
  const [userId, setUserId] = useState(localStorage.getItem('konnect_userId') || '');
  const [currentGroup, setCurrentGroup] = useState(null); // { id: 'groupId', name: 'groupName' }
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState('');
  const [isConnected, setIsConnected] = useState(false); // Track WebSocket connection status

  const ws = useRef(null);

  // Store username in localStorage
  useEffect(() => {
    if (userName) {
      localStorage.setItem('konnect_userName', userName);
      localStorage.setItem('konnect_userId', userName);
    } else {
      localStorage.removeItem('konnect_userName');
      localStorage.removeItem('konnect_userId');
    }
  }, [userName]);

  // WebSocket connection logic
  useEffect(() => {
    if (!currentGroup || !userName) {
      if (ws.current) {
        console.log("Closing WebSocket connection as no group/user is active.");
        ws.current.close();
        ws.current = null;
        setIsConnected(false);
      }
      return;
    }

    // If already connected or connecting, don't create a new one
    if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
        // If connected to a different group, close old and open new
        if (ws.current.url !== `${WS_URL}/${currentGroup.id}/${userName}`) {
            console.log(`Switching WebSocket from ${ws.current.url} to group ${currentGroup.id}`);
            ws.current.close();
            // The rest will be handled by re-running this effect due to currentGroup change
        } else {
            console.log("WebSocket already connected to the correct group.");
            return;
        }
    }


    console.log(`Attempting to connect WebSocket to: ${WS_URL}/${currentGroup.id}/${userName}`);
    const socket = new WebSocket(`${WS_URL}/${currentGroup.id}/${userName}`);
    ws.current = socket;

    socket.onopen = () => {
      console.log(`WebSocket connected to group: ${currentGroup.id}`);
      setIsConnected(true);
      setError(''); // Clear previous connection errors
      setMessages([]); // Clear messages from previous group
    };

    socket.onmessage = (event) => {
      try {
        const receivedMessage = JSON.parse(event.data);
        console.log("Message received:", receivedMessage);
        // Add a unique ID to messages on the client-side if backend doesn't provide one
        // This is for React keys. A real backend message ID is better.
        setMessages((prevMessages) => [...prevMessages, { ...receivedMessage, id: Date.now() + Math.random() }]);
      } catch (e) {
        console.error("Error parsing message or updating state:", e);
      }
    };

    socket.onerror = (event) => {
      console.error("WebSocket error:", event);
      setError(`WebSocket connection error. Please try rejoining the group or check server.`);
      setIsConnected(false);
    };

    socket.onclose = (event) => {
      console.log("WebSocket disconnected.", event.reason, event.code);
      setIsConnected(false);
      // Optionally, try to reconnect or inform the user
      // For now, if not a clean close initiated by user, show error
      if (!event.wasClean && currentGroup) { // only show error if we expected to be connected
          setError('WebSocket connection closed unexpectedly. Try rejoining.');
      }
      // ws.current = null; // Already handled if user leaves group. Here, it's a server-side or network close.
    };

    // Cleanup function: close WebSocket when component unmounts or dependencies change
    return () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("Cleaning up WebSocket connection for group:", currentGroup?.id);
        socket.close(1000, "Client unmounting or changing group");
      }
      ws.current = null;
      setIsConnected(false);
    };
  }, [currentGroup, userName]); // Re-run effect if currentGroup or userName changes


  const handleNameSet = async (name) => {
    // ... (same as before)
    try {
      const response = await axios.post(`${API_URL}/users`, { name });
      if (response.status === 201 || response.status === 200) {
        setUserName(response.data.name);
        setUserId(response.data.userId);
        setError('');
      } else {
        throw new Error(response.data.error || 'Failed to set name.');
      }
    } catch (err) {
      console.error("Error setting name:", err);
      const errorMessage = err.response?.data?.error || err.message || 'Server error setting name.';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  const handleCreateGroup = async (groupName) => {
    // ... (same as before, but ensure setCurrentGroup triggers WebSocket useEffect)
    if (!userName) {
      setError("Please set your name first.");
      throw new Error("User name not set.");
    }
    try {
      const response = await axios.post(`${API_URL}/groups`, { groupName, creatorName: userName });
      if (response.status === 201) {
        // Important: set currentGroup to trigger useEffect for WebSocket
        setCurrentGroup({ id: response.data.groupId, name: response.data.groupName });
        setError('');
      } else {
        throw new Error(response.data.error || 'Failed to create group.');
      }
    } catch (err) {
      console.error("Error creating group:", err);
      const errorMessage = err.response?.data?.error || err.message || 'Server error creating group.';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  const handleJoinGroup = async (groupId) => {
    // ... (same as before, ensure setCurrentGroup triggers WebSocket useEffect)
    if (!userName) {
      setError("Please set your name first.");
      throw new Error("User name not set.");
    }
    try {
      const joinResponse = await axios.post(`${API_URL}/groups/${groupId}/join`, { userName });
      if (joinResponse.status !== 200) {
          throw new Error(joinResponse.data.error || 'Failed to join group via API.');
      }
      // Important: set currentGroup to trigger useEffect for WebSocket
      setCurrentGroup({ id: groupId, name: joinResponse.data.message.includes("group '") ? joinResponse.data.message.split("group '")[1].split("'")[0] : groupId });
      setError('');
    } catch (err) {
      console.error("Error joining group:", err);
      const errorMessage = err.response?.data?.error || err.message || 'Server error joining group.';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  const handleSendMessage = (messageText) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      const messagePayload = {
        message: messageText,
        // Backend's WebSocket endpoint expects sender/group from path params,
        // but payload might be useful for other things or if backend changes.
      };
      ws.current.send(JSON.stringify(messagePayload));
    } else {
      setError("Not connected to chat server. Cannot send message.");
      console.error("WebSocket is not connected or not ready.");
    }
  };

  const handleLeaveGroup = () => {
    // currentGroup change will trigger useEffect to close WebSocket
    setCurrentGroup(null);
    setMessages([]); // Clear messages
    setError(''); // Clear any errors
  };


  // Conditional rendering logic
  if (!userName) {
    return (
      <div className="App">
        <h1>Konnect Chat</h1>
        {error && <p className="error-message app-error">{error}</p>}
        <SetNameForm onNameSet={handleNameSet} />
      </div>
    );
  }

  if (!currentGroup) {
    return (
      <div className="App">
        <h1>Konnect Chat</h1>
        <p>Welcome, {userName}!</p>
        {error && <p className="error-message app-error">{error}</p>}
        <GroupControls onCreateGroup={handleCreateGroup} onJoinGroup={handleJoinGroup} />
      </div>
    );
  }

  return (
    <div className="App">
      <h1>Konnect Chat</h1>
      <p>User: {userName} | Group: {currentGroup.name} (ID: {currentGroup.id}) | Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
      {error && <p className="error-message app-error">{error}</p>}
      <ChatWindow
        groupId={currentGroup.id}
        userName={userName}
        messages={messages}
        onSendMessage={handleSendMessage}
      />
      <button onClick={handleLeaveGroup} style={{marginTop: "10px"}}>Leave Group</button>
    </div>
  );
}

export default App;