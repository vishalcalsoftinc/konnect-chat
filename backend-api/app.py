from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)
CORS(app)

# --- Database Configuration ---
# Replace with your actual PostgreSQL connection string
# Format: postgresql://username:password@host:port/database_name
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://konnect_user:your_strong_password@localhost:5432/konnect_chat_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress a warning

db = SQLAlchemy(app)

# --- Database Models ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # Using name as a unique identifier for simplicity, as in PRD.
    # In a real app, you'd likely have a separate, non-user-facing unique ID.
    name = db.Column(db.String(80), unique=True, nullable=False)
    
    # Relationship (optional for now, but good for future)
    # created_groups = db.relationship('Group', backref='creator', lazy=True)

    def __repr__(self):
        return f'<User {self.name}>'

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())[:8]) # Short UUID
    name = db.Column(db.String(120), nullable=False)
    creator_user_name = db.Column(db.String(80), db.ForeignKey('users.name'), nullable=False) # Link to User's name

    # Relationship for members (many-to-many)
    # This will be handled via an association table if we track all members explicitly in DB
    # For now, creator is stored. WebSocket server might handle live members.
    # If we want persistent membership, we need a group_members table.

    def __repr__(self):
        return f'<Group {self.name}>'

# Association table for many-to-many relationship between users and groups
group_members = db.Table('group_members',
    db.Column('user_name', db.String(80), db.ForeignKey('users.name'), primary_key=True),
    db.Column('group_id', db.String(36), db.ForeignKey('groups.id'), primary_key=True)
)
# Add relationship to User and Group models if you want to easily access members/groups
User.groups = db.relationship('Group', secondary=group_members, lazy='subquery',
                              backref=db.backref('members', lazy=True))


# Remove old in-memory data stores:
# users = {}
# groups = {}

@app.route('/')
def home():
    return "Welcome to the Konnect Chat API! (DB Connected)"

# --- User Management ---
@app.route('/api/users', methods=['POST'])
def set_username():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Name is required"}), 400

    name = data['name'].strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    existing_user = User.query.filter_by(name=name).first()
    if existing_user:
        return jsonify({"userId": existing_user.name, "name": existing_user.name, "message": "User already exists"}), 200
    
    new_user = User(name=name)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"userId": new_user.name, "name": new_user.name}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not create user", "details": str(e)}), 500


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
    
    creator = User.query.filter_by(name=creator_name).first()
    if not creator:
        return jsonify({"error": f"User '{creator_name}' not found. Please set username first."}), 404

    new_group = Group(name=group_name, creator_user_name=creator.name)
    # Add creator to the group_members association
    new_group.members.append(creator)

    try:
        db.session.add(new_group)
        db.session.commit()
        return jsonify({"groupId": new_group.id, "groupName": new_group.name, "creatorName": new_group.creator_user_name}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating group: {e}") # Log the error
        return jsonify({"error": "Could not create group", "details": str(e)}), 500


@app.route('/api/groups', methods=['GET'])
def get_groups():
    all_groups = Group.query.all()
    group_list = [{"groupId": group.id, "groupName": group.name, "creatorName": group.creator_user_name} for group in all_groups]
    return jsonify(group_list), 200


@app.route('/api/groups/<group_id>/join', methods=['POST'])
def join_group(group_id):
    data = request.get_json()
    if 'userName' not in data:
        return jsonify({"error": "userName is required to join a group"}), 400
    
    user_name = data['userName'].strip()
    if not user_name:
        return jsonify({"error": "User name cannot be empty"}), 400

    user = User.query.filter_by(name=user_name).first()
    if not user:
        return jsonify({"error": f"User '{user_name}' not found. Please set username first."}), 404

    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return jsonify({"error": "Group not found"}), 404
    
    if user in group.members:
        return jsonify({"message": f"User '{user_name}' is already a member of group '{group.name}'"}), 200

    try:
        group.members.append(user)
        db.session.commit()
        return jsonify({"message": f"User '{user_name}' joined group '{group.name}'"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error joining group: {e}") # Log the error
        return jsonify({"error": "Could not join group", "details": str(e)}), 500

# (Optional) Endpoint to view members of a group for debugging
@app.route('/api/groups/<group_id>/members', methods=['GET'])
def get_group_members(group_id):
    group = Group.query.filter_by(id=group_id).first()
    if not group:
        return jsonify({"error": "Group not found"}), 404
    
    member_list = [member.name for member in group.members]
    return jsonify({"groupId": group.id, "groupName": group.name, "members": member_list}), 200


if __name__ == '__main__':
    # Create database tables if they don't exist
    # In a production app, you'd use migrations (e.g., Flask-Migrate with Alembic)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)