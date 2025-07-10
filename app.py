# app.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify(msg="Hello, world!")

@app.route('/health')
def health():
    return jsonify(status="ok")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
