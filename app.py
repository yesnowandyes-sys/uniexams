"""
Exam Tutor — Serves the latest Clean Slate design HTML.
Auto-pulls from GitHub so the code lives in one central place.
"""

import os
from flask import Flask, send_from_directory

app = Flask(__name__)

# The repo auto-pulls from GitHub into this directory
REPO_DIR = '/home/ubuntu/exam-tutor'

@app.route('/')
def index():
    return send_from_directory(REPO_DIR, 'index.html')

@app.route('/<path:filepath>')
def static_file(filepath):
    return send_from_directory(REPO_DIR, filepath)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=True)
