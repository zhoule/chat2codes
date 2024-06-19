import openai
import os
import pathspec
import subprocess
from langchain.document_loaders import TextLoader
# from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams
from dotenv import load_dotenv

load_dotenv()
# Set the OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.api_base = os.environ.get("OPENAI_API_BASE")

def clone_repository(repo_url, local_path):
    """Clone the specified git repository to the given local path."""
    subprocess.run(["git", "clone", repo_url, local_path])

def load_docs(root_dir, file_extensions=None):
    """
    Load documents from the specified root directory.
    Ignore dotfiles, dot directories, and files that match .gitignore rules.
    Optionally filter by file extensions.
    """
    docs = []

    # Load .gitignore rules
    gitignore_path = os.path.join(root_dir, ".gitignore")

    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as gitignore_file:
            gitignore = gitignore_file.read()
        spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, gitignore.splitlines()
        )
    else:
        spec = None

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove dot directories from the list of directory names
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for file in filenames:
            file_path = os.path.join(dirpath, file)

            # Skip dotfiles
            if file.startswith("."):
                continue

            # Skip files that match .gitignore rules
            if spec and spec.match_file(file_path):
                continue

            if file_extensions and os.path.splitext(file)[1] not in file_extensions:
                continue

            try:
                loader = TextLoader(file_path, encoding="utf-8")
                docs.extend(loader.load_and_split())
            except Exception:
                pass
    return docs

def split_docs(docs):
    """Split the input documents into smaller chunks."""
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    return text_splitter.split_documents(docs)

def process(repo_url, include_file_extensions, qdrant_collection_name, repo_destination):
    """
    Process a git repository by cloning it, filtering files, splitting documents,
    creating embeddings, and storing everything in a Qdrant collection.
    """
    clone_repository(repo_url, repo_destination)

    docs = load_docs(repo_destination, include_file_extensions)
    texts = split_docs(docs)

    embeddings = OpenAIEmbeddings()

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    qdrant_client = QdrantClient(url=qdrant_url, timeout=60)
    qdrant_client.recreate_collection(
        collection_name=qdrant_collection_name,
        vectors_config=VectorParams(size=1536, distance="Cosine")  # Manually specify the vector size and distance
    )

    # client = QdrantClient(url=qdrant_url)
    db = Qdrant(client=qdrant_client, collection_name=qdrant_collection_name, embeddings=embeddings)
    db.add_documents(texts)
