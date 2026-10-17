from langchain_chroma import Chroma
from src.helper import load_embeddings, repo_ingestion, load_repo, text_splitter, clear_repo
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify,render_template
from langchain_groq import ChatGroq
from langchain_classic.memory import ConversationSummaryMemory
from langchain_classic.chains import ConversationalRetrievalChain

app = Flask(__name__)
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

embeddings = load_embeddings()
persist_directory = "db"

vetordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

llm = ChatGroq(model = "openai/gpt-oss-120b",
    api_key=GROQ_API_KEY)

memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
qa = ConversationalRetrievalChain.from_llm(llm, vetordb.as_retriever(search_type="mmr",search_kwargs={"k":8}), memory=memory)

def clear_everything():
    # drop the cloned repo, its indexed chunks and the chat memory so a new repo can be loaded
    clear_repo()
    vetordb.reset_collection()
    memory.clear()
    return "Repository cleared. You can now submit a new GitHub URL."


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/chatbot", methods=["GET","POST"])
def gitRepo():

    if request.method != "POST":
        return jsonify({"response": "Send a GitHub URL via POST"}), 405

    user_input = request.form["question"].strip()
    if user_input.lower() == "clear":
        return jsonify({"response": clear_everything()})

    try:
        repo_ingestion(user_input)
        chunks = text_splitter(load_repo("repo/"))
        # replace the previous repo's chunks in the live store, no restart needed
        vetordb.reset_collection()
        vetordb.add_documents(chunks)
    except Exception as e:
        return jsonify({"response": f"Failed to index repo: {e}"}), 500
    return jsonify({"response": f"Indexed {len(chunks)} chunks from {user_input}"})


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    print(input)

    if input.strip().lower() == "clear":
        return clear_everything()

    result = qa(input)
    print(result['answer'])
    return str(result["answer"])


if __name__ == "__main__":
    app.run(debug=True, port=8080,host="0.0.0.0")