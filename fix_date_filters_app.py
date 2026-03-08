"""
Fix Date Filters - For app.html
================================
This script adds proper date filtering to app.html
"""

import re

def fix_date_filters(input_file='app.html', output_file='app.html'):
    """
    Update app.html to add date filtering for Events tab
    """
    
    print("="*60)
    print("FIXING DATE FILTERS IN APP.HTML")
    print("="*60)
    
    print(f"\n>> Reading {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {input_file} not found!")
        print("\nMake sure you have app.html in the current directory.")
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
    
    # More flexible pattern - just find the function and replace all of it
    pattern1 = r'(function renderChips\(\) \{)([\s\S]*?)(\n        \})'
    
    new_render_chips_body = '''
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
'''
    
    if re.search(pattern1, html):
        html = re.sub(pattern1, r'\1' + new_render_chips_body + r'\3', html, count=1)
        print("   ✓ Updated renderChips() function")
    else:
        print("   ✗ Could not find renderChips() function!")
        print("   Trying alternative pattern...")
        
        # Alternative: look for just the start and find the closing brace
        if 'function renderChips() {' in html:
            print("   Found function declaration, attempting manual replacement...")
            # This is trickier - let's try a different approach
            # Find the function start
            start_idx = html.find('function renderChips() {')
            if start_idx != -1:
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
                    # Replace the entire function
                    new_function = 'function renderChips() {' + new_render_chips_body + '\n        }'
                    html = html[:start_idx] + new_function + html[end_idx+1:]
                    print("   ✓ Updated renderChips() function (manual method)")
                else:
                    print("   ✗ Could not find function end")
                    return False
        else:
            print("   ✗ Function not found at all!")
            return False
    
    # ============================================================
    # STEP 2: Update filterData() function
    # ============================================================
    print("\n>> Step 2: Updating filterData() function...")
    
    # Find filterData function
    if 'function filterData() {' in html:
        print("   Found filterData() function...")
        
        # Find the function start
        start_idx = html.find('function filterData() {')
        if start_idx != -1:
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
                
                html = html[:start_idx] + new_filter_data + html[end_idx+1:]
                print("   ✓ Updated filterData() function")
            else:
                print("   ✗ Could not find function end")
                return False
    else:
        print("   ✗ filterData() function not found!")
        return False
    
    # ============================================================
    # VERIFICATION
    # ============================================================
    print("\n>> Step 3: Verifying changes...")
    
    if html == original_html:
        print("   ✗ No changes were made!")
        return False
    
    if "'Tomorrow': 'tomorrow'" in html:
        print("   ✓ Date filter mapping found")
    else:
        print("   ✗ Date filter mapping NOT found")
        return False
    
    if "if (currentTab === 'events') {" in html and "const dateFilters = ['All', 'Tomorrow'" in html:
        print("   ✓ Events tab date filtering found")
    else:
        print("   ✗ Events tab date filtering NOT found")
        return False
    
    # ============================================================
    # SAVE
    # ============================================================
    print(f"\n>> Saving updated file to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   Output file size: {len(html)} characters")
    
    print("\n" + "="*60)
    print("✓ SUCCESS! Date filters added to app.html")
    print("="*60)
    print("\nThe Events tab will now show:")
    print("  • All Dates")
    print("  • Tomorrow")
    print("  • This Week")
    print("  • Next Week")
    print("  • This Month")
    print("  • Later")
    print("\n📤 NEXT STEP:")
    print("   Upload app.html to Hostinger → public_html/app.html")
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
