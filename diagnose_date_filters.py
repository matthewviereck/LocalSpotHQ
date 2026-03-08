"""
Diagnose Duplicate Date Filters
================================
This will show you exactly where the duplicate filters are coming from
"""

import re

def diagnose_duplicates(html_file='app.html'):
    """
    Find and display all date filter related code
    """
    
    print("="*60)
    print("DIAGNOSING DUPLICATE DATE FILTERS")
    print("="*60)
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {html_file} not found!")
        return False
    
    print(f"\n>> File size: {len(html)} characters")
    
    # ============================================================
    # Search for all date filter related code
    # ============================================================
    
    findings = []
    
    # 1. Look for HTML date filter containers
    print("\n" + "="*60)
    print("1. HTML DATE FILTER CONTAINERS")
    print("="*60)
    
    patterns = [
        r'<div[^>]*id="date-filter-container"[^>]*>',
        r'<!-- Date Filters -->',
        r'<button[^>]*data-filter="(all|today|tomorrow|week)"[^>]*>',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, html)
        for match in matches:
            start = max(0, match.start() - 100)
            end = min(len(html), match.end() + 100)
            context = html[start:end]
            findings.append({
                'type': 'HTML Container',
                'pattern': pattern,
                'position': match.start(),
                'context': context
            })
            print(f"\n   Found at position {match.start()}:")
            print(f"   {context[:200]}...")
    
    # 2. Look for CSS
    print("\n" + "="*60)
    print("2. DATE FILTER CSS")
    print("="*60)
    
    css_patterns = [
        r'\.date-filter-btn\s*\{[^}]*\}',
        r'#date-filter-container[^}]*\{[^}]*\}',
    ]
    
    for pattern in css_patterns:
        matches = re.finditer(pattern, html)
        for match in matches:
            findings.append({
                'type': 'CSS',
                'pattern': pattern,
                'position': match.start()
            })
            print(f"\n   Found at position {match.start()}:")
            print(f"   {match.group()[:200]}...")
    
    # 3. Look for JavaScript date filtering
    print("\n" + "="*60)
    print("3. JAVASCRIPT DATE FILTERING")
    print("="*60)
    
    js_patterns = [
        (r'function setDateFilter\([^)]*\)', 'setDateFilter function'),
        (r'function filterByDate\([^)]*\)', 'filterByDate function'),
        (r'let currentDateFilter\s*=', 'currentDateFilter variable'),
        (r"const dateFilters = \['All', 'Tomorrow'", 'dateFilters array in renderChips'),
    ]
    
    for pattern, name in js_patterns:
        matches = re.finditer(pattern, html)
        for match in matches:
            start = max(0, match.start() - 50)
            end = min(len(html), match.end() + 200)
            context = html[start:end]
            findings.append({
                'type': f'JavaScript ({name})',
                'pattern': pattern,
                'position': match.start()
            })
            print(f"\n   Found {name} at position {match.start()}:")
            print(f"   {context[:300]}...")
    
    # 4. Look for filter mapping
    print("\n" + "="*60)
    print("4. FILTER MAPPING")
    print("="*60)
    
    if "'Tomorrow': 'tomorrow'" in html:
        pos = html.find("'Tomorrow': 'tomorrow'")
        print(f"\n   Found at position {pos}")
        start = max(0, pos - 200)
        end = min(len(html), pos + 300)
        print(f"   {html[start:end]}")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    # Count types
    html_count = sum(1 for f in findings if 'HTML' in f['type'])
    css_count = sum(1 for f in findings if 'CSS' in f['type'])
    js_count = sum(1 for f in findings if 'JavaScript' in f['type'])
    
    print(f"\nFound:")
    print(f"  - HTML date filter elements: {html_count}")
    print(f"  - CSS rules: {css_count}")
    print(f"  - JavaScript functions: {js_count}")
    print(f"\nTotal findings: {len(findings)}")
    
    # ============================================================
    # RECOMMENDATIONS
    # ============================================================
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    
    if html_count > 0:
        print("\n⚠️  FOUND OLD HTML DATE FILTERS!")
        print("   These are the first row of buttons you're seeing.")
        print("   They need to be removed.")
    
    js_has_old = any('setDateFilter' in str(f.get('pattern', '')) or 'filterByDate' in str(f.get('pattern', '')) for f in findings)
    js_has_new = any('dateFilters array' in f.get('type', '') for f in findings)
    
    if js_has_old:
        print("\n⚠️  FOUND OLD JAVASCRIPT DATE FILTERING!")
        print("   Old functions: setDateFilter, filterByDate")
        print("   These need to be removed.")
    
    if js_has_new:
        print("\n✓ FOUND NEW DATE FILTERING (in renderChips)")
        print("   This is correct and should stay.")
    
    print("\n" + "="*60)
    print("RECOMMENDED ACTION")
    print("="*60)
    
    if html_count > 0 or js_has_old:
        print("\nYou need to remove the old date filter code.")
        print("\nI'll create a custom cleaning script based on these findings...")
        
        # Create custom cleaning script
        return create_custom_cleaner(findings, html)
    else:
        print("\nNo obvious duplicates found in code.")
        print("The issue might be elsewhere. Can you upload your app.html?")
    
    return True

def create_custom_cleaner(findings, html):
    """Create a custom script to remove the exact duplicates found"""
    
    print("\n" + "="*60)
    print("CREATING CUSTOM CLEANER")
    print("="*60)
    
    # Find all HTML container positions
    html_positions = [f['position'] for f in findings if 'HTML' in f['type']]
    
    if html_positions:
        print(f"\nFound {len(html_positions)} HTML date filter sections")
        print("Creating removal script...")
        
        # Let's just do a simple aggressive removal
        with open('fix_duplicates_aggressive.py', 'w') as f:
            f.write('''import re

html_file = 'app.html'

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

print("Removing ALL old date filter code...")

# Remove HTML containers
patterns = [
    r'<!-- Date Filters -->.*?(?=<div class="flex gap-2 overflow-x-auto pb-2 no-scrollbar" id="chip-container">)',
    r'<div[^>]*id="date-filter-container"[^>]*>.*?</div>\\s*',
]

for pattern in patterns:
    html = re.sub(pattern, '', html, flags=re.DOTALL)

# Remove CSS
html = re.sub(r'\\.date-filter-btn\\s*\\{[^}]*\\}\\s*', '', html)
html = re.sub(r'\\.date-filter-btn\\.active\\s*\\{[^}]*\\}\\s*', '', html)
html = re.sub(r'\\.date-filter-btn:hover:not\\(\\.active\\)\\s*\\{[^}]*\\}\\s*', '', html)

# Remove old JS
html = re.sub(r'let currentDateFilter[^;]+;\\s*', '', html)
html = re.sub(r'function setDateFilter\\([^)]*\\)\\s*\\{[^}]*\\}\\s*', '', html)
html = re.sub(r'function filterByDate\\([^)]*\\)\\s*\\{[^}]*\\}\\s*', '', html)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Done! Old date filters removed.")
''')
        
        print("✓ Created fix_duplicates_aggressive.py")
        print("\nRun it:")
        print("  py fix_duplicates_aggressive.py")
        
    return True

if __name__ == "__main__":
    try:
        diagnose_duplicates()
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
