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
        print("Please run: py update_localspot.py first")
        return False
    
    print(">> Removing landing page...")
    
    # 1. Hide the landing page by adding "hidden" class
    html = html.replace(
        '<div id="landing-page" class="fixed inset-0',
        '<div id="landing-page" class="hidden fixed inset-0'
    )
    
    # 2. Show the main app by removing "hidden" class
    html = html.replace(
        '<div id="main-app" class="hidden min-h-screen',
        '<div id="main-app" class="min-h-screen'
    )
    
    # 3. Add auto-load script at the end of the script section
    # Find the last </script> tag before </body>
    pattern = r'(\s+)(</script>\s*</body>)'
    replacement = r'\1\n        // Load content when page loads (since we\'re skipping the landing page)\n        window.addEventListener(\'DOMContentLoaded\', function() {\n            renderContent();\n        });\n\n    \2'
    
    html = re.sub(pattern, replacement, html)
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f">> SUCCESS! Created {output_file}")
    print(">> App now loads directly without landing page")
    print(">> Upload this file to Hostinger as app.html")
    
    return True

if __name__ == "__main__":
    remove_landing_page()
