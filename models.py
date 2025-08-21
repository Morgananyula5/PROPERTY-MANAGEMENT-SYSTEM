from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  # ✅ Added

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # "Resident" or "Manager"


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    sub_county = db.Column(db.String(255), nullable=False)
    landmarks = db.Column(db.Text, nullable=False)

    # Availability options (9-5, Full-time, Part-time)
    availability = db.Column(db.String(20), nullable=False)

    viewing_schedule = db.Column(db.String(255), nullable=False)
    features = db.Column(db.Text, nullable=False)  # Store features & prices as JSON string
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to manager


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_role = db.Column(db.String(50), nullable=False)  # 'Resident' or 'Manager'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    property = db.relationship('Property', backref=db.backref('messages', lazy=True))
    sender = db.relationship('User', backref=db.backref('messages', lazy=True))

    def __init__(self, property_id, sender_id, sender_role, message):
        self.property_id = property_id
        self.sender_id = sender_id
        self.sender_role = sender_role
        self.message = message
