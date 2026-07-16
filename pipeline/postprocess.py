import re
import os
import shutil

TAILWIND_CDN_TAG = '<script src="https://cdn.tailwindcss.com"></script>'
PREBUILT_CSS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'app.css')


def swap_tailwind_cdn(html, output_dir):
    """Replace the Tailwind CDN JIT compiler (a large render-blocking script
    that compiles CSS in the browser on every visit) with the prebuilt static
    stylesheet from assets/app.css. Pipeline builds only - the PHP builder
    keeps the CDN tag until cutover. Regenerate the CSS after template edits:
        npx tailwindcss@3.4.17 --content templates/app_template.html -o assets/app.css --minify
    """
    if TAILWIND_CDN_TAG not in html:
        print("   WARNING: Tailwind CDN tag not found; leaving as-is")
        return html
    if not os.path.exists(PREBUILT_CSS):
        print("   WARNING: assets/app.css missing; keeping Tailwind CDN")
        return html
    shutil.copy(PREBUILT_CSS, os.path.join(output_dir, 'app.css'))
    print("   Tailwind CDN swapped for prebuilt app.css")
    return html.replace(TAILWIND_CDN_TAG, '<link rel="stylesheet" href="app.css">', 1)


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

    # 3. Add auto-load script as a standalone <script> immediately before </body>.
    # Using a dedicated <script> tag (instead of appending into an existing one)
    # keeps this robust against trailing markup between the last </script> and </body>
    # (e.g. a build-timestamp footer).
    print(">> Adding auto-load script...")
    auto_load_script = (
        '\n    <script>\n'
        '        // Auto-load content (landing page is skipped on built output)\n'
        '        window.addEventListener("DOMContentLoaded", function() {\n'
        '            console.log("Auto-loading content...");\n'
        '            if (typeof renderContent === "function") renderContent();\n'
        '        });\n'
        '    </script>\n'
    )

    if '</body>' in html:
        html = html.replace('</body>', auto_load_script + '</body>', 1)
        print("   Auto-load script added before </body>")
    else:
        print("   WARNING: Could not find </body>; appending auto-load script at end")
        html += auto_load_script

    # 4. Prebuilt CSS instead of the in-browser Tailwind compiler
    print(">> Swapping Tailwind CDN for prebuilt CSS...")
    html = swap_tailwind_cdn(html, os.path.dirname(output_file) or '.')

    # 5. Save
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f">> Created {output_file} ({len(html)} characters)")
    return True


if __name__ == "__main__":
    remove_landing_page('phoenixville_updated.html', 'app.html')
