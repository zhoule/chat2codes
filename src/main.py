import argparse
import os
import sys
from dotenv import load_dotenv
from streamlit.web import cli as stcli
from utils.process import process

# Load environment variables from a .env file (containing OPENAI_API_KEY)
load_dotenv()

def extract_repo_name(repo_url):
    """Extract the repository name from the given repository URL."""
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    return repo_name

def process_repo(args):
    """
    Process the git repository by cloning it, filtering files, and
    creating a Qdrant collection with the contents.
    """
    repo_name = extract_repo_name(args.repo_url)

    if not args.qdrant_collection_name:
        args.qdrant_collection_name = repo_name

    process(
        args.repo_url,
        args.include_file_extensions,
        args.qdrant_collection_name,
        args.repo_destination,
    )

def chat(args):
    """
    Start the Streamlit chat application using the specified Qdrant collection.
    """
    sys.argv = [
        "streamlit",
        "run",
        "src/utils/chat.py",
        "--",
        f"--qdrant_collection_name={args.qdrant_collection_name}",
    ]

    sys.exit(stcli.main())

def main():
    """Define and parse CLI arguments, then execute the appropriate subcommand."""
    parser = argparse.ArgumentParser(description="Chat with a git repository")
    subparsers = parser.add_subparsers(dest="command")

    # Process subcommand
    process_parser = subparsers.add_parser("process", help="Process a git repository")
    process_parser.add_argument(
        "--repo-url", required=True, help="The git repository URL"
    )
    process_parser.add_argument(
        "--include-file-extensions",
        nargs="+",
        default=None,
        help=(
            "Include only files with these extensions. Example:"
            " --include-file-extensions .py .js .ts .html .css .md .txt"
        ),
    )
    process_parser.add_argument(
        "--qdrant_collection_name",
        help=(
            "The name for the Qdrant collection. Defaults to the repository name."
        ),
    )
    process_parser.add_argument(
        "--repo-destination",
        default=".",
        help="The local path to clone the repository into. Defaults to current directory.",
    )
    process_parser.set_defaults(func=process_repo)

    # Chat subcommand
    chat_parser = subparsers.add_parser("chat", help="Start the chat application")
    chat_parser.add_argument(
        "--qdrant_collection_name", required=True, help="The Qdrant collection name to use"
    )
    chat_parser.set_defaults(func=chat)

    # Parse arguments and call the appropriate function
    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
