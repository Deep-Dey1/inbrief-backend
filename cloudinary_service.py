# Cloudinary service for image upload and management
import cloudinary
import cloudinary.uploader
import cloudinary.api
from config import Config
import uuid
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Configure Cloudinary
try:
    cloudinary.config(
        cloud_name=Config.CLOUDINARY_CLOUD_NAME,
        api_key=Config.CLOUDINARY_API_KEY,
        api_secret=Config.CLOUDINARY_API_SECRET,
        secure=True  # Always use HTTPS
    )
    logger.info("Cloudinary configured successfully")
except Exception as e:
    logger.error(f"Cloudinary configuration failed: {e}")

class CloudinaryService:
    @staticmethod
    def upload_image(file, folder="inbrief_posts"):
        """Upload image to Cloudinary and return URL"""
        try:
            logger.info(f"Starting image upload: {file.filename}")
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            
            # Upload to Cloudinary with optimized settings
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                public_id=unique_filename,
                overwrite=True,
                resource_type="image",
                # Optimized transformations for faster upload
                transformation=[
                    {'quality': 'auto:good'},  # Faster than 'auto'
                    {'fetch_format': 'auto'},
                    {'width': 1200, 'height': 800, 'crop': 'limit'}  # Limit size
                ],
                # Add timeout and retry settings
                timeout=30,  # 30 second timeout
                chunk_size=6000000  # 6MB chunks
            )
            
            logger.info(f"Image upload successful: {result['secure_url']}")
            return {
                'success': True,
                'url': result['secure_url'],
                'public_id': result['public_id']
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary upload error: {e}")
            return {
                'success': False,
                'error': f'Cloudinary error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"General upload error: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    @staticmethod
    def delete_image(public_id):
        """Delete image from Cloudinary"""
        try:
            logger.info(f"Deleting image: {public_id}")
            result = cloudinary.uploader.destroy(public_id, timeout=15)
            success = result.get('result') == 'ok'
            logger.info(f"Image deletion {'successful' if success else 'failed'}: {public_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting image {public_id}: {e}")
            return False
    
    @staticmethod
    def upload_multiple_images(files, folder="inbrief_posts"):
        """Upload multiple images and return URLs with improved error handling"""
        uploaded_images = []
        failed_uploads = []
        
        logger.info(f"Starting upload of {len(files)} images")
        
        for i, file in enumerate(files):
            if file and file.filename:
                logger.info(f"Uploading image {i+1}/{len(files)}: {file.filename}")
                result = CloudinaryService.upload_image(file, folder)
                if result['success']:
                    uploaded_images.append({
                        'url': result['url'],
                        'public_id': result['public_id']
                    })
                else:
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': result['error']
                    })
                    logger.warning(f"Failed to upload {file.filename}: {result['error']}")
        
        logger.info(f"Upload complete: {len(uploaded_images)} successful, {len(failed_uploads)} failed")
        return uploaded_images, failed_uploads
