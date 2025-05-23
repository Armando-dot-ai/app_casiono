# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 22:40:50 2025

@author: arman
"""

from flask import Flask, request, jsonify
from models import db, User, Friend, FriendRequest, Message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    points = 200

    if not username or not password:
        return jsonify({"error": "Pseudo et mot de passe requis"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Utilisateur déjà existant"}), 409

    new_user = User(username=username, password=password, points = points)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": f"Utilisateur '{username}' créé avec succès",
        "id": new_user.id,
        "points": new_user.points
    }), 201



@app.route('/login', methods = ['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username = username, password = password).first()

    if not user:
        return jsonify({"error" : "Identifiant ou mot de passe incorrect"}), 401
    else:
        return jsonify({
        "message": f"Bienvenue {user.username}, vous avez {user.points} points !!",
        "id": user.id,
        "points": user.points
    }), 200



@app.route('/add_friend', methods=['POST'])
def add_friend():
    user_id = request.json.get('user_id')
    friend_username = request.json.get('friend_username')
    friend = User.query.filter_by(username=friend_username).first()
    if not friend:
        return jsonify({"error": "Ami introuvable"}), 404
    new_friend = Friend(user_id=user_id, friend_id=friend.id)
    db.session.add(new_friend)
    db.session.commit()
    return jsonify({"message": "Ami ajouté"})


@app.route('/search_friend', methods=['POST'])
def search_friend():
    searched_friend = request.json.get('searched_friend')
    
    matching_users = User.query.filter(User.username.like(f"%{searched_friend}%")).all()

    if not matching_users:
        return jsonify([])

    result = []
    for user in matching_users:
        result.append({
            "id": user.id,
            "username": user.username,
            "points": user.points
        })

    return jsonify(result)
    

@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    data = request.get_json()
    sender_id = data.get("sender_id")
    receiver_username = data.get("receiver_username")

    receiver = User.query.filter_by(username=receiver_username).first()
    if not receiver:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    already_friend = Friend.query.filter_by(user_id=sender_id, friend_id=receiver.id).first()
    if already_friend:
        return jsonify({"error": "Vous êtes déjà amis."}), 409

    reverse_request = FriendRequest.query.filter_by(sender_id=receiver.id, receiver_id=sender_id, status='pending').first()
    if reverse_request:
        reverse_request.status = 'accepted'
        db.session.add(Friend(user_id=sender_id, friend_id=receiver.id))
        db.session.add(Friend(user_id=receiver.id, friend_id=sender_id))
        db.session.commit()
        return jsonify({"message": "Demande croisée détectée : amitié créée automatiquement."}), 200

    # Sinon, créer une nouvelle demande
    existing_request = FriendRequest.query.filter_by(sender_id=sender_id, receiver_id=receiver.id).first()
    if existing_request:
        return jsonify({"error": "Demande déjà envoyée."}), 409

    new_request = FriendRequest(sender_id=sender_id, receiver_id=receiver.id)
    db.session.add(new_request)
    db.session.commit()
    return jsonify({"message": "Demande envoyée."}), 201



@app.route('/pending_requests', methods=['POST'])
def pending_requests():
    data = request.get_json()
    user_id = data.get("user_id")

    requests_received = FriendRequest.query.filter_by(receiver_id=user_id, status='pending').all()

    results = []
    for req in requests_received:
        sender = User.query.get(req.sender_id)
        results.append({
            "request_id": req.id,
            "sender_id": req.sender_id,
            "sender_username": sender.username
        })

    return jsonify(results)
    


@app.route('/accept_request', methods=['POST'])
def accept_request():
    data = request.get_json()
    request_id = data.get("request_id")

    friend_request = FriendRequest.query.get(request_id)
    if not friend_request or friend_request.status != 'pending':
        return jsonify({"error": "Request not found or already handled"}), 404

    sender_id = friend_request.sender_id
    receiver_id = friend_request.receiver_id

    friend_request.status = 'accepted'

    already_1 = Friend.query.filter_by(user_id=receiver_id, friend_id=sender_id).first()
    already_2 = Friend.query.filter_by(user_id=sender_id, friend_id=receiver_id).first()

    if not already_1:
        db.session.add(Friend(user_id=receiver_id, friend_id=sender_id))
    if not already_2:
        db.session.add(Friend(user_id=sender_id, friend_id=receiver_id))

    db.session.commit()
    return jsonify({"message": "Friendship established successfully"})



@app.route('/relationship_status', methods=['POST'])
def relationship_status():
    data = request.get_json()
    user_id = data.get('user_id')
    other_user_id = data.get('other_user_id')

    is_friend = Friend.query.filter_by(user_id=user_id, friend_id=other_user_id).first()
    if is_friend:
        return jsonify({"status": "friend"})

    pending_request = FriendRequest.query.filter_by(sender_id=user_id, receiver_id=other_user_id, status='pending').first()
    if pending_request:
        return jsonify({"status": "pending"})

    return jsonify({"status": "none"})


@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    message = data.get('message')

    if not message or not username:
        return jsonify({"error": "Message or username missing"}), 400

    new_message = Message(user_id=user_id, username=username, message=message)
    db.session.add(new_message)
    db.session.commit()
    return jsonify({"message": "Message sent"}), 201

@app.route('/get_messages', methods=['GET'])
def get_messages():
    messages = Message.query.order_by(Message.id.desc()).limit(50).all()
    messages.reverse()  # pour afficher du plus ancien au plus récent
    result = [{"username": m.username, "message": m.message} for m in messages]
    return jsonify(result)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=10000, debug=True)
