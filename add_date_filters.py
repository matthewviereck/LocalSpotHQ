import re

def add_date_filters(input_file='phoenixville.html', output_file='phoenixville.html'):
    """
    Add date filter buttons (Today, Tomorrow, This Week, All Dates) 
    above the category chips
    """
    
    print(">> Reading template...")
    with open(input_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Find where to insert date filters (before chip-container)
    search_pattern = r'(<div class="flex gap-2 overflow-x-auto pb-2 no-scrollbar" id="chip-container"></div>)'
    
    if not re.search(search_pattern, html):
        print("ERROR: Could not find chip-container!")
        return False
    
    # Date filter buttons HTML
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
    
    # Insert date filters before chip-container
    replacement = date_filters_html + r'\1'
    html = re.sub(search_pattern, replacement, html)
    
    print(">> Added date filter HTML")
    
    # Add CSS for date filter buttons (before closing </style>)
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
    
    # Insert CSS before closing </style>
    html = html.replace('    </style>', css + '    </style>')
    
    print(">> Added date filter CSS")
    
    # Add JavaScript for date filtering (before closing </script>)
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
    
    # Find the last function before </script>
    # Insert before the auto-load script if it exists, otherwise before </script>
    if "window.addEventListener('DOMContentLoaded'" in html:
        # Insert before DOMContentLoaded
        html = html.replace(
            "        // Load content when page loads",
            js + "        // Load content when page loads"
        )
    else:
        # Insert before </script>
        html = html.replace('    </script>\n</body>', js + '    </script>\n</body>')
    
    print(">> Added date filter JavaScript")
    
    # Update filterData() function to use date filtering
    # Find the filterData function and modify it
    old_filter_pattern = r'(function filterData\(\) \{[\s\S]*?const data = getActiveData\(\);[\s\S]*?return data\.filter\(item => \{)'
    
    if re.search(old_filter_pattern, html):
        # We need to add filterByDate() call
        # Find where data.filter() returns and add date filtering after
        
        # Actually, let's modify the end of filterData to apply date filter
        old_return = r'(function filterData\(\) \{[\s\S]*?\}\);[\s\S]*?\})'
        
        # This is complex, let's just add a note that filterByDate should be called
        # Actually, let's do it properly by replacing the filterData function
        
        filter_data_replacement = '''        function filterData() {
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
        
        # Replace the entire filterData function
        old_function = r'function filterData\(\) \{[^}]*\{[^}]*\}[^}]*\}[^}]*\}'
        html = re.sub(old_function, filter_data_replacement, html, count=1)
        
        print(">> Updated filterData() to include date filtering")
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f">> SUCCESS! Updated {output_file}")
    print("\nDate filter buttons added:")
    print("  - All Dates")
    print("  - Today")
    print("  - Tomorrow")
    print("  - This Week")
    print("\nThese will appear above category chips for Events tab only.")
    
    return True

if __name__ == "__main__":
    add_date_filters()
