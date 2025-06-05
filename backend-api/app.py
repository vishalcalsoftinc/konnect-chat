from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid # For generating unique IDs later for groups

app = Flask(__name__)
CORS(app) # Enable CORS for all routes and origins for now

# In-memory data stores (for now)
users = {} # Store users: { "userId": "name" } -> simple, userId can be name
groups = {} # Store groups: { "groupId": {"name": "groupName", "members": set()} }

@app.route('/')
def home():
    return "Welcome to the Konnect Chat API!"

# --- User Management ---
@app.route('/api/users', methods=['POST'])
def set_username():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Name is required"}), 400

    name = data['name'].strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    # For simplicity, we'll use the name as the userId.
    # In a real app, you might want to ensure uniqueness or generate a separate ID.
    # For now, if name exists, we can just "re-confirm" it.
    users[name] = name # Storing name as key and value for simplicity
    print(f"Users: {users}") # For debugging
    return jsonify({"userId": name, "name": name}), 201

# --- Group Management ---
@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.get_json()
    if not data or 'groupName' not in data or 'creatorName' not in data:
        return jsonify({"error": "groupName and creatorName are required"}), 400

    group_name = data['groupName'].strip()
    creator_name = data['creatorName'].strip()

    if not group_name:
        return jsonify({"error": "Group name cannot be empty"}), 400
    if not creator_name:
        return jsonify({"error": "Creator name cannot be empty"}), 400
    
    if creator_name not in users:
        # Or auto-create user? For now, require user to be "set" first.
        return jsonify({"error": f"User '{creator_name}' not found. Please set username first."}), 404

    group_id = str(uuid.uuid4())[:8] # Generate a short unique ID
    groups[group_id] = {
        "name": group_name,
        "creator": creator_name,
        "members": {creator_name} # Creator is the first member
    }
    print(f"Groups: {groups}") # For debugging
    return jsonify({"groupId": group_id, "groupName": group_name, "creatorName": creator_name}), 201

@app.route('/api/groups', methods=['GET'])
def get_groups():
    # Return a list of groups with their IDs and names
    group_list = [{"groupId": gid, "groupName": ginfo["name"]} for gid, ginfo in groups.items()]
    return jsonify(group_list), 200

# Placeholder for joining a group - this might be handled more by WebSocket logic
# or we can have an explicit API call to register interest/membership
@app.route('/api/groups/<group_id>/join', methods=['POST'])
def join_group(group_id):
    data = request.get_json()
    if 'userName' not in data:
        return jsonify({"error": "userName is required to join a group"}), 400
    
    user_name = data['userName']

    if group_id not in groups:
        return jsonify({"error": "Group not found"}), 404
    
    if user_name not in users:
         # Or auto-create user? For now, require user to be "set" first.
        return jsonify({"error": f"User '{user_name}' not found. Please set username first."}), 404

    groups[group_id]["members"].add(user_name)
    print(f"Group {group_id} members: {groups[group_id]['members']}") # For debugging
    return jsonify({"message": f"User '{user_name}' joined group '{groups[group_id]['name']}'"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)