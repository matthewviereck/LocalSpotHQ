"""
Fix Date Filters - Robust Version
==================================
Uses manual function boundary detection for reliable updates
"""

import re

def find_function_boundaries(html, function_name):
    """
    Find the start and end index of a JavaScript function
    Returns (start_idx, end_idx) or (None, None) if not found
    """
    # Look for function declaration
    search_str = f'function {function_name}() {{'
    start_idx = html.find(search_str)
    
    if start_idx == -1:
        # Try alternative: function name = () =>
        search_str = f'const {function_name} = () => {{'
        start_idx = html.find(search_str)
    
    if start_idx == -1:
        return None, None
    
    # Find the matching closing brace
    brace_count = 0
    in_function = False
    end_idx = start_idx
    
    for i in range(start_idx, len(html)):
        if html[i] == '{':
            brace_count += 1
            in_function = True
        elif html[i] == '}':
            brace_count -= 1
            if in_function and brace_count == 0:
                end_idx = i
                break
    
    if end_idx > start_idx:
        return start_idx, end_idx + 1  # Include the closing brace
    
    return None, None

def fix_date_filters(input_file='phoenixville.html'):
    """
    Update phoenixville.html template to add date filtering
    """
    
    print("="*60)
    print("FIXING DATE FILTERS FOR EVENTS TAB")
    print("="*60)
    
    print(f"\n>> Reading {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {input_file} not found!")
        return False
    
    original_html = html
    
    # Check if already has proper date filtering
    if "'Tomorrow': 'tomorrow'" in html:
        print(">> Date filters already properly configured!")
        return True
    
    print(f">> Original file size: {len(html)} characters")
    
    # ============================================================
    # STEP 1: Update renderChips() function
    # ============================================================
    print("\n>> Step 1: Updating renderChips() function...")
    
    start, end = find_function_boundaries(html, 'renderChips')
    
    if start is None:
        print("   ✗ Could not find renderChips() function!")
        return False
    
    new_render_chips = '''function renderChips() {
            const chipContainer = document.getElementById('chip-container');
            
            // Hide chips for Discover tab - it has its own filter buttons
            if (currentTab === 'discover') {
                chipContainer.innerHTML = '';
                chipContainer.style.display = 'none';
                return;
            }
            
            chipContainer.style.display = 'flex';
            const data = getActiveData();
            
            // FOR EVENTS TAB: Show date filters instead of type filters
            if (currentTab === 'events') {
                const dateFilters = ['All', 'Tomorrow', 'This Week', 'Next Week', 'This Month', 'Later'];
                const html = dateFilters.map(filter => `
                    <button onclick="setCategory('${filter}')" 
                        class="px-4 py-2 rounded-full text-xs font-bold transition-all border whitespace-nowrap ${currentFilter === filter ? 'bg-blue-600 text-white border-blue-600 shadow-md transform scale-105' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}">
                        ${filter === 'All' ? 'All Dates' : filter}
                    </button>
                `).join('');
                chipContainer.innerHTML = html;
                return;
            }
            
            // For other tabs: show type/tag filters (original behavior)
            let categories = new Set();
            data.forEach(item => {
                if (item.type) categories.add(item.type);
                if (item.tags) item.tags.forEach(t => categories.add(t));
            });
            const list = ['All', ...categories];
            
            const html = list.map(cat => `
                <button onclick="setCategory('${cat}')" 
                    class="px-4 py-2 rounded-full text-xs font-bold transition-all border whitespace-nowrap ${currentFilter === cat ? 'bg-blue-600 text-white border-blue-600 shadow-md transform scale-105' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}">
                    ${cat}
                </button>
            `).join('');
            chipContainer.innerHTML = html;
        }'''
    
    html = html[:start] + new_render_chips + html[end:]
    print("   ✓ Updated renderChips() function")
    
    # ============================================================
    # STEP 2: Update filterData() function
    # ============================================================
    print("\n>> Step 2: Updating filterData() function...")
    
    start, end = find_function_boundaries(html, 'filterData')
    
    if start is None:
        print("   ✗ Could not find filterData() function!")
        print("   Searching for it manually...")
        
        # Debug: Show what functions we can find
        functions_found = []
        for line in html.split('\n'):
            if 'function ' in line and '() {' in line:
                functions_found.append(line.strip()[:50])
        
        if functions_found:
            print(f"   Found these functions:")
            for f in functions_found[:10]:  # Show first 10
                print(f"     - {f}")
        
        return False
    
    new_filter_data = '''function filterData() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const data = getActiveData();
            
            return data.filter(item => {
                const matchesText = 
                    item.title.toLowerCase().includes(query) || 
                    (item.loc && item.loc.toLowerCase().includes(query)) || 
                    (item.type ? item.type.toLowerCase().includes(query) : false) ||
                    (item.tags ? item.tags.join(' ').toLowerCase().includes(query) : false);
                
                let matchesCategory;
                
                // FOR EVENTS TAB: Filter by date_category field
                if (currentTab === 'events' && currentFilter !== 'All') {
                    // Map button labels to data field values
                    const filterMap = {
                        'Tomorrow': 'tomorrow',
                        'This Week': 'this_week',
                        'Next Week': 'next_week',
                        'This Month': 'this_month',
                        'Later': 'later'
                    };
                    matchesCategory = item.date_category === filterMap[currentFilter];
                } else {
                    // Original filtering for other tabs
                    matchesCategory = currentFilter === 'All' || 
                                            (item.type && item.type === currentFilter) || 
                                            (item.tags && item.tags.includes(currentFilter));
                }

                return matchesText && matchesCategory;
            });
        }'''
    
    html = html[:start] + new_filter_data + html[end:]
    print("   ✓ Updated filterData() function")
    
    # ============================================================
    # VERIFICATION
    # ============================================================
    print("\n>> Step 3: Verifying changes...")
    
    if html == original_html:
        print("   ✗ No changes were made!")
        return False
    
    changes = []
    
    if "'Tomorrow': 'tomorrow'" in html:
        print("   ✓ Date filter mapping found")
        changes.append("date_mapping")
    else:
        print("   ⚠ Date filter mapping NOT found")
    
    if "if (currentTab === 'events') {" in html and "const dateFilters = ['All', 'Tomorrow'" in html:
        print("   ✓ Events tab date filtering found")
        changes.append("events_filtering")
    else:
        print("   ⚠ Events tab date filtering NOT found")
    
    if len(changes) < 2:
        print("\n   ⚠ Some changes may be missing, but continuing...")
    
    # ============================================================
    # SAVE
    # ============================================================
    print(f"\n>> Saving updated {input_file}...")
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   Output file size: {len(html)} characters")
    print(f"   Size change: {len(html) - len(original_html):+d} characters")
    
    print("\n" + "="*60)
    print("✓ SUCCESS! Date filters fixed in template")
    print("="*60)
    print("\nThe Events tab will now show:")
    print("  • All Dates")
    print("  • Tomorrow")
    print("  • This Week")
    print("  • Next Week")
    print("  • This Month")
    print("  • Later")
    print("\n💡 NEXT STEPS:")
    print("   Run: py weekly_update.py")
    print("   (This will regenerate app.html with the date filters)")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = fix_date_filters()
        if not success:
            print("\n✗ Failed to fix date filters. Check errors above.")
            exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
