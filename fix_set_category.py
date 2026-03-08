"""
Fix setCategory Function
=========================
The date filter buttons call setCategory() but it's not defined
"""

import re

def fix_set_category(html_file='app.html'):
    """
    Make sure setCategory() function exists and works
    """
    
    print("="*60)
    print("FIXING setCategory() FUNCTION")
    print("="*60)
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    print(f"\n>> File size: {len(html)} characters")
    
    # Check if setCategory exists
    if 'function setCategory(' in html:
        print("\n>> Found setCategory() function")
        
        # Find the function
        start = html.find('function setCategory(')
        if start != -1:
            # Get some context
            end = min(start + 500, len(html))
            context = html[start:end]
            print(f"\n   Function preview:")
            print(f"   {context[:200]}...")
            
            # Check if it calls renderContent
            if 'renderContent()' in context:
                print("\n   >> Function calls renderContent() - looks correct!")
                print("\n   The issue might be that setCategory is not in global scope.")
                print("   Let me check...")
                
                # Check if it's inside another function or script tag
                # Look backwards from setCategory to find context
                before_func = html[max(0, start-1000):start]
                
                if 'function ' in before_func and before_func.rfind('function ') > before_func.rfind('}'):
                    print("\n   WARNING: setCategory might be inside another function!")
                    print("   It needs to be at the global scope.")
                else:
                    print("\n   >> setCategory appears to be at global scope")
                    print("\n   Try these debugging steps:")
                    print("   1. In browser console, type: setCategory")
                    print("   2. If it says 'undefined', the function isn't loaded")
                    print("   3. If it shows 'function', try: setCategory('Tomorrow')")
            else:
                print("\n   WARNING: setCategory doesn't call renderContent()")
                print("   Need to fix the function...")
        
        return True
    else:
        print("\n>> setCategory() function NOT FOUND!")
        print(">> Need to create it...")
    
    # setCategory doesn't exist - we need to add it
    print("\n>> Adding setCategory() function...")
    
    # Find where to insert it - after switchTab or before renderContent
    insert_point = None
    
    # Look for function renderContent
    if 'function renderContent()' in html:
        insert_point = html.find('function renderContent()')
        print("   >> Will insert before renderContent()")
    elif 'function switchTab(' in html:
        # Find end of switchTab function and insert after
        start = html.find('function switchTab(')
        if start != -1:
            # Find the closing brace
            brace_count = 0
            for i in range(start, len(html)):
                if html[i] == '{':
                    brace_count += 1
                elif html[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        insert_point = i + 1
                        break
        print("   >> Will insert after switchTab()")
    
    if insert_point is None:
        print("   ERROR: Can't find good insertion point!")
        return False
    
    # Create the setCategory function
    set_category_function = '''
        function setCategory(cat) {
            currentFilter = cat;
            renderChips();
            renderContent();
        }
        
'''
    
    # Insert it
    html = html[:insert_point] + set_category_function + html[insert_point:]
    
    print("   >> Added setCategory() function")
    
    # Save
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("\n" + "="*60)
    print("SUCCESS! setCategory() function added")
    print("="*60)
    print("\nNext steps:")
    print("  1. Upload app.html to Hostinger")
    print("  2. Hard refresh (Ctrl+Shift+R)")
    print("  3. Test the date filters - should work now!")
    
    return True

if __name__ == "__main__":
    try:
        fix_set_category()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
