import json
import psycopg2
import os
from urllib.parse import parse_qs

# Supabase Database configuration - Session Pooler (recommended for serverless)
# Database: inbrief-database, Password: InBrief2025!
DATABASE_URL = os.environ.get('SUPABASE_DATABASE_URL', 'postgresql://postgres.iwzmixjdzjdukkrkwyxh:InBrief2025!@aws-0-ap-south-1.pooler.supabase.com:5432/postgres')

def get_db_connection():
    """Get database connection to Supabase"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        return None

def handler(event, context):
    """Netlify Function handler"""
    
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS request (CORS preflight)
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Parse the path
    path = event.get('path', '')
    
    try:
        # Health check
        if path == '/' or path == '/health':
            conn = get_db_connection()
            if not conn:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({"status": "unhealthy", "database": "connection_failed"})
                }
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM news_post")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    "status": "healthy",
                    "database": "supabase_connected",
                    "total_posts": count,
                    "message": "InBrief API - Netlify + Supabase",
                    "timestamp": "2025-08-08"
                })
            }
        
        # Get all news
        elif path == '/api/news/all' or path.endswith('/news/all'):
            conn = get_db_connection()
            if not conn:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({"error": "Database connection failed"})
                }
            
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
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(posts)
            }
        
        else:
            # Default response
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({"error": "Endpoint not found", "available_endpoints": ["/", "/health", "/api/news/all"]})
            }
            
    except Exception as e:
        print(f"Function error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e)})
        }
