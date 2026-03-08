"""
Add setCategory to Template
============================
Add the setCategory() function to phoenixville.html template
so it's included every time weekly_update.py runs
"""

import re

def add_set_category_to_template(template_file='phoenixville.html'):
    """
    Add setCategory() function to the template
    """
    
    print("="*60)
    print("ADDING setCategory() TO TEMPLATE")
    print("="*60)
    
    with open(template_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    print(f"\n>> File size: {len(html)} characters")
    
    # Check if setCategory already exists
    if 'function setCategory(' in html:
        print("\n>> setCategory() already exists in template!")
        
        # Verify it's correct
        start = html.find('function setCategory(')
        context = html[start:start+300]
        
        if 'renderContent()' in context:
            print("   >> Function looks correct!")
            return True
        else:
            print("   >> Function exists but may be incomplete")
            print("   >> Will replace it...")
            
            # Remove old version
            # Find the function boundaries
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
            
            # Remove it
            html = html[:start] + html[end:]
            print("   >> Removed old setCategory()")
    else:
        print("\n>> setCategory() NOT found in template")
        print(">> Will add it...")
    
    # Find insertion point - look for other similar functions
    insert_point = None
    insertion_marker = None
    
    # Try to find switchTab function
    if 'function switchTab(' in html:
        start = html.find('function switchTab(')
        # Find end of function
        brace_count = 0
        in_function = False
        
        for i in range(start, len(html)):
            if html[i] == '{':
                brace_count += 1
                in_function = True
            elif html[i] == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    insert_point = i + 1
                    insertion_marker = "after switchTab()"
                    break
    
    # If no switchTab, try updateTabButtons
    if insert_point is None and 'function updateTabButtons()' in html:
        start = html.find('function updateTabButtons()')
        brace_count = 0
        in_function = False
        
        for i in range(start, len(html)):
            if html[i] == '{':
                brace_count += 1
                in_function = True
            elif html[i] == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    insert_point = i + 1
                    insertion_marker = "after updateTabButtons()"
                    break
    
    # If still nothing, try renderChips
    if insert_point is None and 'function renderChips()' in html:
        insert_point = html.find('function renderChips()')
        insertion_marker = "before renderChips()"
    
    if insert_point is None:
        print("\n   ERROR: Can't find good insertion point!")
        print("   Looked for: switchTab, updateTabButtons, renderChips")
        return False
    
    print(f"\n>> Inserting {insertion_marker}")
    
    # Create the function
    set_category_function = '''
        function setCategory(cat) {
            currentFilter = cat;
            renderChips();
            renderContent();
        }
        
'''
    
    # Insert
    html = html[:insert_point] + set_category_function + html[insert_point:]
    
    print("   >> Added setCategory() function")
    
    # Save
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n>> Saved to {template_file}")
    print(f"   New size: {len(html)} characters")
    
    print("\n" + "="*60)
    print("SUCCESS! setCategory() added to template")
    print("="*60)
    print("\nNow the function will be included every time you run:")
    print("  py weekly_update.py")
    print("\nNext steps:")
    print("  1. Run: py weekly_update.py")
    print("  2. Upload app.html to Hostinger")
    print("  3. Test date filters - should work!")
    
    return True

if __name__ == "__main__":
    try:
        add_set_category_to_template()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
