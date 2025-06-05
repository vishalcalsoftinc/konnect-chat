import React, { useState } from 'react';

// Prop: onNameSet (function to call when name is submitted)
function SetNameForm({ onNameSet }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name cannot be empty.');
      return;
    }
    setError('');
    // Here we would call the API, for now, just pass the name up
    try {
      // For now, we assume onNameSet handles API call and success/failure
      await onNameSet(name.trim());
      // No need to clear name here, App component will hide this form
    } catch (apiError) {
      setError(apiError.message || 'Failed to set name. Please try again.');
    }
  };

  return (
    <div className="set-name-form">
      <h2>Set Your Display Name</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter your name"
          required
        />
        <button type="submit">Set Name</button>
      </form>
      {error && <p className="error-message">{error}</p>}
    </div>
  );
}

export default SetNameForm;