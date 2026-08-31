"""Emit the community board into an area's build output.

The deploy rsyncs output/<area>/ with --delete, so anything not written into
the build directory is removed from the server on the next run. The board's
PHP therefore has to be emitted here rather than uploaded once by hand.

Storage lives above the docroot (see community.php); only the scripts ship.
"""

import os
import shutil

_WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')

FILES = ['community.php', 'community_moderate.php']


def emit_community(output_dir, area_config):
    """Copy the board scripts into output_dir, substituting area tokens."""
    name = (area_config or {}).get('name', '')
    slug = (area_config or {}).get('slug', '')
    written = []
    for fname in FILES:
        src = os.path.join(_WEB, fname)
        if not os.path.exists(src):
            print(f"   WARNING: {fname} missing from web/ - board will 404")
            continue
        with open(src, 'r', encoding='utf-8') as f:
            php = f.read()
        php = php.replace('{{AREA_NAME}}', name).replace('{{AREA_SLUG}}', slug)
        dest = os.path.join(output_dir, fname)
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(php)
        written.append(fname)
    print(f">> Community board: {len(written)} file(s) -> {output_dir}")
    return written
