# Cloudinary service for image upload and management
import cloudinary
import cloudinary.uploader
import cloudinary.api
from config import Config
import uuid
import os

# Configure Cloudinary
cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)

class CloudinaryService:
    @staticmethod
    def upload_image(file, folder="inbrief_posts"):
        """Upload image to Cloudinary and return URL"""
        try:
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                public_id=unique_filename,
                overwrite=True,
                resource_type="image",
                transformation=[
                    {'quality': 'auto'},
                    {'fetch_format': 'auto'}
                ]
            )
            
            return {
                'success': True,
                'url': result['secure_url'],
                'public_id': result['public_id']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def delete_image(public_id):
        """Delete image from Cloudinary"""
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
        except Exception as e:
            return False
    
    @staticmethod
    def upload_multiple_images(files, folder="inbrief_posts"):
        """Upload multiple images and return URLs"""
        uploaded_images = []
        
        for file in files:
            if file:
                result = CloudinaryService.upload_image(file, folder)
                if result['success']:
                    uploaded_images.append({
                        'url': result['url'],
                        'public_id': result['public_id']
                    })
        
        return uploaded_images
