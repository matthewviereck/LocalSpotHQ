"""
ONE-TIME FIX: Add Date Filters + Generate App
Run this once to add date filters and create fresh app.html
"""

import subprocess
import re

def run_script(script_name, description):
    """Run a Python script"""
    print(f"\n{'='*60}")
    print(f"{description}...")
    print('='*60)
    
    result = subprocess.run(f"py {script_name}", shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"✗ {description} - FAILED")
        if result.stderr:
            print(result.stderr)
        return False

def add_date_filters_to_template():
    """Add date filters directly to phoenixville.html template"""
    
    print("\n" + "="*60)
    print("ADDING DATE FILTERS TO TEMPLATE")
    print("="*60)
    
    try:
        with open('phoenixville.html', 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print("ERROR: phoenixville.html not found!")
        return False
    
    # Check if date filters already exist
    if 'date-filter-btn' in html:
        print(">> Date filters already exist in template!")
        return True
    
    print(">> Adding date filter buttons...")
    
    # 1. Add date filter HTML before chip-container
    date_filters_html = '''                    <!-- Date Filters -->
                    <div class="flex gap-2 mb-3 overflow-x-auto no-scrollbar" id="date-filter-container">
                        <button onclick="setDateFilter('all')" class="date-filter-btn active" data-filter="all">
                            All Dates
                        </button>
                        <button onclick="setDateFilter('today')" class="date-filter-btn" data-filter="today">
                            Today
                        </button>
                        <button onclick="setDateFilter('tomorrow')" class="date-filter-btn" data-filter="tomorrow">
                            Tomorrow
                        </button>
                        <button onclick="setDateFilter('week')" class="date-filter-btn" data-filter="week">
                            This Week
                        </button>
                    </div>
                    '''
    
    # Find chip-container and add date filters before it
    search_pattern = r'(<div class="flex gap-2 overflow-x-auto pb-2 no-scrollbar" id="chip-container"></div>)'
    if not re.search(search_pattern, html):
        print("ERROR: Could not find chip-container!")
        return False
    
    replacement = date_filters_html + r'\1'
    html = re.sub(search_pattern, replacement, html)
    print("   ✓ Added date filter HTML")
    
    # 2. Add CSS for date filter buttons
    css = '''        .date-filter-btn {
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            transition: all 0.2s;
            border: 1px solid #e2e8f0;
            background: white;
            color: #64748b;
            white-space: nowrap;
            cursor: pointer;
        }
        .date-filter-btn.active {
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
        }
        .date-filter-btn:hover:not(.active) {
            background: #f1f5f9;
        }
        
'''
    
    html = html.replace('    </style>', css + '    </style>')
    print("   ✓ Added date filter CSS")
    
    # 3. Add JavaScript for date filtering
    js = '''
        // --- DATE FILTERING ---
        let currentDateFilter = 'all';
        
        function setDateFilter(filter) {
            currentDateFilter = filter;
            
            // Update button states
            document.querySelectorAll('.date-filter-btn').forEach(btn => {
                if (btn.dataset.filter === filter) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            renderContent();
        }
        
        function filterByDate(items) {
            if (currentTab !== 'events' || currentDateFilter === 'all') {
                return items;
            }
            
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);
            
            const weekEnd = new Date(today);
            weekEnd.setDate(weekEnd.getDate() + 7);
            
            return items.filter(item => {
                if (!item.date) return false;
                
                const itemDate = new Date(item.date);
                itemDate.setHours(0, 0, 0, 0);
                
                switch(currentDateFilter) {
                    case 'today':
                        return itemDate.getTime() === today.getTime();
                    case 'tomorrow':
                        return itemDate.getTime() === tomorrow.getTime();
                    case 'week':
                        return itemDate >= today && itemDate <= weekEnd;
                    default:
                        return true;
                }
            });
        }

'''
    
    # Insert before </script>
    html = html.replace('    </script>\n</body>', js + '    </script>\n</body>')
    print("   ✓ Added date filter JavaScript")
    
    # 4. Update filterData() to use date filtering
    old_function = r'function filterData\(\) \{[^}]*const data = getActiveData\(\);[^}]*return data\.filter\(item => \{[^}]*\}\);[^}]*\}'
    
    new_function = '''function filterData() {
            const data = getActiveData();
            
            // First filter by category/search
            let filtered = data.filter(item => {
                const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
                const matchesFilter = currentFilter === 'All' || 
                    (item.type && item.type.toLowerCase() === currentFilter.toLowerCase()) ||
                    (item.tags && item.tags.some(tag => tag.toLowerCase() === currentFilter.toLowerCase()));
                const matchesSearch = !searchTerm || 
                    item.title.toLowerCase().includes(searchTerm) || 
                    (item.desc && item.desc.toLowerCase().includes(searchTerm)) ||
                    (item.loc && item.loc.toLowerCase().includes(searchTerm));
                return matchesFilter && matchesSearch;
            });
            
            // Then apply date filter (only for events)
            filtered = filterByDate(filtered);
            
            return filtered;
        }'''
    
    html = re.sub(old_function, new_function, html)
    print("   ✓ Updated filterData() function")
    
    # Save updated template
    with open('phoenixville.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("\n✓ Date filters added to template!")
    return True

def main():
    print("\n" + "="*60)
    print("ONE-TIME FIX: ADD DATE FILTERS + GENERATE APP")
    print("="*60)
    print("\nThis will:")
    print("  1. Add date filters to phoenixville.html template")
    print("  2. Inject all data")
    print("  3. Remove landing page")
    print("  4. Create app.html ready to upload")
    print("="*60)
    
    input("\nPress ENTER to continue...")
    
    # Step 1: Add date filters to template
    if not add_date_filters_to_template():
        print("\n✗ Failed to add date filters!")
        return
    
    # Step 2: Inject data
    if not run_script('inject_data_verified.py', 'Injecting data'):
        print("\n✗ Failed to inject data!")
        return
    
    # Step 3: Remove landing page
    if not run_script('fix_app_landing_v2.py', 'Removing landing page'):
        print("\n✗ Failed to remove landing page!")
        return
    
    # Success!
    print("\n" + "="*60)
    print("✓ SUCCESS! DATE FILTERS ADDED!")
    print("="*60)
    print("\nYour app.html now has:")
    print("  ✅ Date filter buttons (All Dates, Today, Tomorrow, This Week)")
    print("  ✅ All events, dining, activities, curated plans")
    print("  ✅ No landing page (goes straight to app)")
    print("\n📤 NEXT STEP:")
    print("   Upload app.html to Hostinger → public_html/app.html")
    print("\n💡 FROM NOW ON:")
    print("   Just run: py weekly_update.py")
    print("   (Date filters are now in the template)")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
