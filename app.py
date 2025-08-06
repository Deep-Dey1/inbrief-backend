from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from flask_cors import CORS
import os
import uuid
from datetime import datetime, timedelta
import pytz
import requests
from requests.auth import HTTPBasicAuth
import json
import sys
import logging
from logging.handlers import RotatingFileHandler
import traceback
from config import Config
from cloudinary_service import CloudinaryService
from models import db, NewsPost

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10000, backupCount=3),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created successfully")

# Configure CORS to allow requests from any origin
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "empId", "phoneLastFour"]
    }
})

# Legacy upload folder (kept for backward compatibility)
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,empId,phoneLastFour')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# SAP API credentials (from config)
SAP_API_USERNAME = Config.SAP_API_USERNAME
SAP_API_PASSWORD = Config.SAP_API_PASSWORD
SAP_API_BASE_URL = Config.SAP_API_BASE_URL

# Allowed employee IDs for admin access (from config)
ALLOWED_ADMIN_IDS = Config.ALLOWED_ADMIN_IDS

# Timezone helper function
def get_ist_time():
    """Get current time in Indian Standard Time"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def format_ist_time(dt=None):
    """Format datetime in IST for display"""
    if dt is None:
        dt = get_ist_time()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Post categories
POST_CATEGORIES = ['Finance', 'Healthcare', 'Achievement', 'Notice', 'Urgent']

# Database operations replace JSON file operations
def load_posts():
    """Load posts from database"""
    try:
        posts = NewsPost.query.order_by(NewsPost.created_at.desc()).all()
        posts_data = [post.to_dict_with_image_data() for post in posts]
        logger.info(f"Loaded {len(posts_data)} posts from database")
        return posts_data
    except Exception as e:
        logger.error(f"Error loading posts from database: {e}")
        return []

def save_posts(posts_data):
    """Save posts to database (for compatibility with existing code)"""
    try:
        # Clear existing posts and re-save all (not efficient but maintains compatibility)
        NewsPost.query.delete()
        
        for post_data in posts_data:
            post = NewsPost.from_dict(post_data)
            db.session.add(post)
        
        db.session.commit()
        logger.info(f"Saved {len(posts_data)} posts to database")
    except Exception as e:
        logger.error(f"Error saving posts to database: {e}")
        db.session.rollback()

def add_post_to_db(post_data):
    """Add a single post to database"""
    try:
        post = NewsPost.from_dict(post_data)
        db.session.add(post)
        db.session.commit()
        logger.info(f"Added post {post_data['id']} to database")
        return True
    except Exception as e:
        logger.error(f"Error adding post to database: {e}")
        db.session.rollback()
        return False

def update_post_in_db(post_id, post_data):
    """Update a post in database"""
    try:
        post = NewsPost.query.get(post_id)
        if post:
            post.headline = post_data.get('headline', '')
            post.description = post_data.get('description', '')
            post.image_urls = json.dumps(post_data.get('image_urls', []))
            post.image_data = json.dumps(post_data.get('image_data', []))
            post.category = post_data.get('category')
            db.session.commit()
            logger.info(f"Updated post {post_id} in database")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating post in database: {e}")
        db.session.rollback()
        return False

def delete_post_from_db(post_id):
    """Delete a post from database"""
    try:
        post = NewsPost.query.get(post_id)
        if post:
            db.session.delete(post)
            db.session.commit()
            logger.info(f"Deleted post {post_id} from database")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting post from database: {e}")
        db.session.rollback()
        return False

def generate_post_id():
    return str(uuid.uuid4())

def is_post_editable(post_date):
    """Check if post is within 24 hour edit window"""
    # Parse the post time and make it timezone-aware (IST)
    ist = pytz.timezone('Asia/Kolkata')
    post_time = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
    post_time = ist.localize(post_time)
    
    # Compare with current IST time
    current_time = get_ist_time()
    return current_time - post_time <= timedelta(hours=24)

def fallback_image_upload(images):
    """Fallback image upload to local storage if Cloudinary fails"""
    image_urls = []
    for image in images:
        if image and image.filename:
            try:
                filename = f"{uuid.uuid4()}_{image.filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(save_path)
                # Use Railway's domain for the URL
                base_url = os.environ.get('RAILWAY_STATIC_URL', 'https://web-production-c427.up.railway.app')
                image_urls.append(f'{base_url}/static/uploads/{filename}')
                logger.info(f"Fallback upload successful: {filename}")
            except Exception as e:
                logger.error(f"Fallback upload failed for {image.filename}: {e}")
    return image_urls

# Mobile app endpoints - Authentication moved to Flutter app
# This endpoint is removed as authentication now happens directly in Flutter

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_id = request.form.get('employee_id')
        phone_last_four = request.form.get('password')
        
        if not emp_id or not phone_last_four:
            return render_template('login.html', error='Employee ID and password are required')
            
        if emp_id not in ALLOWED_ADMIN_IDS:
            return render_template('login.html', error='Unauthorized access')
            
        try:
            # Verify against SAP API
            query = (
                f"{SAP_API_BASE_URL}/EmpJob?$filter=userId eq '{emp_id}'"
                "&$expand=employmentNav/personNav/phoneNav,"
                "employmentNav/personNav/personalInfoNav,"
                "departmentNav,locationNav"
                "&$select=userId,employmentNav/personNav/phoneNav/phoneNumber,"
                "employmentNav/personNav/personalInfoNav/firstName,"
                "employmentNav/personNav/personalInfoNav/lastName,"
                "departmentNav/name,locationNav/name"
                "&$format=json"
            )
            
            response = requests.get(
                query,
                auth=HTTPBasicAuth(SAP_API_USERNAME, SAP_API_PASSWORD),
                timeout=30
            )
            
            if response.status_code != 200:
                return render_template('login.html', error='Failed to verify credentials')
                
            data = response.json()
            results = data.get('d', {}).get('results', [])
            
            if not results:
                return render_template('login.html', error='Employee not found')
                
            employee = results[0]
            employment_nav = employee.get('employmentNav', {})
            person_nav = employment_nav.get('personNav', {})
            phone_nav = person_nav.get('phoneNav', {})
            phone_results = phone_nav.get('results', [])
            
            if not phone_results:
                return render_template('login.html', error='Phone number not found')
                
            phone_number = phone_results[0].get('phoneNumber')
            if not phone_number:
                return render_template('login.html', error='Invalid phone number')
                
            cleaned_phone = ''.join(filter(str.isdigit, phone_number))
            if cleaned_phone[-4:] != phone_last_four:
                return render_template('login.html', error='Invalid credentials')
                
            # Get employee name for display
            personal_info = person_nav.get('personalInfoNav', {}).get('results', [{}])[0]
            first_name = personal_info.get('firstName', '')
            last_name = personal_info.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip()
            
            # Store in session
            session['logged_in'] = True
            session['employee_id'] = emp_id
            session['employee_name'] = full_name
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return render_template('login.html', error='Login failed. Please try again.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(f):
    """Decorator to require login for routes"""
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Admin dashboard route
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html',
                         employee_name=session.get('employee_name'),
                         categories=POST_CATEGORIES)

# List all posts (clean data for mobile app)
@app.route('/api/news/all', methods=['GET'])
def get_all_news():
    try:
        # Get posts directly from database
        posts = NewsPost.query.order_by(NewsPost.created_at.desc()).all()
        clean_posts = [post.to_dict() for post in posts]
        return jsonify(clean_posts)
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return jsonify([]), 500

# Add a new post with Cloudinary image upload and better error handling
@app.route('/api/news', methods=['POST'])
@login_required
def add_news():
    headline = request.form.get('headline', '')
    description = request.form.get('description', '')
    category = request.form.get('category')
    images = request.files.getlist('images')
    
    logger.info(f"Creating new post: headline='{headline[:50]}...', images={len(images)}")
    
    # Allow empty headline but require at least one of: headline, description, or image
    if not headline and not description and not images:
        return jsonify({'error': 'Post must have at least a headline, description, or image.'}), 400
        
    if category and category not in POST_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
        
    # Upload images to Cloudinary with better error handling
    image_data = []
    upload_errors = []
    
    if images:
        try:
            logger.info(f"Starting upload of {len(images)} images to Cloudinary")
            uploaded_images, failed_uploads = CloudinaryService.upload_multiple_images(images, folder="inbrief_posts")
            
            for img in uploaded_images:
                image_data.append({
                    'url': img['url'],
                    'public_id': img['public_id']
                })
            
            if failed_uploads:
                upload_errors = [f"Failed to upload {f['filename']}: {f['error']}" for f in failed_uploads]
                logger.warning(f"Some image uploads failed: {upload_errors}")
                
        except Exception as e:
            logger.error(f"Critical error during image upload: {e}")
            return jsonify({'error': f'Image upload failed: {str(e)}'}), 500
                
    post_id = generate_post_id()
    date_str = format_ist_time()  # Use IST time instead of UTC
    news_item = {
        'id': post_id,
        'headline': headline,
        'description': description,
        'image_urls': [img['url'] for img in image_data],  # URLs for mobile app
        'image_data': image_data,  # Full data with public_ids for backend
        'date': date_str,
        'category': category,
        'author': session.get('employee_name')
    }
    
    # Add to database instead of in-memory list
    if add_post_to_db(news_item):
        logger.info(f"Post created successfully: {post_id}")
        
        # Return clean data for mobile app (without public_ids)
        clean_item = {
            'id': news_item['id'],
            'headline': news_item['headline'],
            'description': news_item['description'],
            'image_urls': news_item['image_urls'],
            'date': news_item['date'],
            'author': news_item['author']
        }
        
        response_data = {'success': True, 'item': clean_item}
        if upload_errors:
            response_data['warnings'] = upload_errors
        
        return jsonify(response_data), 201
    else:
        return jsonify({'error': 'Failed to save post to database'}), 500

# Edit a post by id with Cloudinary support
@app.route('/api/news/edit/<post_id>', methods=['POST'])
@login_required
def edit_news(post_id):
    try:
        # Get post from database
        post = NewsPost.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
            
        # Convert to dict for compatibility
        post_data = post.to_dict_with_image_data()
        
        # Check if post is older than 24 hours
        if not is_post_editable(post_data['date']):
            return jsonify({'error': 'Posts can only be edited within 24 hours of creation'}), 403
            
        headline = request.form.get('headline', '')
        description = request.form.get('description', '')
        category = request.form.get('category')
        images = request.files.getlist('images')
        
        # Allow empty headline but require at least one of: headline, description, or image
        if not headline and not description and not images:
            return jsonify({'error': 'Post must have at least a headline, description, or image.'}), 400
            
        if category and category not in POST_CATEGORIES:
            return jsonify({'error': 'Invalid category'}), 400
            
        # Update post data
        post_data['headline'] = headline
        post_data['description'] = description
        if category:
            post_data['category'] = category
            
        # Handle new images
        if images and len(images) > 0:
            # Delete old images from Cloudinary
            old_image_data = post_data.get('image_data', [])
            for img_data in old_image_data:
                if 'public_id' in img_data:
                    CloudinaryService.delete_image(img_data['public_id'])
            
            # Upload new images
            uploaded_images, failed_uploads = CloudinaryService.upload_multiple_images(images, folder="inbrief_posts")
            new_image_data = []
            for img in uploaded_images:
                new_image_data.append({
                    'url': img['url'],
                    'public_id': img['public_id']
                })
            
            post_data['image_urls'] = [img['url'] for img in new_image_data]
            post_data['image_data'] = new_image_data
            
        # Update in database
        if update_post_in_db(post_id, post_data):
            # Return clean data for response
            clean_post = {
                'id': post_data['id'],
                'headline': post_data['headline'],
                'description': post_data['description'],
                'image_urls': post_data['image_urls'],
                'date': post_data['date'],
                'author': post_data['author']
            }
            
            return jsonify({'success': True, 'item': clean_post}), 200
        else:
            return jsonify({'error': 'Failed to update post in database'}), 500
            
    except Exception as e:
        logger.error(f"Error editing post {post_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Delete a post with Cloudinary cleanup
@app.route('/api/news/delete/<post_id>', methods=['DELETE'])
@login_required
def delete_news(post_id):
    try:
        # Get post from database
        post = NewsPost.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
            
        # Convert to dict to get image data
        post_data = post.to_dict_with_image_data()
        
        # Remove images from Cloudinary
        image_data = post_data.get('image_data', [])
        for img_data in image_data:
            if 'public_id' in img_data:
                CloudinaryService.delete_image(img_data['public_id'])
        
        # Also clean up legacy local images if they exist
        image_urls = post_data.get('image_urls', [])
        for url in image_urls:
            if url and '/static/uploads/' in url:
                filename = url.split('/static/uploads/')[-1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        # Delete from database
        if delete_post_from_db(post_id):
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to delete post from database'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Assign admin access
@app.route('/api/assign_admin', methods=['POST'])
@login_required
def assign_admin():
    data = request.get_json()
    emp_id = data.get('empId')

    if not emp_id:
        return jsonify({'error': 'Employee ID is required'}), 400

    try:
        # Verify the requesting user is an admin
        if session.get('employee_id') not in ALLOWED_ADMIN_IDS:
            return jsonify({'error': 'Unauthorized to assign admin access'}), 403

        # Verify the employee exists in SAP before assigning admin
        query = (
            f"{SAP_API_BASE_URL}/EmpJob?$filter=userId eq '{emp_id}'"
            "&$select=userId"
            "&$format=json"
        )
        response = requests.get(
            query,
            auth=HTTPBasicAuth(SAP_API_USERNAME, SAP_API_PASSWORD),
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"SAP API request failed with status {response.status_code}")
            return jsonify({'error': 'Failed to verify employee'}), 400

        data = response.json()
        results = data.get('d', {}).get('results', [])
        if not results:
            return jsonify({'error': 'Employee not found'}), 404

        # Add the new admin to ALLOWED_ADMIN_IDS
        ALLOWED_ADMIN_IDS.add(emp_id)
        logger.info(f"Admin access granted to Employee ID: {emp_id} at {format_ist_time()}")
        return jsonify({'success': True})
    except requests.Timeout:
        logger.error("SAP API request timed out")
        return jsonify({'error': 'Request timed out'}), 408
    except requests.RequestException as e:
        logger.error(f"SAP API request failed: {e}")
        return jsonify({'error': 'Failed to connect to SAP API'}), 500
    except Exception as e:
        logger.error(f"Error assigning admin: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

# Database management endpoint (for testing/migration)
@app.route('/api/admin/db-info', methods=['GET'])
@login_required
def db_info():
    try:
        post_count = NewsPost.query.count()
        return jsonify({
            'success': True,
            'database_connected': True,
            'total_posts': post_count,
            'message': f'Database is working! Found {post_count} posts.'
        })
    except Exception as e:
        logger.error(f"Database info error: {e}")
        return jsonify({
            'success': False,
            'database_connected': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Use environment PORT for cloud deployment, default to 5000 for local
    port = int(os.environ.get('PORT', 5000))
    # Use threaded=True for better handling of concurrent requests
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)



    