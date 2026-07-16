import os
import shutil

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'pwa')

ICONS = ['icon-192.png', 'icon-512.png', 'icon-180.png']


def emit_pwa_assets(output_dir, config):
    """Copy the PWA assets (manifest, service worker, icons) into an area's
    output directory, substituting area placeholders in the manifest. The
    template links these relatively, so each area gets its own installable
    scope (/phoenixville/, /west-chester/, ...)."""
    area_name = config['name']

    with open(os.path.join(ASSETS_DIR, 'manifest.webmanifest'), 'r', encoding='utf-8') as f:
        manifest = f.read().replace('{{AREA_NAME}}', area_name)
    with open(os.path.join(output_dir, 'manifest.webmanifest'), 'w', encoding='utf-8') as f:
        f.write(manifest)

    shutil.copy(os.path.join(ASSETS_DIR, 'sw.js'), os.path.join(output_dir, 'sw.js'))
    for icon in ICONS:
        shutil.copy(os.path.join(ASSETS_DIR, icon), os.path.join(output_dir, icon))

    print(f">> PWA assets: manifest + sw.js + {len(ICONS)} icons -> {output_dir}")
