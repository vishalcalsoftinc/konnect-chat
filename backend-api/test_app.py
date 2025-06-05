import pytest
import json
from app import app as flask_app, db, User, Group # Import User and Group here

@pytest.fixture
def app(): # This fixture is correctly named 'app'
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with flask_app.app_context():
        db.create_all()

    yield flask_app # Pytest uses the name of this function 'app' as the fixture name

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app): # Correct: The client fixture depends on the 'app' fixture
    """A test client for the app."""
    return app.test_client()

# --- Test User Management ---
def test_set_username_success(client, app): # Correct: Request 'app' fixture for app_context
    response = client.post('/api/users', json={'name': 'Alice'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['userId'] == 'Alice'
    assert data['name'] == 'Alice'

    # Verify in DB
    with app.app_context(): # Correct: Use the 'app' fixture instance
        user = User.query.filter_by(name='Alice').first()
        assert user is not None
        assert user.name == 'Alice'

def test_set_existing_username(client, app): # Correct: Request 'app' fixture
    with app.app_context():
        client.post('/api/users', json={'name': 'Alice'})
    response = client.post('/api/users', json={'name': 'Alice'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['userId'] == 'Alice'
    assert 'message' in data
    assert data['message'] == "User already exists"

# Tests that don't need direct app_context can just use client
def test_set_username_missing_name(client):
    response = client.post('/api/users', json={})
    assert response.status_code == 400
    # ... (rest of assertions)

def test_set_username_empty_name(client):
    response = client.post('/api/users', json={'name': '  '})
    assert response.status_code == 400
    # ... (rest of assertions)


# --- Test Group Management ---
def test_create_group_success(client, app): # Correct: Request 'app' fixture
    with app.app_context():
        client.post('/api/users', json={'name': 'Charlie'})

    response = client.post('/api/groups', json={'groupName': 'Test Group', 'creatorName': 'Charlie'})
    assert response.status_code == 201
    data = response.get_json()
    group_id = data['groupId']
    # ... (rest of assertions for response data)

    with app.app_context(): # Correct: Use the 'app' fixture instance
        group = Group.query.get(group_id)
        assert group is not None
        # ... (rest of DB assertions)
        charlie = User.query.filter_by(name='Charlie').first()
        assert charlie in group.members


def test_create_group_missing_fields(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'David'})
    response = client.post('/api/groups', json={'creatorName': 'David'})
    assert response.status_code == 400
    # ...

def test_create_group_empty_group_name(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Eve'})
    response = client.post('/api/groups', json={'groupName': ' ', 'creatorName': 'Eve'})
    assert response.status_code == 400
    # ...

def test_create_group_creator_not_found(client):
    response = client.post('/api/groups', json={'groupName': 'New Group', 'creatorName': 'NonExistentUser'})
    assert response.status_code == 404
    # ...

def test_get_groups_empty(client):
    response = client.get('/api/groups')
    assert response.status_code == 200
    assert response.get_json() == []

def test_get_groups_with_data(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Frank'})
        client.post('/api/groups', json={'groupName': 'Group1', 'creatorName': 'Frank'})
        client.post('/api/groups', json={'groupName': 'Group2', 'creatorName': 'Frank'})

    response = client.get('/api/groups')
    assert response.status_code == 200
    # ...

def test_join_group_success(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Grace'})
        client.post('/api/users', json={'name': 'Heidi'})
        group_res = client.post('/api/groups', json={'groupName': 'Community', 'creatorName': 'Grace'})
        group_id = group_res.get_json()['groupId']

    response = client.post(f'/api/groups/{group_id}/join', json={'userName': 'Heidi'})
    assert response.status_code == 200
    # ...

    with app.app_context(): # Correct
        group = Group.query.get(group_id)
        assert group is not None
        heidi = User.query.filter_by(name='Heidi').first()
        assert heidi is not None
        assert heidi in group.members

def test_join_group_already_member(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Grace'})
        group_res = client.post('/api/groups', json={'groupName': 'Community', 'creatorName': 'Grace'})
        group_id = group_res.get_json()['groupId']

    response = client.post(f'/api/groups/{group_id}/join', json={'userName': 'Grace'})
    assert response.status_code == 200
    # ...

def test_join_group_group_not_found(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Ivan'})
    response = client.post('/api/groups/nonexistentgroup/join', json={'userName': 'Ivan'})
    assert response.status_code == 404

def test_join_group_user_not_found(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Judy'})
        group_res = client.post('/api/groups', json={'groupName': 'Inner Circle', 'creatorName': 'Judy'})
        group_id = group_res.get_json()['groupId']

    response = client.post(f'/api/groups/{group_id}/join', json={'userName': 'Mallory'})
    assert response.status_code == 404

def test_join_group_missing_username(client, app): # Correct
    with app.app_context():
        client.post('/api/users', json={'name': 'Oscar'})
        group_res = client.post('/api/groups', json={'groupName': 'Study Group', 'creatorName': 'Oscar'})
        group_id = group_res.get_json()['groupId']

    response = client.post(f'/api/groups/{group_id}/join', json={})
    assert response.status_code == 400