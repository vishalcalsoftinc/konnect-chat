import pytest
import json
from app import app as flask_app # Import your Flask app instance

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # You can add test-specific configurations here if needed
    # For example, using a test-specific database
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(autouse=True)
def clear_data_stores():
    """Clears in-memory data stores before each test."""
    from app import users, groups # Import the actual data stores
    users.clear()
    groups.clear()
    yield # This allows the test to run, then cleanup happens if needed after yield

# --- Test User Management ---
def test_set_username_success(client):
    """Test setting a username successfully."""
    response = client.post('/api/users', json={'name': 'Alice'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['userId'] == 'Alice'
    assert data['name'] == 'Alice'
    from app import users
    assert 'Alice' in users

def test_set_username_missing_name(client):
    """Test setting username with missing name field."""
    response = client.post('/api/users', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Name is required'

def test_set_username_empty_name(client):
    """Test setting username with an empty name string."""
    response = client.post('/api/users', json={'name': '  '})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Name cannot be empty'

# --- Test Group Management ---
def test_create_group_success(client):
    """Test creating a group successfully."""
    # First, create a user
    client.post('/api/users', json={'name': 'Charlie'})

    response = client.post('/api/groups', json={'groupName': 'Test Group', 'creatorName': 'Charlie'})
    assert response.status_code == 201
    data = response.get_json()
    assert 'groupId' in data
    assert data['groupName'] == 'Test Group'
    assert data['creatorName'] == 'Charlie'
    from app import groups
    assert data['groupId'] in groups
    assert groups[data['groupId']]['creator'] == 'Charlie'
    assert 'Charlie' in groups[data['groupId']]['members']

def test_create_group_missing_fields(client):
    """Test creating a group with missing fields."""
    client.post('/api/users', json={'name': 'David'})
    response = client.post('/api/groups', json={'creatorName': 'David'}) # Missing groupName
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'groupName and creatorName are required' # Adjust if your error message is different

def test_create_group_empty_group_name(client):
    """Test creating a group with an empty group name."""
    client.post('/api/users', json={'name': 'Eve'})
    response = client.post('/api/groups', json={'groupName': ' ', 'creatorName': 'Eve'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Group name cannot be empty'
    
def test_create_group_creator_not_found(client):
    """Test creating a group when the creator does not exist."""
    response = client.post('/api/groups', json={'groupName': 'New Group', 'creatorName': 'NonExistentUser'})
    assert response.status_code == 404 # Assuming 404 for user not found
    data = response.get_json()
    assert 'error' in data
    assert "User 'NonExistentUser' not found" in data['error']

def test_get_groups_empty(client):
    """Test getting groups when no groups exist."""
    response = client.get('/api/groups')
    assert response.status_code == 200
    data = response.get_json()
    assert data == []

def test_get_groups_with_data(client):
    """Test getting groups when groups exist."""
    client.post('/api/users', json={'name': 'Frank'})
    client.post('/api/groups', json={'groupName': 'Group1', 'creatorName': 'Frank'})
    client.post('/api/groups', json={'groupName': 'Group2', 'creatorName': 'Frank'})

    response = client.get('/api/groups')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert any(g['groupName'] == 'Group1' for g in data)
    assert any(g['groupName'] == 'Group2' for g in data)

def test_join_group_success(client):
    """Test a user joining a group successfully."""
    client.post('/api/users', json={'name': 'Grace'})
    client.post('/api/users', json={'name': 'Heidi'})
    group_res = client.post('/api/groups', json={'groupName': 'Community', 'creatorName': 'Grace'})
    group_id = group_res.get_json()['groupId']

    response = client.post(f'/api/groups/{group_id}/join', json={'userName': 'Heidi'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == "User 'Heidi' joined group 'Community'"
    from app import groups
    assert 'Heidi' in groups[group_id]['members']

def test_join_group_group_not_found(client):
    """Test joining a non-existent group."""
    client.post('/api/users', json={'name': 'Ivan'})
    response = client.post('/api/groups/nonexistentgroup/join', json={'userName': 'Ivan'})
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Group not found'

def test_join_group_user_not_found(client):
    """Test joining a group with a non-existent user."""
    client.post('/api/users', json={'name': 'Judy'})
    group_res = client.post('/api/groups', json={'groupName': 'Inner Circle', 'creatorName': 'Judy'})
    group_id = group_res.get_json()['groupId']

    response = client.post(f'/api/groups/{group_id}/join', json={'userName': 'Mallory'}) # Mallory not created
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert "User 'Mallory' not found" in data['error']

def test_join_group_missing_username(client):
    """Test joining a group without providing a username."""
    client.post('/api/users', json={'name': 'Oscar'})
    group_res = client.post('/api/groups', json={'groupName': 'Study Group', 'creatorName': 'Oscar'})
    group_id = group_res.get_json()['groupId']
    
    response = client.post(f'/api/groups/{group_id}/join', json={}) # Missing userName
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == "userName is required to join a group"