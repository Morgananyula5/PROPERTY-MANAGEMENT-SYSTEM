from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Property
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
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
    return render_template('resident_dashboard.html', properties=properties)

# Manager Dashboard Route
@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))
    return render_template('manager_dashboard.html')

# Route to Add Property (UPDATED: Removed `available_from`, Added "Vacant or Occupied")
@app.route('/add_property', methods=['POST'])
def add_property():
    if 'user_id' not in session or session.get('role') != 'Manager':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    name = request.form['name']
    property_type = request.form['type']
    status = request.form['status']
    phone = request.form['phone']
    email = request.form['email']
    description = request.form['description']
    location = request.form['location']
    sub_county = request.form['sub_county']
    landmarks = request.form['landmarks']
    
    features = request.form.getlist('features[]')
    prices = request.form.getlist('prices[]')
    occupancy_status = request.form.getlist('occupancy[]')  # Vacant or Occupied

    # Combine into list of dictionaries
    feature_price_status = [{"feature": f, "price": p, "status": s} for f, p, s in zip(features, prices, occupancy_status)]

    new_property = Property(
        name=name,
        property_type=property_type,
        status=status,
        phone=phone,
        email=email,
        description=description,
        location=location,
        sub_county=sub_county,
        landmarks=landmarks,
        features=str(feature_price_status)  # Store as JSON-like string
    )

    db.session.add(new_property)
    db.session.commit()

    flash("Property added successfully!", "success")
    return redirect(url_for('manager_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
