import re
import os


def remove_landing_page(input_file, output_file):
    """
    Post-process the injected HTML:
    - Hide the landing page overlay
    - Show the main app div
    - Add DOMContentLoaded auto-load script
    """
    print(f">> Reading {input_file}...")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"   ! Error: {input_file} not found!")
        return False

    print(f">> Original size: {len(html)} characters")

    # 1. Hide the landing page
    print(">> Hiding landing page...")
    original = html
    html = html.replace(
        '<div id="landing-page" class="fixed inset-0',
        '<div id="landing-page" class="hidden fixed inset-0'
    )
    if html != original:
        print("   Landing page hidden")
    else:
        print("   WARNING: Could not find landing-page div")

    # 2. Show the main app
    print(">> Showing main app...")
    original = html
    html = html.replace(
        '<div id="main-app" class="hidden min-h-screen',
        '<div id="main-app" class="min-h-screen'
    )
    if html != original:
        print("   Main app shown")
    else:
        print("   WARNING: Could not find main-app div")

    # 3. Add auto-load script
    print(">> Adding auto-load script...")
    auto_load_script = '''
        // Load content when page loads (since we're skipping the landing page)
        window.addEventListener('DOMContentLoaded', function() {
            console.log('Auto-loading content...');
            renderContent();
        });

    '''

    pattern = r'([\s\S]*)(</script>\s*</body>)'
    if re.search(pattern, html):
        html = re.sub(pattern, r'\1' + auto_load_script + r'\2', html)
        print("   Auto-load script added")
    else:
        print("   WARNING: Could not find </script></body> pattern")

    # 4. Save
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f">> Created {output_file} ({len(html)} characters)")
    return True


if __name__ == "__main__":
    remove_landing_page('phoenixville_updated.html', 'app.html')
