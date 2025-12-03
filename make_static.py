"""Create a cleaned static site in `public/` from the frozen `build/`.

This script copies `build/` -> `public/` and then sanitizes HTML files by:
- removing login banners that say "Please log in to access this page."
- removing <form>...</form> blocks (to avoid broken POSTs)
- removing hidden CSRF inputs

Run this locally before publishing; the resulting `public/` folder is
fully static and requires no Python to serve.
"""
import os
import shutil
import re

ROOT = os.path.dirname(__file__)
BUILD = os.path.join(ROOT, 'build')
PUBLIC = os.path.join(ROOT, 'public')


def copy_build():
    if os.path.exists(PUBLIC):
        shutil.rmtree(PUBLIC)
    shutil.copytree(BUILD, PUBLIC)


def sanitize_html_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remove login alert blocks that contain the phrase
    html = re.sub(r"<div class=\"alert alert-message\">.*?Please log in to access this page\..*?</div>", '', html, flags=re.S)

    # Remove any remaining CSRF hidden inputs
    html = re.sub(r"<input[^>]*name=\"csrf_token\"[^>]*>", '', html)

    # Remove form blocks (replace form with static div)
    def _form_repl(m):
        inner = m.group(1)
        # Keep inner text but remove inputs and buttons
        # Strip input elements
        inner = re.sub(r"<input[^>]*>", '', inner)
        inner = re.sub(r"<button[^>]*>.*?</button>", '', inner, flags=re.S)
        inner = re.sub(r"<textarea[^>]*>.*?</textarea>", '', inner, flags=re.S)
        return f"<div class=\"form-removed\">{inner}</div>"

    html = re.sub(r"<form[^>]*>(.*?)</form>", _form_repl, html, flags=re.S)

    # Remove any remaining placeholders that mention 'Default admin credentials'
    html = re.sub(r"<div class=\"login-footer\">.*?</div>", '', html, flags=re.S)

    # Ensure links to /static are relative to root (they already are),
    # so no further action required.

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)


def sanitize_all():
    for dirpath, _, filenames in os.walk(PUBLIC):
        for fn in filenames:
            if fn.lower().endswith('.html'):
                full = os.path.join(dirpath, fn)
                sanitize_html_file(full)


def main():
    if not os.path.exists(BUILD):
        print('Error: build/ not found. Run freeze.py first.')
        return

    print('Copying build/ -> public/')
    copy_build()
    print('Sanitizing HTML files in public/')
    sanitize_all()
    print('Static site ready in public/')


if __name__ == '__main__':
    main()
