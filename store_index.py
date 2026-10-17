from src.helper import repo_ingestion,load_repo,text_splitter,load_embeddings
from dotenv import load_dotenv
from langchain_chroma import Chroma
import os
import sys

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/sauravyadav7721/Telecom-Customer-Churn-Prediction"

repo_ingestion(url)

documents = load_repo("repo/")

text_chunks = text_splitter(documents)

embeddings = load_embeddings()

vectorstore = Chroma.from_documents(text_chunks, embeddings, persist_directory="./db")
