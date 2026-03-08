"""
Reorder Discover Tab
=====================
Move "Curated Day Plans" section above "Activities & Attractions"
so people see it first
"""

import re

def reorder_discover_tab(template_file='phoenixville.html'):
    """
    Swap the order of sections in the Discover tab
    """
    
    print("="*60)
    print("REORDERING DISCOVER TAB SECTIONS")
    print("="*60)
    
    with open(template_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    print(f"\n>> File size: {len(html)} characters")
    
    # Find the renderDiscoverTab function
    if 'function renderDiscoverTab(' not in html:
        print("\nERROR: renderDiscoverTab function not found!")
        return False
    
    print("\n>> Found renderDiscoverTab function")
    
    # Check current order
    activities_pos = html.find('SECTION 1: ACTIVITIES')
    plans_pos = html.find('SECTION 2: CURATED PLANS')
    
    if activities_pos == -1 or plans_pos == -1:
        print("\n>> Can't find section markers")
        print(">> Looking for alternative patterns...")
        
        activities_pos = html.find('Activities & Attractions')
        plans_pos = html.find('Curated Day Plans')
        
        if activities_pos == -1 or plans_pos == -1:
            print("   ERROR: Can't find sections!")
            return False
    
    if activities_pos < plans_pos:
        print("\n>> Current order: Activities BEFORE Plans")
        print(">> Will swap them so Plans come first...")
    else:
        print("\n>> Plans already come before Activities!")
        print(">> No changes needed")
        return True
    
    # Find the renderDiscoverTab function and extract it
    func_start = html.find('function renderDiscoverTab(')
    if func_start == -1:
        print("ERROR: Can't find function start")
        return False
    
    # Find the end of the function
    brace_count = 0
    in_function = False
    func_end = func_start
    
    for i in range(func_start, len(html)):
        if html[i] == '{':
            brace_count += 1
            in_function = True
        elif html[i] == '}':
            brace_count -= 1
            if in_function and brace_count == 0:
                func_end = i + 1
                break
    
    function_body = html[func_start:func_end]
    
    # Now we need to find and swap the two sections within the function
    # Look for the two main HTML generation blocks
    
    # Pattern 1: Find "SECTION 1: ACTIVITIES" comment and its code
    activities_start = function_body.find('// SECTION 1: ACTIVITIES')
    if activities_start == -1:
        activities_start = function_body.find('Activities & Attractions')
        if activities_start == -1:
            print("ERROR: Can't find Activities section start")
            return False
        # Back up to find the html += line
        activities_start = function_body.rfind('html +=', 0, activities_start)
    
    # Find where Activities section ends (look for SECTION 2 or the closing of that html block)
    activities_end = function_body.find('// SECTION 2: CURATED PLANS', activities_start)
    if activities_end == -1:
        activities_end = function_body.find('Curated Day Plans', activities_start)
        if activities_end == -1:
            print("ERROR: Can't find where Activities section ends")
            return False
        # Back up to find html += before it
        activities_end = function_body.rfind("html += '</div></div>';", 0, activities_end)
        if activities_end != -1:
            activities_end += len("html += '</div></div>';")
    
    # Extract Activities section
    activities_section = function_body[activities_start:activities_end]
    
    # Pattern 2: Find Plans section
    plans_start = activities_end
    plans_end = function_body.find("container.innerHTML = html;", plans_start)
    
    if plans_end == -1:
        print("ERROR: Can't find Plans section end")
        return False
    
    # Extract Plans section (everything from activities_end to container.innerHTML)
    plans_section = function_body[plans_start:plans_end]
    
    # Now reconstruct the function with swapped sections
    new_function = function_body[:activities_start] + plans_section + activities_section + function_body[plans_end:]
    
    # Replace in HTML
    html = html[:func_start] + new_function + html[func_end:]
    
    print("\n>> Swapped sections!")
    print("   New order: Curated Plans -> Activities")
    
    # Save
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n>> Saved to {template_file}")
    
    print("\n" + "="*60)
    print("SUCCESS! Discover tab reordered")
    print("="*60)
    print("\nNew order:")
    print("  1. Curated Day Plans (people see this first!)")
    print("  2. Activities & Attractions")
    print("\nNext steps:")
    print("  1. Run: py weekly_update.py")
    print("  2. Upload app.html")
    print("  3. Check Discover tab - plans should be on top!")
    
    return True

if __name__ == "__main__":
    try:
        reorder_discover_tab()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
