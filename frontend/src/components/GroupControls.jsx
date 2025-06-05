import React, { useState } from 'react';

// Props: onCreateGroup (function), onJoinGroup (function)
function GroupControls({ onCreateGroup, onJoinGroup }) {
  const [newGroupName, setNewGroupName] = useState('');
  const [joinGroupId, setJoinGroupId] = useState('');
  const [createError, setCreateError] = useState('');
  const [joinError, setJoinError] = useState('');

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) {
      setCreateError('Group name cannot be empty.');
      return;
    }
    setCreateError('');
    try {
      await onCreateGroup(newGroupName.trim());
      setNewGroupName(''); // Clear input on success
    } catch (apiError) {
      setCreateError(apiError.message || 'Failed to create group.');
    }
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    if (!joinGroupId.trim()) {
      setJoinError('Group ID cannot be empty.');
      return;
    }
    setJoinError('');
    try {
      await onJoinGroup(joinGroupId.trim());
      setJoinGroupId(''); // Clear input on success
    } catch (apiError)
    {
      setJoinError(apiError.message || 'Failed to join group. Check ID.');
    }
  };

  return (
    <div className="group-controls">
      <div className="create-group">
        <h3>Create New Group</h3>
        <form onSubmit={handleCreate}>
          <input
            type="text"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
            placeholder="New group name"
          />
          <button type="submit">Create Group</button>
        </form>
        {createError && <p className="error-message">{createError}</p>}
      </div>

      <hr />

      <div className="join-group">
        <h3>Join Existing Group</h3>
        <form onSubmit={handleJoin}>
          <input
            type="text"
            value={joinGroupId}
            onChange={(e) => setJoinGroupId(e.target.value)}
            placeholder="Enter Group ID"
          />
          <button type="submit">Join Group</button>
        </form>
        {joinError && <p className="error-message">{joinError}</p>}
      </div>
    </div>
  );
}

export default GroupControls;