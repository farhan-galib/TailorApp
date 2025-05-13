from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tailor.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'ftmlbiproject@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'wckx hxvl ujhc uqke')

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=False)
    orders = db.relationship('Order', backref='tailor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Order Model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    measurements = db.Column(db.Text, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    delivery_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    user_orders = Order.query.filter_by(user_id=current_user.id)
    total_orders = user_orders.count()
    deliveries_this_week = user_orders.filter(Order.delivery_date >= week_start, Order.delivery_date <= week_end).count()
    pending_orders = user_orders.filter_by(status='Pending').count()
    completed_orders = user_orders.filter_by(status='Completed').count()
    return render_template(
        'dashboard.html',
        total_orders=total_orders,
        deliveries_this_week=deliveries_this_week,
        pending_orders=pending_orders,
        completed_orders=completed_orders
    )

@app.route('/create_order', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        try:
            new_order = Order(
                customer_name=request.form.get('customer_name'),
                customer_email=request.form.get('customer_email'),
                phone_number=request.form.get('phone_number'),
                gender=request.form.get('gender'),
                measurements=request.form.get('measurements'),
                delivery_date=datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%d'),
                user_id=current_user.id
            )
            db.session.add(new_order)
            db.session.commit()
            flash('Order created successfully!', 'success')
            return redirect(url_for('order_details'))
        except Exception as e:
            flash('Failed to create order. Please try again.', 'error')
            print(f"Order creation failed: {str(e)}")
            return render_template('create_order.html')
    return render_template('create_order.html')

@app.route('/order_details')
@login_required
def order_details():
    filter_type = request.args.get('filter')
    orders_query = Order.query.filter_by(user_id=current_user.id)
    if filter_type == 'pending':
        orders_query = orders_query.filter_by(status='Pending')
    elif filter_type == 'completed':
        orders_query = orders_query.filter_by(status='Completed')
    elif filter_type == 'delivered_this_week':
        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        orders_query = orders_query.filter(Order.delivery_date >= week_start, Order.delivery_date <= week_end)
    orders = orders_query.all()
    return render_template('order_details.html', orders=orders)

def send_order_completion_email(user_email, customer_name, order_id):
    msg = Message(
        'Order Completed',
        sender=app.config['MAIL_USERNAME'],
        recipients=[user_email]
    )
    msg.body = f'''Dear Tailor,

The order for customer {customer_name} (Order ID: {order_id}) has been marked as completed.

Best regards,
Your Tailoring System
'''
    mail.send(msg)

def send_customer_completion_email(customer_email, customer_name, order_id):
    msg = Message(
        'Your Order is Ready!',
        sender=app.config['MAIL_USERNAME'],
        recipients=[customer_email]
    )
    msg.body = f'''Dear {customer_name},

We are pleased to inform you that your order (Order ID: {order_id}) has been completed and is ready for pickup/delivery.

Please visit our store to collect your order or contact us for delivery arrangements.

Thank you for choosing our services!

Best regards,
Your Tailoring Team
'''
    mail.send(msg)

@app.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        old_status = order.status
        order.customer_name = request.form.get('customer_name')
        order.customer_email = request.form.get('customer_email')
        order.phone_number = request.form.get('phone_number')
        order.gender = request.form.get('gender')
        order.measurements = request.form.get('measurements')
        order.delivery_date = datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%d')
        order.status = request.form.get('status')
        
        # Send email notifications if status changed to completed
        if old_status != 'Completed' and order.status == 'Completed':
            try:
                # Send notification to customer
                send_customer_completion_email(order.customer_email, order.customer_name, order.id)
                flash('Order updated successfully! Email notification sent to customer.', 'success')
            except Exception as e:
                flash('Order updated successfully, but failed to send email notification. Please try again later.', 'error')
                print(f"Email sending failed: {str(e)}")
            
        db.session.commit()
        return redirect(url_for('order_details'))
    return render_template('edit_order.html', order=order)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return render_template('register.html')
            
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered')
            return render_template('register.html')
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 