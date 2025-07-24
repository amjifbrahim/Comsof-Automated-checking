import re
from typing import Dict, Optional, Tuple, Any

class MultipartParser:
    """Simple multipart form data parser for serverless functions"""
    
    def __init__(self, body: bytes, content_type: str):
        self.body = body
        self.content_type = content_type
        self.boundary = self._extract_boundary()
        
    def _extract_boundary(self) -> Optional[str]:
        """Extract boundary from content type header"""
        match = re.search(r'boundary=([^;]+)', self.content_type)
        if match:
            boundary = match.group(1).strip('"')
            return boundary
        return None
    
    def parse(self) -> Dict[str, Any]:
        """Parse multipart form data and return dictionary of fields"""
        if not self.boundary:
            raise ValueError("No boundary found in content type")
        
        fields = {}
        boundary_bytes = f'--{self.boundary}'.encode()
        
        # Split by boundary
        parts = self.body.split(boundary_bytes)
        
        for part in parts[1:-1]:  # Skip first empty part and last closing part
            if not part.strip():
                continue
                
            # Split headers and body
            try:
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    continue
                    
                headers = part[:header_end].decode('utf-8', errors='ignore')
                body = part[header_end + 4:]
                
                # Remove trailing CRLF
                if body.endswith(b'\r\n'):
                    body = body[:-2]
                
                # Parse Content-Disposition header
                field_info = self._parse_content_disposition(headers)
                if not field_info:
                    continue
                
                field_name = field_info.get('name')
                if not field_name:
                    continue
                
                # Handle file fields
                if 'filename' in field_info:
                    fields[field_name] = {
                        'filename': field_info['filename'],
                        'data': body,
                        'size': len(body),
                        'content_type': self._extract_content_type(headers)
                    }
                else:
                    # Regular form field
                    try:
                        fields[field_name] = body.decode('utf-8')
                    except UnicodeDecodeError:
                        fields[field_name] = body
                        
            except Exception as e:
                # Skip malformed parts
                continue
        
        return fields
    
    def _parse_content_disposition(self, headers: str) -> Optional[Dict[str, str]]:
        """Parse Content-Disposition header"""
        disposition_match = re.search(r'Content-Disposition:\s*([^\r\n]+)', headers, re.IGNORECASE)
        if not disposition_match:
            return None
        
        disposition = disposition_match.group(1)
        result = {}
        
        # Extract name
        name_match = re.search(r'name="([^"]*)"', disposition)
        if name_match:
            result['name'] = name_match.group(1)
        
        # Extract filename if present
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match:
            result['filename'] = filename_match.group(1)
        
        return result if result else None
    
    def _extract_content_type(self, headers: str) -> str:
        """Extract Content-Type from headers"""
        content_type_match = re.search(r'Content-Type:\s*([^\r\n]+)', headers, re.IGNORECASE)
        if content_type_match:
            return content_type_match.group(1).strip()
        return 'application/octet-stream'

def parse_multipart_form(body: bytes, content_type: str) -> Dict[str, Any]:
    """Convenience function to parse multipart form data"""
    parser = MultipartParser(body, content_type)
    return parser.parse()