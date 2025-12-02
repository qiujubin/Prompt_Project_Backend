import sys
import os
import json
import re
from sqlalchemy import text

# Add Backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal, engine
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword

def parse_sidebar_data():
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Frontend/src/api/mockData/sidebar.ts'))
    print(f"Reading file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract promptCatagory array content
    # Look for "promptCatagory: [" and the matching closing bracket is tricky with regex due to nesting.
    # Instead, we can find the start index and then count brackets.
    
    start_marker = "promptCatagory: ["
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("Could not find promptCatagory start marker")
        return []
    
    start_idx += len(start_marker) - 1 # Point to '['
    
    # Count brackets to find the end
    bracket_count = 0
    end_idx = -1
    for i in range(start_idx, len(content)):
        if content[i] == '[':
            bracket_count += 1
        elif content[i] == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end_idx = i + 1
                break
                
    if end_idx == -1:
        print("Could not find matching closing bracket")
        return []
        
    json_str = content[start_idx:end_idx]
    
    # Cleanup to make it valid JSON
    # 1. Remove comments
    json_str = re.sub(r'//.*', '', json_str)
    # 2. Quote keys (simple keys like name, label, icon, children)
    json_str = re.sub(r'(\s)([a-zA-Z0-9_]+):', r'\1"\2":', json_str)
    # 3. Ensure strings are double quoted (if they are single quoted)
    # This is tricky if strings contain quotes. Assuming simple structure.
    # But wait, python's json.loads expects double quotes.
    # If the file uses "double quotes", we are good. If 'single', we need replacement.
    # Looking at the file content earlier, it uses double quotes: name: "food".
    # So we just need to quote the keys.
    # Also remove trailing commas
    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
    
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        # Fallback: Manual evaluation or stricter regex?
        # Let's try to debug by printing a snippet if fail
        print(json_str[:500])
        return []

def seed_data():
    db = SessionLocal()
    
    # 0. Ensure column exists (Migration hack)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE prompt_keywords ADD COLUMN IF NOT EXISTS display_name VARCHAR(256)"))
            conn.execute(text("ALTER TABLE prompt_categories ADD COLUMN IF NOT EXISTS icon VARCHAR(64)"))
            conn.commit()
        print("Columns check passed.")
    except Exception as e:
        print(f"Column check warning: {e}")

    data = parse_sidebar_data()
    if not data:
        print("No data found.")
        return

    print(f"Found {len(data)} top-level categories.")
    
    # Clear existing data to ensure updates (like icons) are applied?
    # Since we are checking `if not cat`, we might miss updates if we don't update existing.
    # Let's update existing records.

    for i, cat_data in enumerate(data):
        cat_name = cat_data.get("name")
        cat_label = cat_data.get("label")
        cat_icon = cat_data.get("icon", "Box")
        
        # Check if exists
        cat = db.query(PromptCategory).filter(PromptCategory.name == cat_name).first()
        if not cat:
            cat = PromptCategory(name=cat_name, display_name=cat_label, icon=cat_icon, sort_order=i)
            db.add(cat)
            db.commit()
            db.refresh(cat)
        else:
            # Update existing
            cat.display_name = cat_label
            cat.icon = cat_icon
            cat.sort_order = i
            db.commit()
        
        children = cat_data.get("children", [])
        for j, sub_data in enumerate(children):
            sub_name = sub_data.get("name")
            sub_label = sub_data.get("label")
            
            sub = db.query(PromptSubcategory).filter(
                PromptSubcategory.category_id == cat.id,
                PromptSubcategory.name == sub_name
            ).first()
            
            if not sub:
                sub = PromptSubcategory(
                    category_id=cat.id,
                    name=sub_name,
                    display_name=sub_label,
                    sort_order=j
                )
                db.add(sub)
                db.commit()
                db.refresh(sub)
            
            keywords = sub_data.get("children", [])
            for kw_data in keywords:
                kw_word = kw_data.get("name")
                kw_label = kw_data.get("label")
                
                kw = db.query(PromptKeyword).filter(
                    PromptKeyword.small_category_id == sub.id,
                    PromptKeyword.word == kw_word
                ).first()
                
                if not kw:
                    kw = PromptKeyword(
                        small_category_id=sub.id,
                        word=kw_word,
                        display_name=kw_label
                    )
                    db.add(kw)
            
            db.commit() # Commit keywords batch
            
    print("Data seeding completed.")
    db.close()

if __name__ == "__main__":
    seed_data()
