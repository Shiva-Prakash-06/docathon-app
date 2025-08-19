import os

# Best practice: load secret values from environment variables
# Set these in your terminal before running the app:
# export SECRET_KEY='a_very_secret_random_string'
# export ADMIN_PASSCODE='your_chosen_admin_password'

SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key-for-dev')
ADMIN_PASSCODE = os.environ.get('ADMIN_PASSCODE', 'docathon@2025')
TIMEZONE = 'Asia/Kolkata'