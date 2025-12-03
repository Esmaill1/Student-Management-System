# Deploying to Cloudflare Pages (static build)

This repository contains a Flask application. Cloudflare Pages is primarily a static site host. The included `freeze.py` uses `Frozen-Flask` to render the Flask views into a static `public/` directory which Cloudflare Pages can serve.

Important notes and limitations:
- Dynamic features (login, database-driven pages, CSV exports, etc.) will not function as interactive server-backed pages when deployed as static HTML. Pages that require authentication will generally redirect to the login page and freeze that login page HTML only.
- For a fully functional deployment (with login, APIs, and database), host the Flask app on a server (e.g., Render, Railway, Cloud Run) and use Cloudflare Pages only for the frontend or set up Cloudflare Workers to proxy to your backend.

Quick steps to deploy the static build to Cloudflare Pages:

1. On your machine (or in CI), install dependencies and run the freeze script locally to verify output:

```bash
python3 -m pip install -r requirements.txt
python3 freeze.py
```

2. Confirm a `build/` directory was created with static HTML and assets.

3. In the Cloudflare Pages dashboard, create a new project connected to this repository.

4. Set the build command to:

```
python3 -m pip install -r requirements.txt && python3 freeze.py
```

5. Set the output (publish) directory to:

```
build
```

6. Start the deployment. Monitor the build logs for any template errors — pages that rely on DB queries or logged-in users may raise exceptions during freezing and will be skipped or render the login page instead.

Optional improvements:
- Use a separate backend (hosted elsewhere) to provide APIs for dynamic content, then let Pages host the static frontend and call the backend via client-side JavaScript.
- Convert the app to an API + SPA model and host the backend with Cloudflare Workers or another serverless platform.

If you want, I can:
- Try running the freeze locally in this dev container and fix template issues that prevent freezing.
- Add extra generator functions in `freeze.py` to enumerate dynamic routes (e.g., for specific student/course IDs) if you provide a seed dataset.
