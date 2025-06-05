import React, { useState, useEffect, useRef } from 'react';
import './ChatWindow.css'; // We'll create this CSS file

// Props:
// - groupId: string
// - userName: string (current user)
// - messages: array of message objects [{ sender, message, type, (optional) id }]
// - onSendMessage: function to call when user sends a message: (messageText) => void
function ChatWindow({ groupId, userName, messages, onSendMessage }) {
  const [newMessage, setNewMessage] = useState('');
  const messagesEndRef = useRef(null); // To auto-scroll to the bottom

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll to bottom whenever messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    onSendMessage(newMessage.trim());
    setNewMessage('');
  };

  return (
    <div className="chat-window">
      <h2>Group: {groupId}</h2> {/* You might pass groupName instead/as well */}
      <div className="messages-list">
        {messages.map((msg, index) => (
          <div
            key={msg.id || index} // Prefer a unique msg.id from backend if available
            className={`message-item ${
              msg.type === 'system'
                ? 'system-message'
                : msg.sender === userName
                ? 'my-message'
                : 'other-message'
            }`}
          >
            {msg.type !== 'system' && <span className="sender-name">{msg.sender}: </span>}
            <span className="message-text">{msg.message}</span>
          </div>
        ))}
        <div ref={messagesEndRef} /> {/* Invisible element to scroll to */}
      </div>
      <form onSubmit={handleSubmit} className="message-input-form">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Type your message..."
          autoFocus
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}

export default ChatWindow;