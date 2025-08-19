import os
from dotenv import load_dotenv
load_dotenv()

class Config():
    def __init__(self):
        self.default_model = os.getenv("GEMINI_MODEL", "googleai/gemini-2.5-flash")
        
        self.api_key_map = {
            "gemini": os.getenv("GEMINI_API_KEY", "")
        }
        
        self.base_url_map = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/"
        }
        
        self.default_include_patterns = {"*.cs"}
        self.default_exclude_patterns = {
            "*.md", 
            "dockerfile",
            "*test*",
            "*Test*",
            "*test*/*",
            "*Test*/*",
            "*/test*/*",
            "*/Test*/*",
            "tests/*",
            "test/*",
            "__tests__/*",
        }