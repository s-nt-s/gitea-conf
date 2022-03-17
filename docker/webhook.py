from flask import Flask, request, json, jsonify
import json
from core.git import Gitea, GitException
import logging

app = Flask(__name__)

git = Gitea("http://localhost:3000/api/v1", '1911a20d79a731b20465eefab4dc38f65666fbb1')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    datefmt='%Y-%M-%d %H:%M:%S'
)


@app.route('/create', methods=['POST'])
def create():
    data = request.json
    if data.get('action') != 'created':
        return data.get('action')
    repo = data['repository']
    name = repo['full_name']
    ow, rp = name.split("/")
    try:
        git.config_repo(ow, rp)
    except GitException as e:
        return jsonify(str(e))
    return jsonify(data)

@app.route('/branch', methods=['POST'])
def branch():
    data = request.json
    repo = data['repository']
    name = repo['full_name']
    ow, rp = name.split("/")
    try:
        git.config_repo(ow, rp)
    except GitException as e:
        return jsonify(str(e))
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
