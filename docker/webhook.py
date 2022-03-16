from flask import Flask, request, json, jsonify
import json
from core.git import Gitea
import logging
import base64

app = Flask(__name__)

git = Gitea("http://localhost:3000/api/v1", '1911a20d79a731b20465eefab4dc38f65666fbb1')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    datefmt='%Y-%M-%d %H:%M:%S'
)

def new_content(name, email, dt, content, message='INIT'):
    content = content.encode('utf-8')
    content = base64.b64encode(content)
    content = content.decode('utf-8')
    data = {
        "author": {
            "email": email,
            "name": name,
        },
        "branch": "develop",
        "committer": {
            "email": email,
            "name": name,
        },
        "content": content,
        "dates": {
            "author": dt,
            "author": dt,
        },
        "message": message,
        "new_branch": "develop"
    }
    return data

@app.route('/create', methods=['POST'])
def create():
    data = request.json
    fl = "debug/{}_{}.json".format(data['action'], data['repository']['full_name'].replace("/", "_"))
    with open(fl, "w") as f:
        json.dump(data, f, indent=2)
    if data.get('action') != 'created':
        return data.get('action')
    repo = data['repository']
    name = repo['full_name']
    ow, rp = name.split("/")
    git.config_repo(ow, rp)
    return jsonify(data)

@app.route('/push', methods=['POST'])
def push():
    data = request.json
    repo = data['repository']
    name = repo['full_name']
    ow, rp = name.split("/")
    git.config_repo(ow, rp)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
