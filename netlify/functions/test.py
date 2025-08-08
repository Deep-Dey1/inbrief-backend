import json

def handler(event, context):
    """Simple test function for Netlify deployment verification"""
    
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
    
    # Simple health check response
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            "status": "healthy",
            "message": "InBrief API - Netlify Test Function",
            "timestamp": "2025-08-08",
            "note": "This is a simple test function. Main app.py function will handle database connections."
        })
    }
