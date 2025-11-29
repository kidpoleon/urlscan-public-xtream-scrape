"""
Data models for XTream credentials
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class XtreamCredential:
    """Model for XTream IPTV credential"""
    domain: str
    port: str
    username: str
    password: str
    xtream_url: str
    original_redirect: str
    source_path: str
    source_text: str
    scan_id: str
    scan_date: str
    page_url: str
    is_valid: Optional[bool] = None
    validation_date: Optional[datetime] = None
    user_info: Optional[dict] = None
    
    def is_valid_xtream_format(self) -> bool:
        """Check if this follows XTream API format (not live/play)"""
        invalid_usernames = {'live', 'play', 'test', 'demo', 'admin'}
        invalid_passwords = {'live', 'play', 'test', 'demo', 'password', '123456'}
        
        return (self.username not in invalid_usernames and 
                self.password not in invalid_passwords and
                len(self.username) > 2 and 
                len(self.password) > 2)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'domain': self.domain,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'xtream_url': self.xtream_url,
            'original_redirect': self.original_redirect,
            'source_path': self.source_path,
            'source_text': self.source_text,
            'scan_id': self.scan_id,
            'scan_date': self.scan_date,
            'page_url': self.page_url,
            'is_valid': self.is_valid,
            'validation_date': self.validation_date.isoformat() if self.validation_date else None,
            'user_info': self.user_info
        }
