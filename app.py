"""
Exam Tutor — Serves the latest Clean Slate design HTML.
Auto-pulls from GitHub so the code lives in one central place.
"""

from flask import Flask, send_from_directory

app = Flask(__name__)

# The repo auto-pulls from GitHub into this directory
REPO_DIR = '/home/ubuntu/uniexams'

# index.html is a single self-contained file (inline CSS/JS, client-side-only
# nav, no local assets) — there is nothing else in REPO_DIR that should ever
# be served. A catch-all static route here would expose .git/, app.py, and
# pull.log to the public internet.
@app.route('/')
def index():
    return send_from_directory(REPO_DIR, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)
