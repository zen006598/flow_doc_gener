def compress_content(content):
    lines = content.split('\n')
    stripped_lines = [line.strip() for line in lines if line.strip()]  # Remove empty lines
    
    # Merge single character lines with next line
    compressed_lines = []
    i = 0
    while i < len(stripped_lines):
        current_line = stripped_lines[i]
        if len(current_line) == 1 and i + 1 < len(stripped_lines):
            # Merge single character with next line
            next_line = stripped_lines[i + 1]
            compressed_lines.append(current_line + '' + next_line)
            i += 2
        else:
            compressed_lines.append(current_line)
            i += 1
    
    return '\n'.join(compressed_lines)