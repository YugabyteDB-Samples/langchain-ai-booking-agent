from flask import Flask, jsonify, request
from agent import handle_agent_input
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

# Home route
@app.route('/')
def home():
    return "Welcome to the REST Server running on port 8000!"

# A simple API route
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    result = handle_agent_input(data['input_val'])
    response = {"output": result["output"]}
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=3000, debug=True)
