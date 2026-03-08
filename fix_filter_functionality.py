"""
Fix Filter Functionality
=========================
Make sure the date filters actually work by fixing filterData()
"""

import re

def fix_filter_functionality(html_file='app.html'):
    """
    Fix the filterData() function to properly filter by date_category
    """
    
    print("="*60)
    print("FIXING DATE FILTER FUNCTIONALITY")
    print("="*60)
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    print(f"\n>> File size: {len(html)} characters")
    
    # Check if filterData exists
    if 'function filterData()' not in html:
        print("ERROR: filterData() function not found!")
        return False
    
    print("\n>> Found filterData() function")
    
    # Check if it already has date_category filtering
    if "'Tomorrow': 'tomorrow'" in html and "item.date_category ===" in html:
        print(">> Date filtering already implemented!")
        print("\n>> Checking if it's inside filterData()...")
        
        # Extract filterData function
        start = html.find('function filterData()')
        if start == -1:
            print("   ERROR: Can't find function start")
            return False
        
        # Find the closing brace
        brace_count = 0
        in_function = False
        end = start
        
        for i in range(start, len(html)):
            if html[i] == '{':
                brace_count += 1
                in_function = True
            elif html[i] == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    end = i + 1
                    break
        
        function_body = html[start:end]
        
        if "'Tomorrow': 'tomorrow'" in function_body:
            print("   >> Date filtering IS in filterData() - function looks correct!")
            print("\n>> The filters should be working. Let me check the event data...")
            
            # Check if events have date_category field
            if '"date_category":' in html:
                print("   >> Events have date_category field")
                
                # Count how many events have each category
                categories = ['tomorrow', 'this_week', 'next_week', 'this_month', 'later']
                for cat in categories:
                    count = html.count(f'"date_category": "{cat}"')
                    print(f"      - {cat}: {count} events")
                
                if all(html.count(f'"date_category": "{cat}"') == 0 for cat in categories):
                    print("\n   WARNING: No events have date_category values!")
                    print("   This means transform_events.py didn't run properly.")
                    print("   Run: py weekly_update.py")
                else:
                    print("\n   >> Everything looks correct!")
                    print("\n   If filters still don't work, the issue might be:")
                    print("   1. Browser cache (try hard refresh: Ctrl+Shift+R)")
                    print("   2. JavaScript error (check browser console)")
            else:
                print("   ERROR: Events don't have date_category field!")
                print("   Run: py weekly_update.py to regenerate with proper data")
            
            return True
        else:
            print("   >> Date filtering NOT in filterData()")
            print("   >> Need to update the function...")
    else:
        print(">> Date filtering NOT implemented")
        print(">> Need to add it to filterData()...")
    
    # Need to replace filterData function
    print("\n>> Updating filterData() function...")
    
    # Find function boundaries
    start = html.find('function filterData()')
    if start == -1:
        print("   ERROR: Can't find function")
        return False
    
    # Find the closing brace
    brace_count = 0
    in_function = False
    end = start
    
    for i in range(start, len(html)):
        if html[i] == '{':
            brace_count += 1
            in_function = True
        elif html[i] == '}':
            brace_count -= 1
            if in_function and brace_count == 0:
                end = i + 1
                break
    
    if end <= start:
        print("   ERROR: Can't find function end")
        return False
    
    # Replace with new function
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
    
    print("   >> Updated filterData() function")
    
    # Save
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("\n" + "="*60)
    print("SUCCESS! Filter functionality fixed")
    print("="*60)
    print("\nNext steps:")
    print("  1. Upload app.html to Hostinger")
    print("  2. Hard refresh browser (Ctrl+Shift+R)")
    print("  3. Click date filter buttons - they should work now!")
    print("\nNote: There's no 'Today' button because events are categorized as:")
    print("  - Tomorrow")
    print("  - This Week")
    print("  - Next Week")
    print("  - This Month")
    print("  - Later")
    print("\nIf you want 'Today', you need to modify transform_events.py")
    
    return True

if __name__ == "__main__":
    try:
        fix_filter_functionality()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
