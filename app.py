from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Property
from config import Config
import os
import json
from datetime import datetime
from flask import jsonify
from flask_migrate import Migrate   # ✅ add this
from models import db  # import your db from models

app = Flask(__name__)
app.config.from_object(Config)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Custom Jinja filter to parse JSON strings
@app.template_filter('parse_json')
def parse_json(s):
    try:
        return json.loads(s) if s else []
    except json.JSONDecodeError:
        return []

db.init_app(app)

# Ensure tables are created if they don't exist
with app.app_context():
    db.create_all()

# Home route redirects to signup
@app.route('/')
def home():
    return redirect(url_for('signup'))

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role'].capitalize()

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already exists. Use a different one.", "danger")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()

        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("This email does not exist in our system.", "warning")
            return redirect(url_for('login'))

        if check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role.capitalize()
            flash("Login successful!", "success")

            if session['role'] == "Resident":
                return redirect(url_for('resident_dashboard'))
            elif session['role'] == "Manager":
                return redirect(url_for('manager_dashboard'))
        else:
            flash("Invalid login credentials. Try again.", "danger")

    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Resident Dashboard Route
@app.route('/resident_dashboard')
def resident_dashboard():
    if 'user_id' not in session or session.get('role') != 'Resident':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    properties = Property.query.all()  # Fetch all properties
    properties_data = []

    for property in properties:
        # Extract profile picture from description
        description_lines = property.description.split('\n')
        profile_picture = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), 'default-profile.png')
        if profile_picture != 'default-profile.png':
            profile_picture = f"/static/{profile_picture}"

        # Extract media paths
        media_paths = []
        for line in description_lines:
            if line.startswith('Media: '):
                media_paths = [f"/static/{path}" for path in line.split(': ')[1].split(', ') if line.split(': ')[1]] or []

        # Prepare property data for template
        property_data = {
            'id': property.id,
            'name': property.name,
            'type': property.property_type,
            'status': property.status,
            'phone': property.phone,
            'email': property.email,
            'description': description_lines[0],
            'location': property.location,
            'sub_county': property.sub_county,
            'landmarks': property.landmarks,
            'location_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Location Address: ')), ''),
            'property_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), ''),
            'amenities': next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), ''),
            'availability': property.availability,
            'features': json.loads(property.features) if property.features else [],
            'media': media_paths,
            'profile_picture': profile_picture
        }
        properties_data.append(property_data)

    return render_template('resident_dashboard.html', properties=properties_data)

# Manager Dashboard Route
@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))
    
    # Fetch the property associated with the logged-in manager
    user_id = session['user_id']
    recent_property = Property.query.filter_by(manager_id=user_id).first()
    property_data = None
    profile_picture = None
    
    if recent_property:
        # Extract profile picture from description
        description_lines = recent_property.description.split('\n')
        profile_picture = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), 'default-profile.png')
        if profile_picture != 'default-profile.png':
            profile_picture = f"/static/{profile_picture}"
        
        # Extract media paths
        media_paths = []
        for line in description_lines:
            if line.startswith('Media: '):
                media_paths = [f"/static/{path}" for path in line.split(': ')[1].split(', ') if line.split(': ')[1]] or []
        
        # Prepare property data for template
        property_data = {
            'id': recent_property.id,  # Added for edit functionality
            'name': recent_property.name,
            'type': recent_property.property_type,
            'status': recent_property.status,
            'phone': recent_property.phone,
            'email': recent_property.email,
            'description': description_lines[0],  # First line is the main description
            'location': recent_property.location,
            'sub_county': recent_property.sub_county,
            'landmarks': recent_property.landmarks,
            'location_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Location Address: ')), ''),
            'property_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), ''),
            'amenities': next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), ''),
            'availability': recent_property.availability,
            'features': json.loads(recent_property.features) if recent_property.features else [],
            'media': media_paths
        }
    
    return render_template('manager_dashboard.html', profile_picture=profile_picture, property=property_data)

# Route to Add Property
@app.route('/add_property', methods=['POST'])
def add_property():
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    # Check if the manager already has a property
    user_id = session['user_id']
    existing_property = Property.query.filter_by(manager_id=user_id).first()
    if existing_property:
        flash("You have already added a property. You can only manage one property.", "danger")
        return redirect(url_for('manager_dashboard'))

    # Retrieve form data
    name = request.form['name']
    property_type = request.form['type']
    status = request.form['status']
    phone = request.form['phone']
    email = request.form['email']
    description = request.form['description']
    location = request.form['location']
    sub_county = request.form['sub_county']
    landmarks = request.form['landmarks']
    location_address = request.form['location_address']
    property_address = request.form['property_address']
    availability = request.form['availability']
    amenities = request.form['amenities']
    features = request.form.getlist('features[]')
    prices = request.form.getlist('prices[]')
    occupancy_status = request.form.getlist('status[]')

    # Handle profile picture upload
    profile_picture = request.files.get('profile_picture')
    profile_picture_path = None
    if profile_picture and profile_picture.filename:
        try:
            filename = secure_filename(profile_picture.filename)
            profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(profile_picture_path)
            profile_picture_path = f"uploads/{filename}"
            flash(f"Profile picture saved at: {profile_picture_path}", "info")
        except Exception as e:
            flash(f"Error saving profile picture: {str(e)}", "danger")
            profile_picture_path = None
    else:
        flash("No profile picture uploaded", "warning")

    # Handle media files upload
    media_files = request.files.getlist('media[]')
    media_paths = []
    if media_files:
        try:
            for media in media_files:
                if media and media.filename:
                    filename = secure_filename(media.filename)
                    media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    media.save(media_path)
                    media_paths.append(f"uploads/{filename}")
            flash(f"Media files saved: {', '.join(media_paths)}", "info")
        except Exception as e:
            flash(f"Error saving media files: {str(e)}", "danger")
            media_paths = []
    else:
        flash("No media files uploaded", "warning")

    # Combine features, prices, and status into a JSON string
    feature_price_status = [{"feature": f, "price": p, "status": s} for f, p, s in zip(features, prices, occupancy_status)]
    features_json = json.dumps(feature_price_status)

    # Combine additional details into description
    combined_description = f"{description}\nLocation Address: {location_address}\nProperty Address: {property_address}\nAmenities: {amenities}"
    if profile_picture_path:
        combined_description += f"\nProfile Picture: {profile_picture_path}"
    if media_paths:
        combined_description += f"\nMedia: {', '.join(media_paths)}"

    # Create new Property instance with all required fields
    new_property = Property(
        name=name,
        property_type=property_type,
        status=status,
        phone=phone,
        email=email,
        description=combined_description,
        location=location,
        sub_county=sub_county,
        landmarks=landmarks,
        availability=availability,
        viewing_schedule="Not specified",  # Placeholder for viewing_schedule
        features=features_json,
        manager_id=user_id
    )

    try:
        db.session.add(new_property)
        db.session.commit()
        flash("Property added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding property: {str(e)}", "danger")

    return redirect(url_for('manager_dashboard'))

# Route to Edit Property
@app.route('/edit_property/<int:property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    property = Property.query.get_or_404(property_id)

    # Ensure the property belongs to the logged-in manager
    if property.manager_id != session['user_id']:
        flash("You are not authorized to edit this property.", "danger")
        return redirect(url_for('manager_dashboard'))

    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        property_type = request.form['type']
        status = request.form['status']
        phone = request.form['phone']
        email = request.form['email']
        description = request.form['description']
        location = request.form['location']
        sub_county = request.form['sub_county']
        landmarks = request.form['landmarks']
        location_address = request.form['location_address']
        property_address = request.form['property_address']
        availability = request.form['availability']
        amenities = request.form['amenities']
        features = request.form.getlist('features[]')
        prices = request.form.getlist('prices[]')
        occupancy_status = request.form.getlist('status[]')

        # Handle profile picture upload
        profile_picture = request.files.get('profile_picture')
        profile_picture_path = None
        description_lines = property.description.split('\n')
        existing_profile_picture = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), None)
        if profile_picture and profile_picture.filename:
            try:
                filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_picture.save(profile_picture_path)
                profile_picture_path = f"uploads/{filename}"
                flash(f"Profile picture updated: {profile_picture_path}", "info")
            except Exception as e:
                flash(f"Error saving profile picture: {str(e)}", "danger")
                profile_picture_path = existing_profile_picture
        else:
            profile_picture_path = existing_profile_picture

        # Handle media files upload
        media_files = request.files.getlist('media[]')
        media_paths = []
        existing_media = []
        for line in description_lines:
            if line.startswith('Media: '):
                existing_media = line.split(': ')[1].split(', ') if line.split(': ')[1] else []
        if media_files and any(media.filename for media in media_files):
            try:
                for media in media_files:
                    if media and media.filename:
                        filename = secure_filename(media.filename)
                        media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        media.save(media_path)
                        media_paths.append(f"uploads/{filename}")
                flash(f"Media files updated: {', '.join(media_paths)}", "info")
            except Exception as e:
                flash(f"Error saving media files: {str(e)}", "danger")
                media_paths = existing_media
        else:
            media_paths = existing_media

        # Combine features, prices, and status into a JSON string
        feature_price_status = [{"feature": f, "price": p, "status": s} for f, p, s in zip(features, prices, occupancy_status)]
        features_json = json.dumps(feature_price_status)

        # Combine additional details into description
        combined_description = f"{description}\nLocation Address: {location_address}\nProperty Address: {property_address}\nAmenities: {amenities}"
        if profile_picture_path:
            combined_description += f"\nProfile Picture: {profile_picture_path}"
        if media_paths:
            combined_description += f"\nMedia: {', '.join(media_paths)}"

        # Update property instance
        property.name = name
        property.property_type = property_type
        property.status = status
        property.phone = phone
        property.email = email
        property.description = combined_description
        property.location = location
        property.sub_county = sub_county
        property.landmarks = landmarks
        property.availability = availability
        property.viewing_schedule = "Not specified"
        property.features = features_json

        try:
            db.session.commit()
            flash("Property updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating property: {str(e)}", "danger")

        return redirect(url_for('manager_dashboard'))

    # For GET request, prepare data to pre-populate the form
    description_lines = property.description.split('\n')
    profile_picture = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), 'default-profile.png')
    media_paths = []
    for line in description_lines:
        if line.startswith('Media: '):
            media_paths = line.split(': ')[1].split(', ') if line.split(': ')[1] else []

    property_data = {
        'id': property.id,
        'name': property.name,
        'type': property.property_type,
        'status': property.status,
        'phone': property.phone,
        'email': property.email,
        'description': description_lines[0],
        'location': property.location,
        'sub_county': property.sub_county,
        'landmarks': property.landmarks,
        'location_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Location Address: ')), ''),
        'property_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), ''),
        'amenities': next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), ''),
        'availability': property.availability,
        'features': json.loads(property.features) if property.features else [],
        'media': media_paths
    }

    return render_template('manager_dashboard.html', profile_picture=profile_picture, property=property_data, edit_mode=True)

# Route to Add Media
@app.route('/add_media/<int:property_id>', methods=['POST'])
def add_media(property_id):
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    property = Property.query.get_or_404(property_id)

    # Ensure the property belongs to the logged-in manager
    if property.manager_id != session['user_id']:
        flash("You are not authorized to add media to this property.", "danger")
        return redirect(url_for('manager_dashboard'))

    # Extract existing data from description
    description_lines = property.description.split('\n')
    main_description = description_lines[0]
    location_address = next((line.split(': ')[1] for line in description_lines if line.startswith('Location Address: ')), '')
    property_address = next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), '')
    amenities = next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), '')
    profile_picture_path = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), None)
    existing_media = []
    for line in description_lines:
        if line.startswith('Media: '):
            existing_media = line.split(': ')[1].split(', ') if line.split(': ')[1] else []

    # Handle new media files upload
    media_files = request.files.getlist('media[]')
    new_media_paths = []
    if media_files and any(media.filename for media in media_files):
        try:
            for media in media_files:
                if media and media.filename:
                    filename = secure_filename(media.filename)
                    media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    media.save(media_path)
                    new_media_paths.append(f"uploads/{filename}")
            flash(f"New media files added: {', '.join(new_media_paths)}", "info")
        except Exception as e:
            flash(f"Error saving media files: {str(e)}", "danger")
            return redirect(url_for('manager_dashboard'))
    else:
        flash("No media files selected.", "warning")
        return redirect(url_for('manager_dashboard'))

    # Combine existing and new media
    all_media = existing_media + new_media_paths

    # Reconstruct description with updated media
    combined_description = f"{main_description}\nLocation Address: {location_address}\nProperty Address: {property_address}\nAmenities: {amenities}"
    if profile_picture_path:
        combined_description += f"\nProfile Picture: {profile_picture_path}"
    if all_media:
        combined_description += f"\nMedia: {', '.join(all_media)}"

    # Update property description
    property.description = combined_description

    try:
        db.session.commit()
        flash("Media added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding media: {str(e)}", "danger")

    return redirect(url_for('manager_dashboard'))


# Route to Send Message
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized access'}), 401

    data = request.get_json()
    property_id = data.get('property_id')
    message = data.get('message')
    sender_id = data.get('sender_id')
    sender_role = data.get('sender_role')

    if not all([property_id, message, sender_id, sender_role]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    property = Property.query.get_or_404(property_id)
    if sender_role == 'Resident' and session['role'] != 'Resident':
        return jsonify({'success': False, 'error': 'Invalid sender role'}), 403
    if sender_role == 'Manager' and (session['role'] != 'Manager' or property.manager_id != sender_id):
        return jsonify({'success': False, 'error': 'Unauthorized to send as manager'}), 403

    new_message = Message(
        property_id=property_id,
        sender_id=sender_id,
        sender_role=sender_role,
        message=message,
        timestamp=datetime.utcnow()
    )

    try:
        db.session.add(new_message)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Route to Get Messages
@app.route('/get_messages/<int:manager_id>', methods=['GET'])
def get_messages(manager_id):
    if 'user_id' not in session or session['role'] != 'Manager' or session['user_id'] != manager_id:
        return jsonify({'success': False, 'error': 'Unauthorized access'}), 401

    # Get properties managed by the manager
    properties = Property.query.filter_by(manager_id=manager_id).all()
    property_ids = [p.id for p in properties]

    # Fetch messages for those properties
    messages = Message.query.filter(Message.property_id.in_(property_ids)).order_by(Message.timestamp.asc()).all()

    messages_data = [{
        'message': msg.message,
        'sender_role': msg.sender_role,
        'timestamp': msg.timestamp.isoformat()
    } for msg in messages]

    return jsonify({'success': True, 'messages': messages_data}), 200

if __name__ == '__main__':
    app.run(debug=True)