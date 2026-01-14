import firebase_admin
from firebase_admin import credentials, db

def initialize_firebase():
    cred = credentials.Certificate("assets/firebase_key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://your-database-name.firebaseio.com'
    })

def save_message(user, message):
    ref = db.reference('messages')
    ref.push({
        'user': user,
        'message': message
    })

def login(user, password):
    # This is a mock login function.
    # In a real application, you would verify the user's credentials against a database.
    return True
