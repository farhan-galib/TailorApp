from app import app, db, User

def create_test_user():
    with app.app_context():
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(username='admin').first()
            if existing_user:
                print("Test user already exists!")
                # Update the password to ensure it's set correctly
                existing_user.set_password('admin123')
                db.session.commit()
                print("Password has been reset to 'admin123'")
            else:
                # Create new user
                user = User(username='admin')
                user.set_password('admin123')
                db.session.add(user)
                db.session.commit()
                print("Test user created successfully!")
            
            # Verify the user was created/updated
            user = User.query.filter_by(username='admin').first()
            if user:
                print(f"User verification: Username '{user.username}' exists in database")
                # Test password
                if user.check_password('admin123'):
                    print("Password verification: Password is working correctly")
                else:
                    print("Password verification: Password is NOT working correctly")
            else:
                print("Error: User was not found in database after creation")
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    create_test_user() 