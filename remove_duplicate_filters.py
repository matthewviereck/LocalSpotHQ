"""
Remove Duplicate Date Filters
==============================
Removes the old date filter buttons if they exist
"""

import re

def remove_duplicate_filters(input_file='app.html', output_file='app.html'):
    """
    Remove any old date filter HTML that might be duplicating the buttons
    """
    
    print("="*60)
    print("REMOVING DUPLICATE DATE FILTERS")
    print("="*60)
    
    print(f"\n>> Reading {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {input_file} not found!")
        return False
    
    original_html = html
    original_size = len(html)
    
    print(f">> Original file size: {original_size} characters")
    
    # Look for old date filter container that might have been added by add_date_filters.py
    # Pattern: <!-- Date Filters --> ... date-filter-container
    
    patterns_to_remove = [
        # Pattern 1: Old date-filter-container with buttons
        r'<!-- Date Filters -->\s*<div class="flex gap-2 mb-3 overflow-x-auto no-scrollbar" id="date-filter-container">[\s\S]*?</div>',
        
        # Pattern 2: Any div with id="date-filter-container"
        r'<div[^>]*id="date-filter-container"[^>]*>[\s\S]*?</div>\s*',
        
        # Pattern 3: Date filter buttons with data-filter attribute
        r'<div class="flex gap-2 mb-3[^"]*"[^>]*>\s*<button[^>]*data-filter="all"[\s\S]*?</div>\s*(?=\s*<div[^>]*id="chip-container")',
    ]
    
    removed_count = 0
    
    for i, pattern in enumerate(patterns_to_remove, 1):
        print(f"\n>> Checking pattern {i}...")
        matches = re.findall(pattern, html)
        
        if matches:
            print(f"   Found {len(matches)} match(es)")
            html = re.sub(pattern, '', html)
            removed_count += len(matches)
            print(f"   ✓ Removed")
        else:
            print(f"   No matches found")
    
    # Also remove any leftover CSS for date-filter-btn if it exists
    css_pattern = r'\.date-filter-btn \{[^}]*\}\s*\.date-filter-btn\.active \{[^}]*\}\s*\.date-filter-btn:hover:not\(\.active\) \{[^}]*\}\s*'
    
    if re.search(css_pattern, html):
        print("\n>> Removing old date filter CSS...")
        html = re.sub(css_pattern, '', html)
        print("   ✓ Removed old CSS")
    
    # Remove any leftover JavaScript for date filtering (setDateFilter, filterByDate)
    js_patterns = [
        r'// --- DATE FILTERING ---[\s\S]*?function filterByDate\(items\) \{[\s\S]*?\}\s*',
        r'let currentDateFilter = [^;]+;\s*',
        r'function setDateFilter\([^)]*\) \{[\s\S]*?\}\s*',
    ]
    
    for js_pattern in js_patterns:
        if re.search(js_pattern, html):
            print(">> Removing old date filter JavaScript...")
            html = re.sub(js_pattern, '', html)
            print("   ✓ Removed old JS")
    
    # Check for changes
    if html == original_html:
        print("\n>> No duplicates found - file is clean!")
        return True
    
    new_size = len(html)
    size_diff = original_size - new_size
    
    print(f"\n>> Removed {size_diff} characters ({removed_count} duplicate sections)")
    
    # Save
    print(f"\n>> Saving cleaned file to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   New file size: {new_size} characters")
    
    print("\n" + "="*60)
    print("✓ SUCCESS! Duplicates removed")
    print("="*60)
    print("\n📤 NEXT STEP:")
    print("   Upload app.html to Hostinger")
    print("   Clear your browser cache and reload")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = remove_duplicate_filters()
        if not success:
            print("\n✗ Failed. Check errors above.")
            exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
