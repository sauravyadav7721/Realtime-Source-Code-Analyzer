import os
import shutil
import stat
from git import Repo

from langchain_text_splitters import RecursiveCharacterTextSplitter,Language
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_classic.memory import ConversationSummaryMemory
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_huggingface import HuggingFaceEmbeddings

def _force_remove(func, path, _exc):
    # git marks pack files read-only on Windows, which breaks rmtree
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clear_repo(repo_path="repo"):
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, onerror=_force_remove)


def repo_ingestion(repo_url):
    repo_path = "repo"
    clear_repo(repo_path)
    Repo.clone_from(repo_url, repo_path)


def load_repo(repo_path):
    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*.py",
        parser=LanguageParser(language=Language.PYTHON,parser_threshold=500),
    )
    documents = loader.load()
    return documents




def text_splitter(documents):
    text_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=2000,
        chunk_overlap=200,
    )
    text_chunks = text_splitter.split_documents(documents)
    return text_chunks


def load_embeddings():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return embeddings