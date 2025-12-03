import os
import logging
import shutil
from urllib.parse import unquote

# Import the Flask app instance
from webapp import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_get_routes():
    for rule in app.url_map.iter_rules():
        methods = {m for m in rule.methods if m not in ('HEAD', 'OPTIONS')}
        if 'GET' not in methods:
            continue
        # Skip static and parameterized routes
        if rule.endpoint == 'static' or rule.arguments:
            continue
        yield rule.rule


def prepare_output_dir(path='build'):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info('Created output directory: %s', path)


def write_response_to_path(build_root, url_path, content_bytes):
    # Normalize and map URL path -> directory/index.html
    # e.g. '/' -> build/index.html
    # '/students' -> build/students/index.html
    p = url_path.lstrip('/')
    p = unquote(p)
    if p == '':
        target_dir = build_root
    else:
        target_dir = os.path.join(build_root, p)

    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, 'index.html')
    with open(target_file, 'wb') as f:
        f.write(content_bytes)


def copy_static(build_root):
    static_src = app.static_folder
    if static_src and os.path.exists(static_src):
        dest = os.path.join(build_root, 'static')
        try:
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(static_src, dest)
            logger.info('Copied static files to %s', dest)
        except Exception:
            logger.exception('Failed to copy static files')


def main():
    build_root = os.path.abspath('build')
    prepare_output_dir(build_root)

    # Pre-create directories for top-level prefixes that have nested routes
    prefixes = set()
    routes = list(list_get_routes())
    for r in routes:
        parts = [p for p in r.split('/') if p]
        if len(parts) >= 2:
            prefixes.add(parts[0])

    for p in prefixes:
        dirpath = os.path.join(build_root, p)
        os.makedirs(dirpath, exist_ok=True)

    client = app.test_client()

    for url in sorted(set(routes)):
        try:
            logger.info('Requesting %s', url)
            resp = client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                write_response_to_path(build_root, url, resp.get_data())
                logger.info('Wrote %s', url)
            else:
                logger.warning('Skipping %s (status %s)', url, resp.status_code)
        except Exception:
            logger.exception('Error fetching %s', url)

    copy_static(build_root)
    logger.info('Static site generation complete. Output in %s', build_root)


if __name__ == '__main__':
    main()
