"""
Fix Date Filters - Final Version
=================================
This script adds proper date filtering to the Events tab that matches
the date_category values in events_formatted.json

The events have these categories:
- tomorrow
- this_week  
- next_week
- this_month
- later

But the app needs filter buttons for them!
"""

import re

def fix_date_filters(template_file='phoenixville.html'):
    """
    Update phoenixville.html template to add date filtering
    that works with the date_category field in events
    """
    
    print("="*60)
    print("FIXING DATE FILTERS FOR EVENTS TAB")
    print("="*60)
    
    print(f"\n>> Reading {template_file}...")
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {template_file} not found!")
        return False
    
    # Check if already has proper date filtering
    if "'Tomorrow': 'tomorrow'" in html:
        print(">> Date filters already properly configured!")
        return True
    
    print("\n>> Step 1: Updating renderChips() function...")
    
    # Find and replace renderChips() function
    old_render_chips = r'function renderChips\(\) \{[\s\S]*?chipContainer\.innerHTML = html;[\s\S]*?\}'
    
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
    
    if re.search(old_render_chips, html):
        html = re.sub(old_render_chips, new_render_chips, html, count=1)
        print("   ✓ Updated renderChips() function")
    else:
        print("   ✗ Could not find renderChips() function!")
        return False
    
    print("\n>> Step 2: Updating filterData() function...")
    
    # Find and replace filterData() function
    old_filter_data = r'function filterData\(\) \{[\s\S]*?return data\.filter\(item => \{[\s\S]*?\}\);[\s\S]*?\}'
    
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
    
    if re.search(old_filter_data, html):
        html = re.sub(old_filter_data, new_filter_data, html, count=1)
        print("   ✓ Updated filterData() function")
    else:
        print("   ✗ Could not find filterData() function!")
        return False
    
    # Save updated template
    print(f"\n>> Saving updated {template_file}...")
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
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
    print("\nThese match the date_category values in your events data.")
    print("\n💡 NEXT STEPS:")
    print("   1. Run: py inject_data_verified.py")
    print("   2. Run: py fix_app_landing_v2.py")
    print("   3. Upload app.html to Hostinger")
    print("\nOr just run: py weekly_update.py")
    print("(The fix is now in the template)")
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
