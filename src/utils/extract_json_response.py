def extract_json_response(content):
    """Extract JSON from LLM response, handling both ```json wrapped and plain JSON"""
    if not isinstance(content, str):
        return None
        
    content = content.strip()
    
    # Try to extract from ```json wrapper
    if '```json' in content:
        import re
        match = re.search(r'```json\s*\n?(.*?)\n?```', content, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # Try plain JSON (starts with { or [)
    if content.startswith(('{', '[')):
        return content
        
    return None
