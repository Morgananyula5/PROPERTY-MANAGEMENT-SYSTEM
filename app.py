from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Property, Message
from config import Config
from flask_migrate import Migrate
import os
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask-Migrate
db.init_app(app)
migrate = Migrate(app, db)

# Custom Jinja filter to parse JSON strings
@app.template_filter('parse_json')
def parse_json(s):
    try:
        return json.loads(s) if s else []
    except json.JSONDecodeError:
        return []

# Ensure tables are created
with app.app_context():
    db.create_all()

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Home route
@app.route('/')
def home():
    return redirect(url_for('signup'))

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', '').capitalize()

        if not all([username, email, password, role]):
            flash("All fields are required.", "danger")
            return redirect(url_for('signup'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists. Use a different one.", "danger")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password, role=role)
        try:
            db.session.add(user)
            db.session.commit()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating user: {str(e)}", "danger")
            return redirect(url_for('signup'))

    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("This email does not exist in our system.", "warning")
            return redirect(url_for('login'))

        if check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role.capitalize()
            flash("Login successful!", "success")
            if session['role'] == 'Resident':
                return redirect(url_for('resident_dashboard'))
            elif session['role'] == 'Manager':
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

    try:
        properties = Property.query.all()
        properties_data = []
        for property in properties:
            description_lines = property.description.split('\n')
            profile_picture = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), 'default-profile.png')
            if profile_picture != 'default-profile.png':
                profile_picture = f"/static/{profile_picture}"

            media_paths = []
            for line in description_lines:
                if line.startswith('Media: '):
                    media_paths = [f"/static/{path}" for path in line.split(': ')[1].split(', ') if line.split(': ')[1]] or []

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
                'property_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), ''),
                'amenities': next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), ''),
                'availability': property.availability,
                'features': json.loads(property.features) if property.features else [],
                'media': media_paths,
                'profile_picture': profile_picture
            }
            properties_data.append(property_data)
        return render_template('resident_dashboard.html', properties=properties_data)
    except Exception as e:
        logger.error(f"Error loading resident dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return redirect(url_for('login'))


# Manager Dashboard Route
@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    try:
        user_id = session['user_id']
        recent_property = Property.query.filter_by(manager_id=user_id).first()
        property_data = None
        profile_picture = None

        if recent_property:
            description_lines = recent_property.description.split('\n')
            profile_picture = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), 'default-profile.png')
            if profile_picture != 'default-profile.png':
                profile_picture = f"/static/{profile_picture}"

            media_paths = []
            for line in description_lines:
                if line.startswith('Media: '):
                    media_paths = [f"/static/{path}" for path in line.split(': ')[1].split(', ') if line.split(': ')[1]] or []

            property_data = {
                'id': recent_property.id,
                'name': recent_property.name,
                'type': recent_property.property_type,
                'status': recent_property.status,
                'phone': recent_property.phone,
                'email': recent_property.email,
                'description': description_lines[0],
                'location': recent_property.location,
                'sub_county': recent_property.sub_county,
                'landmarks': recent_property.landmarks,
                'property_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), ''),
                'amenities': next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), ''),
                'availability': recent_property.availability,
                'features': json.loads(recent_property.features) if recent_property.features else [],
                'media': media_paths
            }

        return render_template('manager_dashboard.html', profile_picture=profile_picture, property=property_data)
    except Exception as e:
        logger.error(f"Error loading manager dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return redirect(url_for('login'))

# Route to Add Property
@app.route('/add_property', methods=['POST'])
def add_property():
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    existing_property = Property.query.filter_by(manager_id=user_id).first()
    if existing_property:
        flash("You have already added a property. You can only manage one property.", "danger")
        return redirect(url_for('manager_dashboard'))

    try:
        name = request.form.get('name')
        property_type = request.form.get('type')
        status = request.form.get('status')
        phone = request.form.get('phone')
        email = request.form.get('email')
        description = request.form.get('description')
        location = request.form.get('location')
        sub_county = request.form.get('sub_county')
        landmarks = request.form.get('landmarks')
        property_address = request.form.get('property_address')
        availability = request.form.get('availability')
        amenities = request.form.get('amenities')
        common_area_name = request.form.get('common_area_name')
        features = request.form.getlist('features[]')
        prices = request.form.getlist('prices[]')
        occupancy_status = request.form.getlist('status[]')
        rooms_available = request.form.getlist('rooms_available[]')
        room_size = request.form.getlist('room_size[]')
        floor = request.form.getlist('floor[]')
        utilities = request.form.getlist('utilities[]')
        currency = request.form.getlist('currency[]')

        if not all([name, property_type, status, phone, email, description, location, sub_county, landmarks, property_address, availability, amenities, common_area_name]):
            flash("All fields are required.", "danger")
            return redirect(url_for('manager_dashboard'))

        profile_picture = request.files.get('profile_picture')
        profile_picture_path = None
        if profile_picture and profile_picture.filename:
            try:
                filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_picture.save(profile_picture_path)
                profile_picture_path = f"uploads/{filename}"
                logger.info(f"Profile picture saved at: {profile_picture_path}")
            except Exception as e:
                logger.error(f"Error saving profile picture: {str(e)}")
                flash(f"Error saving profile picture: {str(e)}", "danger")
                profile_picture_path = None
        else:
            flash("No profile picture uploaded", "warning")

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
                logger.info(f"Media files saved: {', '.join(media_paths)}")
            except Exception as e:
                logger.error(f"Error saving media files: {str(e)}")
                flash(f"Error saving media files: {str(e)}", "danger")
                media_paths = []
        else:
            flash("No media files uploaded", "warning")

        # Include new fields in the feature JSON
        feature_price_status = [
            {
                "feature": f,
                "price": p,
                "status": s,
                "rooms_available": ra,
                "room_size": rs,
                "floor": fl,
                "utilities": u,
                "currency": c
            }
            for f, p, s, ra, rs, fl, u, c in zip(
                features, prices, occupancy_status, rooms_available, room_size, floor, utilities, currency
            )
        ]
        features_json = json.dumps(feature_price_status)

        combined_description = f"{description}\nProperty Address: {property_address}\nAmenities: {amenities}"
        if profile_picture_path:
            combined_description += f"\nProfile Picture: {profile_picture_path}"
        if media_paths:
            combined_description += f"\nMedia: {', '.join(media_paths)}"

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
            viewing_schedule="Not specified",
            features=features_json,
            common_area_name=common_area_name,
            manager_id=user_id
        )

        db.session.add(new_property)
        db.session.commit()
        flash("Property added successfully!", "success")
        return redirect(url_for('manager_dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding property: {str(e)}")
        flash(f"Error adding property: {str(e)}", "danger")
        return redirect(url_for('manager_dashboard'))

# Route to Edit Property
@app.route('/edit_property/<int:property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    try:
        property = Property.query.get_or_404(property_id)
        if property.manager_id != session['user_id']:
            flash("You are not authorized to edit this property.", "danger")
            return redirect(url_for('manager_dashboard'))

        if request.method == 'POST':
            name = request.form.get('name')
            property_type = request.form.get('type')
            status = request.form.get('status')
            phone = request.form.get('phone')
            email = request.form.get('email')
            description = request.form.get('description')
            location = request.form.get('location')
            sub_county = request.form.get('sub_county')
            landmarks = request.form.get('landmarks')
            property_address = request.form.get('property_address')
            availability = request.form.get('availability')
            amenities = request.form.get('amenities')
            common_area_name = request.form.get('common_area_name')
            features = request.form.getlist('features[]')
            prices = request.form.getlist('prices[]')
            occupancy_status = request.form.getlist('status[]')
            rooms_available = request.form.getlist('rooms_available[]')
            room_size = request.form.getlist('room_size[]')
            floor = request.form.getlist('floor[]')
            utilities = request.form.getlist('utilities[]')
            currency = request.form.getlist('currency[]')

            if not all([name, property_type, status, phone, email, description, location, sub_county, landmarks, property_address, availability, amenities, common_area_name]):
                flash("All fields are required.", "danger")
                return redirect(url_for('edit_property', property_id=property_id))

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
                    logger.info(f"Profile picture updated: {profile_picture_path}")
                except Exception as e:
                    logger.error(f"Error saving profile picture: {str(e)}")
                    flash(f"Error saving profile picture: {str(e)}", "danger")
                    profile_picture_path = existing_profile_picture
            else:
                profile_picture_path = existing_profile_picture

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
                    logger.info(f"Media files updated: {', '.join(media_paths)}")
                except Exception as e:
                    logger.error(f"Error saving media files: {str(e)}")
                    flash(f"Error saving media files: {str(e)}", "danger")
                    media_paths = existing_media
            else:
                media_paths = existing_media

            # Include new fields in the feature JSON
            feature_price_status = [
                {
                    "feature": f,
                    "price": p,
                    "status": s,
                    "rooms_available": ra,
                    "room_size": rs,
                    "floor": fl,
                    "utilities": u,
                    "currency": c
                }
                for f, p, s, ra, rs, fl, u, c in zip(
                    features, prices, occupancy_status, rooms_available, room_size, floor, utilities, currency
                )
            ]
            features_json = json.dumps(feature_price_status)

            combined_description = f"{description}\nProperty Address: {property_address}\nAmenities: {amenities}"
            if profile_picture_path:
                combined_description += f"\nProfile Picture: {profile_picture_path}"
            if media_paths:
                combined_description += f"\nMedia: {', '.join(media_paths)}"

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
            property.common_area_name = common_area_name

            db.session.commit()
            flash("Property updated successfully!", "success")
            return redirect(url_for('manager_dashboard'))
        else:
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
                'property_address': next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), ''),
                'amenities': next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), ''),
                'availability': property.availability,
                'features': json.loads(property.features) if property.features else [],
                'media': media_paths
            }

            return render_template('manager_dashboard.html', profile_picture=profile_picture, property=property_data, edit_mode=True)
    except Exception as e:
        logger.error(f"Error editing property: {str(e)}")
        flash(f"Error editing property: {str(e)}", "danger")
        return redirect(url_for('manager_dashboard'))



# Route to Add Media
@app.route('/add_media/<int:property_id>', methods=['POST'])
def add_media(property_id):
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    try:
        property = Property.query.get_or_404(property_id)
        if property.manager_id != session['user_id']:
            flash("You are not authorized to add media to this property.", "danger")
            return redirect(url_for('manager_dashboard'))

        description_lines = property.description.split('\n')
        main_description = description_lines[0]
        property_address = next((line.split(': ')[1] for line in description_lines if line.startswith('Property Address: ')), '')
        amenities = next((line.split(': ')[1] for line in description_lines if line.startswith('Amenities: ')), '')
        profile_picture_path = next((line.split(': ')[1] for line in description_lines if line.startswith('Profile Picture: ')), None)
        existing_media = []
        for line in description_lines:
            if line.startswith('Media: '):
                existing_media = line.split(': ')[1].split(', ') if line.split(': ')[1] else []

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
                logger.info(f"New media files added: {', '.join(new_media_paths)}")
            except Exception as e:
                logger.error(f"Error saving media files: {str(e)}")
                flash(f"Error saving media files: {str(e)}", "danger")
                return redirect(url_for('manager_dashboard'))
        else:
            flash("No media files selected.", "warning")
            return redirect(url_for('manager_dashboard'))

        all_media = existing_media + new_media_paths
        combined_description = f"{main_description}\nProperty Address: {property_address}\nAmenities: {amenities}"
        if profile_picture_path:
            combined_description += f"\nProfile Picture: {profile_picture_path}"
        if all_media:
            combined_description += f"\nMedia: {', '.join(all_media)}"

        property.description = combined_description
        db.session.commit()
        flash("Media added successfully!", "success")
        return redirect(url_for('manager_dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding media: {str(e)}")
        flash(f"Error adding media: {str(e)}", "danger")
        return redirect(url_for('manager_dashboard'))

# Route to Get Manager's Property ID
@app.route('/get_manager_property', methods=['GET'])
def get_manager_property():
    if 'user_id' not in session or session.get('role') != 'Manager':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 401

    try:
        user_id = session['user_id']
        property = Property.query.filter_by(manager_id=user_id).first()
        if not property:
            return jsonify({'status': 'error', 'message': 'No property associated with this manager'}), 404
        return jsonify({'status': 'success', 'property_id': property.id})
    except Exception as e:
        logger.error(f"Error fetching property: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error fetching property: {str(e)}'}), 500

# Route to Send Message
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        logger.warning("Unauthorized access attempt to /send_message")
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 401

    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data provided in /send_message")
            return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400

        content = data.get('content')
        is_manager = data.get('is_manager', False)
        property_id = data.get('property_id')
        recipient_id = data.get('recipient_id')

        if not content or not property_id:
            logger.error("Missing content or property_id in /send_message")
            return jsonify({'status': 'error', 'message': 'Message content and property ID are required'}), 400

        try:
            property_id = int(property_id)
        except ValueError:
            logger.error(f"Invalid property_id: {property_id}")
            return jsonify({'status': 'error', 'message': 'Invalid property ID'}), 400

        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        property = Property.query.get(property_id)
        if not property:
            logger.error(f"Property not found: {property_id}")
            return jsonify({'status': 'error', 'message': 'Property not found'}), 404

        # Determine recipient_id
        if is_manager:
            if not recipient_id:
                logger.error("Recipient ID required for manager messages")
                return jsonify({'status': 'error', 'message': 'Recipient ID is required for manager messages'}), 400
            recipient = User.query.get(recipient_id)
            if not recipient:
                logger.error(f"Recipient not found: {recipient_id}")
                return jsonify({'status': 'error', 'message': 'Recipient not found'}), 404
        else:
            # Resident sending to manager
            recipient_id = property.manager_id
            if not recipient_id:
                logger.error(f"No manager assigned to property_id: {property_id}")
                return jsonify({'status': 'error', 'message': 'No manager assigned to this property'}), 404

        message = Message(
            sender_id=user_id,
            recipient_id=recipient_id,
            property_id=property_id,
            content=content,
            timestamp=datetime.utcnow(),
            is_manager=is_manager
        )

        db.session.add(message)
        db.session.commit()
        logger.info(f"Message sent successfully: user_id={user_id}, property_id={property_id}, recipient_id={recipient_id}")
        return jsonify({'status': 'success', 'message': 'Message sent successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error sending message: {str(e)}'}), 500


# Route to Get Conversations
@app.route('/get_conversations', methods=['GET'])
def get_conversations():
    if 'user_id' not in session:
        logger.warning("Unauthorized access attempt to /get_conversations")
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 401

    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        if user.role == 'Manager':
            # Get the manager's property
            property = Property.query.filter_by(manager_id=user_id).first()
            if not property:
                logger.error(f"No property associated with manager_id: {user_id}")
                return jsonify({'status': 'error', 'message': 'No property associated with this manager'}), 404

            # Get unique senders who have messaged this property
            senders = db.session.query(Message.sender_id, User.username).join(
                User, Message.sender_id == User.id
            ).filter(
                Message.property_id == property.id,
                Message.sender_id != user_id
            ).distinct().all()

            conversations = [{
                'sender_id': sender_id,
                'sender_name': username,
                'property_id': property.id
            } for sender_id, username in senders]
        else:
            # Resident: get properties they have messaged
            properties = db.session.query(Message.property_id, Property.name).join(
                Property, Message.property_id == Property.id
            ).filter(
                (Message.sender_id == user_id) | (Message.recipient_id == user_id)
            ).distinct().all()

            conversations = [{
                'property_id': property_id,
                'property_name': name
            } for property_id, name in properties]

        logger.info(f"Conversations fetched successfully for user_id: {user_id}")
        return jsonify({'status': 'success', 'conversations': conversations})
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error fetching conversations: {str(e)}'}), 500

# Route to Get Messages
@app.route('/get_messages', methods=['GET'])
def get_messages():
    if 'user_id' not in session:
        logger.warning("Unauthorized access attempt to /get_messages")
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 401

    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        property_id = request.args.get('property_id')
        sender_id = request.args.get('sender_id')

        if not property_id:
            logger.error("Missing property_id in /get_messages")
            return jsonify({'status': 'error', 'message': 'Property ID is required'}), 400

        try:
            property_id = int(property_id)
        except ValueError:
            logger.error(f"Invalid property_id: {property_id}")
            return jsonify({'status': 'error', 'message': 'Invalid property ID'}), 400

        property = Property.query.get(property_id)
        if not property:
            logger.error(f"Property not found: {property_id}")
            return jsonify({'status': 'error', 'message': 'Property not found'}), 404

        if user.role == 'Manager':
            if property.manager_id != user_id:
                logger.error(f"Unauthorized access to messages for property_id: {property_id} by user_id: {user_id}")
                return jsonify({'status': 'error', 'message': 'Unauthorized to view messages for this property'}), 403
            if sender_id:
                try:
                    sender_id = int(sender_id)
                except ValueError:
                    logger.error(f"Invalid sender_id: {sender_id}")
                    return jsonify({'status': 'error', 'message': 'Invalid sender ID'}), 400
                messages = Message.query.filter(
                    Message.property_id == property_id,
                    (Message.sender_id == sender_id) | (Message.recipient_id == sender_id)
                ).order_by(Message.timestamp.asc()).all()
            else:
                messages = Message.query.filter_by(property_id=property_id).order_by(Message.timestamp.asc()).all()
        else:
            messages = Message.query.filter(
                Message.property_id == property_id,
                (Message.sender_id == user_id) | (Message.recipient_id == user_id)
            ).order_by(Message.timestamp.asc()).all()

        messages_data = [{
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'is_manager': msg.is_manager,
            'sender_id': msg.sender_id
        } for msg in messages]

        logger.info(f"Messages fetched successfully for property_id: {property_id}, user_id: {user_id}")
        return jsonify({'status': 'success', 'messages': messages_data})
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error fetching messages: {str(e)}'}), 500



if __name__ == '__main__':
    app.run(debug=True)