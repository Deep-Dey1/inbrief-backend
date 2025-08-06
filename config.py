# Environment Configuration
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
    
    # SAP API (for admin verification only)
    SAP_API_USERNAME = os.environ.get('SAP_API_USERNAME', 'api_user@navitasysi')
    SAP_API_PASSWORD = os.environ.get('SAP_API_PASSWORD', 'api@1234')
    SAP_API_BASE_URL = os.environ.get('SAP_API_BASE_URL', 'https://api44.sapsf.com/odata/v2')
    
    # Admin Access
    ALLOWED_ADMIN_IDS = set(os.environ.get('ALLOWED_ADMIN_IDS', '9025857,9025676,9023422,9025432').split(','))
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///posts.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
