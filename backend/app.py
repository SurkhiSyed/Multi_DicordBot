from flask import Flask, jsonify, request
from rag.rag_model import run_rag
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

app = Flask(__name__)

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "rag", "chroma")

@app.route('/api/echo', methods=['POST'])
def echo():
    data = request.json
    message = data.get('message', '')
    return jsonify({'response': f'Python says: {message}'})

@app.route('/api/rag', methods=['POST'])
def rag():
    data = request.json
    message = data.get('message', '')
    print(f"RAG endpoint called with: {message}")
    result = run_rag(message)
    print(f"RAG result: {result}")
    return jsonify(result)


@app.route('/api/debug', methods=['GET'])
def debug():
    print("CWD:", os.getcwd())
    print("CHROMA_PATH:", CHROMA_PATH)
    print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))
    return jsonify({
        "cwd": os.getcwd(),
        "chroma_path": CHROMA_PATH,
        "google_api_key": os.getenv("GOOGLE_API_KEY")
    })


if __name__ == '__main__':
    '''
    question = "What is all the scheduled events of training camp in PMAcclerator then?"
    result = run_rag(question)
    print("CWD:", os.getcwd())
    print("CHROMA_PATH:", CHROMA_PATH)
    print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))
    print(result)
    #CHROMA_PATH = "chroma"  # or your absolute path
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    print("Number of documents in DB:", db._collection.count())
    '''
    app.run(port=5000)
