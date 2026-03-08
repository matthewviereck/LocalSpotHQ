import re

def remove_landing_page(input_file='phoenixville_updated.html', output_file='app.html'):
    """
    Remove the built-in landing page from phoenixville_updated.html
    so it goes straight to the app
    """
    
    print(f">> Reading {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: {input_file} not found!")
        print("Please run: py inject_data_verified.py first")
        return False
    
    print(f">> Original file size: {len(html)} characters")
    
    print(">> Step 1: Hiding landing page...")
    
    # 1. Hide the landing page by adding "hidden" class
    original_html = html
    html = html.replace(
        '<div id="landing-page" class="fixed inset-0',
        '<div id="landing-page" class="hidden fixed inset-0'
    )
    
    if html == original_html:
        print("   WARNING: Could not find landing-page div to hide!")
    else:
        print("   >> Landing page div hidden")
    
    print(">> Step 2: Showing main app...")
    
    # 2. Show the main app by removing "hidden" class
    original_html = html
    html = html.replace(
        '<div id="main-app" class="hidden min-h-screen',
        '<div id="main-app" class="min-h-screen'
    )
    
    if html == original_html:
        print("   WARNING: Could not find main-app div to show!")
    else:
        print("   >> Main app div shown")
    
    print(">> Step 3: Adding auto-load script...")
    
    # 3. Add auto-load script - look for the pattern more carefully
    # Find the last </script> before </body>
    pattern = r'([\s\S]*)(</script>\s*</body>)'
    
    auto_load_script = '''
        // Load content when page loads (since we're skipping the landing page)
        window.addEventListener('DOMContentLoaded', function() {
            console.log('Auto-loading content...');
            renderContent();
        });

    '''
    
    if re.search(pattern, html):
        html = re.sub(pattern, r'\1' + auto_load_script + r'\2', html)
        print("   >> Auto-load script added")
    else:
        print("   WARNING: Could not find </script></body> pattern!")
    
    # 4. Verify changes
    print("\n>> Verification:")
    verified = True
    
    if 'id="landing-page" class="hidden fixed' in html:
        print("   >> Landing page is hidden")
    else:
        print("   ERROR: Landing page NOT hidden!")
        verified = False
    
    if 'id="main-app" class="min-h-screen' in html and 'id="main-app" class="hidden min-h-screen' not in html:
        print("   >> Main app is visible")
    else:
        print("   ERROR: Main app NOT visible!")
        verified = False
    
    if "window.addEventListener('DOMContentLoaded'" in html or 'window.addEventListener("DOMContentLoaded"' in html:
        print("   >> Auto-load script present")
    else:
        print("   ERROR: Auto-load script NOT added!")
        verified = False
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n>> SUCCESS! Created {output_file}")
    print(f">> Output file size: {len(html)} characters")
    print("\n" + "="*60)
    if verified:
        print("ALL CHECKS PASSED!")
    else:
        print("SOME CHECKS FAILED - Review warnings above")
    print("="*60)
    print("\nNext step:")
    print("  Upload app.html to Hostinger")
    
    return verified

if __name__ == "__main__":
    success = remove_landing_page()
    if success:
        print("\n>> All done! Upload app.html to Hostinger.")
    else:
        print("\n>> Failed. Check errors above.")
