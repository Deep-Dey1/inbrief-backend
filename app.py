from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from flask_cors import CORS
import os
import uuid
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
import json
import sys
import logging
from logging.handlers import RotatingFileHandler
import traceback
from config import Config
from cloudinary_service import CloudinaryService

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

# Post categories
POST_CATEGORIES = ['Finance', 'Healthcare', 'Achievement', 'Notice', 'Urgent']

# In-memory storage for demo (replace with DB in production)
news_posts = []

def generate_post_id():
    return str(uuid.uuid4())

def is_post_editable(post_date):
    """Check if post is within 24 hour edit window"""
    post_time = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
    return datetime.now() - post_time <= timedelta(hours=24)

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
    # Return clean posts without internal data like public_ids
    clean_posts = []
    for post in news_posts:
        clean_post = {
            'id': post['id'],
            'headline': post['headline'],
            'description': post['description'],
            'image_urls': post['image_urls'],
            'date': post['date'],
            'author': post.get('author', '')
        }
        clean_posts.append(clean_post)
    
    # Sort by date (descending)
    clean_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    return jsonify(clean_posts)

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
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    news_posts.insert(0, news_item)
    
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

# Edit a post by id with Cloudinary support
@app.route('/api/news/edit/<post_id>', methods=['POST'])
@login_required
def edit_news(post_id):
    for post in news_posts:
        if post['id'] == post_id:
            # Check if post is older than 24 hours
            if not is_post_editable(post['date']):
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
                
            post['headline'] = headline
            post['description'] = description
            if category:
                post['category'] = category
                
            # Handle new images
            if images and len(images) > 0:
                # Delete old images from Cloudinary
                old_image_data = post.get('image_data', [])
                for img_data in old_image_data:
                    if 'public_id' in img_data:
                        CloudinaryService.delete_image(img_data['public_id'])
                
                # Upload new images
                uploaded_images = CloudinaryService.upload_multiple_images(images, folder="inbrief_posts")
                new_image_data = []
                for img in uploaded_images:
                    new_image_data.append({
                        'url': img['url'],
                        'public_id': img['public_id']
                    })
                
                post['image_urls'] = [img['url'] for img in new_image_data]
                post['image_data'] = new_image_data
                
            # Return clean data for response
            clean_post = {
                'id': post['id'],
                'headline': post['headline'],
                'description': post['description'],
                'image_urls': post['image_urls'],
                'date': post['date'],
                'author': post['author']
            }
            
            return jsonify({'success': True, 'item': clean_post}), 200
            
    return jsonify({'error': 'Post not found'}), 404

# Delete a post with Cloudinary cleanup
@app.route('/api/news/delete/<post_id>', methods=['DELETE'])
@login_required
def delete_news(post_id):
    for i, post in enumerate(news_posts):
        if post['id'] == post_id:
            # Remove images from Cloudinary
            image_data = post.get('image_data', [])
            for img_data in image_data:
                if 'public_id' in img_data:
                    CloudinaryService.delete_image(img_data['public_id'])
            
            # Also clean up legacy local images if they exist
            image_urls = post.get('image_urls', [])
            for url in image_urls:
                if url and '/static/uploads/' in url:
                    filename = url.split('/static/uploads/')[-1]
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            
            news_posts.pop(i)
            return jsonify({'success': True}), 200
    return jsonify({'error': 'Post not found'}), 404

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
        logger.info(f"Admin access granted to Employee ID: {emp_id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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

if __name__ == '__main__':
    # Use environment PORT for cloud deployment, default to 5000 for local
    port = int(os.environ.get('PORT', 5000))
    # Use threaded=True for better handling of concurrent requests
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)