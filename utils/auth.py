from functools import wraps
from flask import session, redirect, url_for, flash

def admin_required(f):
    """
    A decorator to ensure a user is logged in as an admin.
    If not, it redirects to the admin login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if 'role' exists in the session and if it's 'admin'
        if session.get('role') != 'admin':
            flash('You must be logged in as an admin to view this page.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function