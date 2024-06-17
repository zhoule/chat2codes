import openai
import os
import pathspec
import subprocess
from langchain.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams
from dotenv import load_dotenv
import time

load_dotenv()
# Set the OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.api_base = os.environ.get("OPENAI_API_BASE")
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
openrouter_api_base = os.environ.get("OPENROUTER_API_BASE")
print(openai.api_key)
print(openai.api_base)

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
    """Split the input documents into smaller chunks and return as strings."""
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    split_docs = text_splitter.split_documents(docs)
    return [doc.page_content for doc in split_docs]

def process(repo_url, include_file_extensions, qdrant_collection_name, repo_destination):
    """
    Process a git repository by cloning it, filtering files, splitting documents,
    creating embeddings, and storing everything in a Qdrant collection.
    """
    process_incremental(repo_url, include_file_extensions, qdrant_collection_name, repo_destination)
def check_collection_exists(client, collection_name):
    try:
        collections = client.get_collections().collections
        return any(col.name == collection_name for col in collections)
    except Exception as e:
        print(f"Error checking collection existence: {e}")
        return False


def get_embeddings_with_retry(texts, embeddings, max_retries=3):
    for attempt in range(max_retries):
        try:
            return embeddings.embed_documents(texts)
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise


def process_incremental(repo_url, include_file_extensions, qdrant_collection_name, repo_destination):
    clone_repository(repo_url, repo_destination)
    docs = load_docs(repo_destination, include_file_extensions)
    texts = split_docs(docs)
    embeddings = OpenAIEmbeddings()

    qdrant_url = os.getenv("QDRANT_CLOUD_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    qdrant_client = QdrantClient(url="http://127.0.0.1:6333")

    if not check_collection_exists(qdrant_client, qdrant_collection_name):
        qdrant_client.recreate_collection(
            collection_name=qdrant_collection_name,
            vectors_config=VectorParams(size=1536, distance="Cosine")
        )

    db = Qdrant(client=qdrant_client, collection_name=qdrant_collection_name, embeddings=embeddings)

    # 获取嵌入向量并进行重试
    embeddings_vectors = get_embeddings_with_retry(texts, embeddings)

    # 将嵌入向量添加到Qdrant数据库
    db.add_documents(embeddings_vectors)