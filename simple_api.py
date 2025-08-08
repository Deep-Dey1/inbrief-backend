#!/usr/bin/env python3
"""
Simple Direct Database API
Fetches news posts directly from PostgreSQL database
Bypasses Railway domain blocking by running locally or on different hosting
"""

import os
import json
import psycopg2
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import logging

# Simple Flask app
app = Flask(__name__)
CORS(app)

# Database configuration - using the exact same as Railway
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.kthazjqojhsrlpvgnvlt:QeRWafYc1bXhtSzD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres')

# Fix postgres:// to postgresql:// if needed
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    try:
        print(f"🔗 Attempting to connect to database...")
        print(f"📍 Database URL: {DATABASE_URL[:50]}...")
        
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Database connection successful!")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        logger.error(f"Database connection failed: {e}")
        return None

@app.route('/')
def home():
    """Simple health check"""
    return jsonify({
        "status": "active",
        "message": "Simple InBrief API - Direct Database Access",
        "timestamp": datetime.now().isoformat(),
        "endpoints": ["/api/news/all", "/health"]
    })

@app.route('/api/news/all')
def get_all_news():
    """Fetch all news posts directly from database"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Query all news posts
        query = """
        SELECT id, title, content, image_url, created_at, updated_at, author, source_url 
        FROM news_post 
        ORDER BY created_at DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convert to JSON format
        posts = []
        for row in rows:
            post = {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "image_url": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "author": row[6],
                "source_url": row[7]
            }
            posts.append(post)
        
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully fetched {len(posts)} posts from database")
        return jsonify(posts)
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Database health check"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "unhealthy", "database": "connection_failed"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_post")
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "total_posts": count,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Simple InBrief API...")
    print("📊 Direct database connection active")
    print("🌐 Endpoints available:")
    print("   - http://localhost:5000/")
    print("   - http://localhost:5000/api/news/all")
    print("   - http://localhost:5000/health")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
