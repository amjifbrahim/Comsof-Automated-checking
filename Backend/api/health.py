import json

def handler(request):
    """Serverless handler for health check"""
    
    # Allow GET requests only
    if request.method != 'GET':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'}),
            'headers': {'Content-Type': 'application/json'}
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'healthy', 'service': 'comsof-validation'}),
        'headers': {'Content-Type': 'application/json'}
    }