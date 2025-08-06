# Database Models for News Posts
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class NewsPost(db.Model):
    __tablename__ = 'news_posts'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    headline = db.Column(db.Text, nullable=False, default='')
    description = db.Column(db.Text, nullable=False, default='')
    image_urls = db.Column(db.Text)  # JSON string of image URLs
    image_data = db.Column(db.Text)  # JSON string of image data with public_ids
    date = db.Column(db.String(20), nullable=False)  # IST timestamp string
    category = db.Column(db.String(50))
    author = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert post to dictionary for API responses"""
        return {
            'id': self.id,
            'headline': self.headline,
            'description': self.description,
            'image_urls': json.loads(self.image_urls) if self.image_urls else [],
            'date': self.date,
            'category': self.category,
            'author': self.author
        }
    
    def to_dict_with_image_data(self):
        """Convert post to dictionary including image data for backend operations"""
        data = self.to_dict()
        data['image_data'] = json.loads(self.image_data) if self.image_data else []
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create NewsPost instance from dictionary"""
        return cls(
            id=data['id'],
            headline=data.get('headline', ''),
            description=data.get('description', ''),
            image_urls=json.dumps(data.get('image_urls', [])),
            image_data=json.dumps(data.get('image_data', [])),
            date=data['date'],
            category=data.get('category'),
            author=data.get('author')
        )
