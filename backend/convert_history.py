"""
Convert conversation JSON files to readable Markdown and HTML formats.

This script reads conversation files from data/conversations/ and creates
readable copies in both Markdown (.md) and HTML (.html) formats in the
readable_history/ folder. Original JSON files are left untouched.
"""

import json
import os
import html
import sys
from pathlib import Path

# --- CONFIGURATION ---
# Get the project root directory (parent of backend/)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SOURCE_FOLDER = PROJECT_ROOT / "data" / "conversations"
OUTPUT_FOLDER = PROJECT_ROOT / "readable_history"


def create_html_header():
    """Generate the HTML header with styling."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Conversation History</title>
    <style>
        body { font-family: sans-serif; background-color: #f0f2f5; padding: 20px; }
        .chat-container { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 15px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); word-wrap: break-word; }
        .role-user { align-self: flex-end; background-color: #dcf8c6; margin-left: 20%; }
        .role-assistant { align-self: flex-start; background-color: #ffffff; margin-right: 20%; border: 1px solid #ddd; }
        .role-system { align-self: center; background-color: #e1f5fe; font-size: 0.8em; }
        .meta { font-weight: bold; font-size: 0.7em; color: #555; margin-bottom: 5px; text-transform: uppercase; }
        pre { background: #eee; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="chat-container">
"""


def extract_all_text(data):
    """Recursively finds all text strings in the JSON."""
    text_parts = []
    if isinstance(data, str):
        return [data]
    elif isinstance(data, list):
        for item in data:
            text_parts.extend(extract_all_text(item))
    elif isinstance(data, dict):
        for key, value in data.items():
            # Skip metadata keys we don't want to read
            if key in ['role', 'name', 'tool_call_id', 'start', 'end']:
                continue
            text_parts.extend(extract_all_text(value))
    return text_parts


def convert_file(filename):
    """
    Convert a single JSON conversation file to both Markdown and HTML.
    Original JSON file is left untouched.
    
    Args:
        filename: Name of the JSON file to convert
        
    Returns:
        True if successful, False otherwise
    """
    filepath = SOURCE_FOLDER / filename
    
    # Validate file exists
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}", file=sys.stderr)
        return False
    
    # Load JSON data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filename}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}", file=sys.stderr)
        return False

    # Find messages list
    messages = []
    if isinstance(data, list):
        messages = data
    elif isinstance(data, dict):
        for k in ['messages', 'history', 'conversation', 'turns']:
            if k in data:
                messages = data[k]
                break
    
    if not messages:
        print(f"⚠️  No messages found in {filename}", file=sys.stderr)
        return False

    # Extract conversation metadata for title
    conv_title = data.get('title', 'New Conversation') if isinstance(data, dict) else 'Conversation'
    conv_id = data.get('id', filename.replace('.json', '')) if isinstance(data, dict) else filename.replace('.json', '')

    # --- BUILD MARKDOWN CONTENT ---
    md_content = f"# {conv_title}\n\n"
    md_content += f"**Conversation ID:** `{conv_id}`\n\n"
    if isinstance(data, dict) and 'created_at' in data:
        md_content += f"**Created:** {data['created_at']}\n\n"
    md_content += "---\n\n"

    # --- BUILD HTML CONTENT ---
    html_content = create_html_header()
    html_content += f"<h1>{html.escape(conv_title)}</h1>\n"
    html_content += f"<p><strong>Conversation ID:</strong> <code>{html.escape(conv_id)}</code></p>\n"
    if isinstance(data, dict) and 'created_at' in data:
        html_content += f"<p><strong>Created:</strong> {html.escape(data['created_at'])}</p>\n"
    html_content += "<hr>\n"

    # Process each message
    for msg in messages:
        role = msg.get('role', 'unknown')
        
        # Extract text using the universal method
        all_text_bits = extract_all_text(msg)
        clean_text_bits = [t for t in all_text_bits if t and t.strip()]
        clean_text = "\n".join(clean_text_bits)
        
        if not clean_text:
            clean_text = "*(No text content)*"

        # Add to Markdown
        md_content += f"## {role.upper()}\n\n"
        md_content += f"{clean_text}\n\n"
        md_content += "---\n\n"

        # Add to HTML
        display_text = html.escape(clean_text).replace('\n', '<br>')
        css_class = f"role-{role}"
        html_content += f"""
        <div class="message {css_class}">
            <div class="meta">{role}</div>
            <div>{display_text}</div>
        </div>
        """

    # Close HTML
    html_content += "\n    </div>\n</body>\n</html>"

    # Save both formats
    base_name = filename.replace('.json', '')
    md_path = OUTPUT_FOLDER / f"{base_name}.md"
    html_path = OUTPUT_FOLDER / f"{base_name}.html"
    
    try:
        # Write Markdown
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # Write HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Created copies: {base_name}.md, {base_name}.html")
        return True
    except Exception as e:
        print(f"❌ Error writing files for {filename}: {e}", file=sys.stderr)
        return False


def main():
    """Main execution function."""
    # Ensure directories exist
    try:
        SOURCE_FOLDER.mkdir(parents=True, exist_ok=True)
        OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Error creating directories: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check if source folder exists
    if not SOURCE_FOLDER.exists():
        print(f"❌ Source folder does not exist: {SOURCE_FOLDER}", file=sys.stderr)
        sys.exit(1)
    
    # Find all JSON files
    json_files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith('.json')]
    
    if not json_files:
        print(f"⚠️  No JSON files found in {SOURCE_FOLDER}")
        return
    
    print(f"📁 Found {len(json_files)} conversation file(s) to convert...")
    print(f"📂 Original files will remain untouched in {SOURCE_FOLDER}")
    print(f"📝 Creating readable copies in {OUTPUT_FOLDER}\n")
    
    # Convert each file
    success_count = 0
    for filename in json_files:
        if convert_file(filename):
            success_count += 1
    
    print(f"\n✨ Conversion complete: {success_count}/{len(json_files)} files processed successfully")
    print(f"   Created {success_count * 2} readable files ({success_count} .md + {success_count} .html)")


if __name__ == "__main__":
    main()