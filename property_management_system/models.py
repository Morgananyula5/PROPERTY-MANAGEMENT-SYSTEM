from flask_sqlalchemy import SQLAlchemy

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

    def __init__(self, name, property_type, status, phone, email, description, location, sub_county, landmarks, availability, viewing_schedule, features):
        self.name = name
        self.property_type = property_type
        self.status = status
        self.phone = phone
        self.email = email
        self.description = description
        self.location = location
        self.sub_county = sub_county
        self.landmarks = landmarks
        self.availability = availability
        self.viewing_schedule = viewing_schedule
        self.features = features
