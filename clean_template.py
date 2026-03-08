"""
Clean Template - Remove ALL Old Date Filter Code
=================================================
This removes any old date filter HTML/CSS/JS from phoenixville.html
so that ONLY the new renderChips() date filters remain.

Run this ONCE, then weekly_update.py will work perfectly.
"""

import re

def clean_template(template_file='phoenixville.html'):
    """
    Remove all old date filter code from the template
    """
    
    print("="*60)
    print("CLEANING PHOENIXVILLE.HTML TEMPLATE")
    print("="*60)
    
    print(f"\n>> Reading {template_file}...")
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {template_file} not found!")
        return False
    
    original_html = html
    original_size = len(html)
    
    print(f">> Original file size: {original_size} characters")
    
    changes_made = []
    
    # ============================================================
    # STEP 1: Remove old date filter HTML
    # ============================================================
    print("\n>> Step 1: Removing old date filter HTML...")
    
    # Pattern for the old date-filter-container div
    patterns = [
        # Full date filter container with buttons
        r'<!-- Date Filters -->\s*<div class="flex gap-2 mb-3 overflow-x-auto no-scrollbar" id="date-filter-container">[\s\S]*?</div>\s*',
        
        # Just the container if comment is missing
        r'<div class="flex gap-2 mb-3 overflow-x-auto no-scrollbar" id="date-filter-container">[\s\S]*?</div>\s*',
        
        # Alternative pattern - any div with date-filter-container
        r'<div[^>]*id="date-filter-container"[^>]*>(?:(?!<div).)*?</div>\s*',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.findall(pattern, html)
        if matches:
            print(f"   Found pattern {i}: {len(matches)} match(es)")
            before_size = len(html)
            html = re.sub(pattern, '', html)
            after_size = len(html)
            removed = before_size - after_size
            print(f"   ✓ Removed {removed} characters")
            changes_made.append(f"HTML pattern {i}")
    
    # ============================================================
    # STEP 2: Remove old date filter CSS
    # ============================================================
    print("\n>> Step 2: Removing old date filter CSS...")
    
    css_patterns = [
        # The full CSS block for date filter buttons
        r'\.date-filter-btn \{[\s\S]*?\}\s*\.date-filter-btn\.active \{[\s\S]*?\}\s*\.date-filter-btn:hover:not\(\.active\) \{[\s\S]*?\}\s*',
        
        # Individual CSS rules
        r'\.date-filter-btn \{[^}]*\}\s*',
        r'\.date-filter-btn\.active \{[^}]*\}\s*',
        r'\.date-filter-btn:hover:not\(\.active\) \{[^}]*\}\s*',
    ]
    
    for i, pattern in enumerate(css_patterns, 1):
        matches = re.findall(pattern, html)
        if matches:
            print(f"   Found CSS pattern {i}: {len(matches)} match(es)")
            before_size = len(html)
            html = re.sub(pattern, '', html)
            after_size = len(html)
            removed = before_size - after_size
            print(f"   ✓ Removed {removed} characters")
            changes_made.append(f"CSS pattern {i}")
    
    # ============================================================
    # STEP 3: Remove old date filter JavaScript
    # ============================================================
    print("\n>> Step 3: Removing old date filter JavaScript...")
    
    js_patterns = [
        # The full date filtering block
        r'// --- DATE FILTERING ---[\s\S]*?function filterByDate\(items\) \{[\s\S]*?\n        \}\s*',
        
        # Individual functions and variables
        r'let currentDateFilter = [^;]+;\s*',
        r'function setDateFilter\([^)]*\) \{[\s\S]*?\n        \}\s*',
        r'function filterByDate\([^)]*\) \{[\s\S]*?\n        \}\s*',
    ]
    
    for i, pattern in enumerate(js_patterns, 1):
        matches = re.findall(pattern, html)
        if matches:
            print(f"   Found JS pattern {i}: {len(matches)} match(es)")
            before_size = len(html)
            html = re.sub(pattern, '', html)
            after_size = len(html)
            removed = before_size - after_size
            print(f"   ✓ Removed {removed} characters")
            changes_made.append(f"JS pattern {i}")
    
    # ============================================================
    # VERIFICATION
    # ============================================================
    print("\n>> Step 4: Verification...")
    
    # Make sure the NEW date filters are still there
    if "if (currentTab === 'events') {" in html and "const dateFilters = ['All', 'Tomorrow'" in html:
        print("   ✓ New date filters (in renderChips) still present")
    else:
        print("   ⚠ WARNING: New date filters not found!")
    
    if "'Tomorrow': 'tomorrow'" in html:
        print("   ✓ Date filter mapping (in filterData) still present")
    else:
        print("   ⚠ WARNING: Date filter mapping not found!")
    
    # Check that old code is gone
    old_code_check = [
        ('date-filter-container', 'Old date filter container'),
        ('date-filter-btn', 'Old date filter button class'),
        ('setDateFilter', 'Old setDateFilter function'),
        ('filterByDate', 'Old filterByDate function'),
        ('currentDateFilter', 'Old date filter variable'),
    ]
    
    issues = []
    for code, description in old_code_check:
        if code in html:
            print(f"   ⚠ {description} still found!")
            issues.append(description)
        else:
            print(f"   ✓ {description} removed")
    
    # ============================================================
    # SAVE
    # ============================================================
    if html == original_html:
        print("\n>> No changes needed - template is already clean!")
        return True
    
    new_size = len(html)
    size_diff = original_size - new_size
    
    print(f"\n>> Removed {size_diff} characters total")
    print(f">> Changes made: {', '.join(changes_made) if changes_made else 'None'}")
    
    print(f"\n>> Saving cleaned template to {template_file}...")
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   New file size: {new_size} characters")
    
    print("\n" + "="*60)
    if issues:
        print("⚠ PARTIAL SUCCESS - Some old code may remain")
        print("="*60)
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nThe template has been cleaned but may need manual review.")
    else:
        print("✓ SUCCESS! Template is clean")
        print("="*60)
        print("\nYour phoenixville.html now has:")
        print("  ✓ Date filters in renderChips() (JavaScript-based)")
        print("  ✓ Date filtering in filterData()")
        print("  ✓ NO old duplicate HTML/CSS/JS")
    
    print("\n💡 NEXT STEPS:")
    print("   1. Run: py weekly_update.py")
    print("   2. Upload the generated app.html")
    print("   3. Clear browser cache and test")
    print("\n   From now on, just run weekly_update.py weekly!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = clean_template()
        if not success:
            print("\n✗ Failed. Check errors above.")
            exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
