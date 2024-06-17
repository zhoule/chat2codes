import os

GITLAB_CONNECTOR_INCLUDE_CODE_FILES = (
    os.environ.get("GITLAB_CONNECTOR_INCLUDE_CODE_FILES", "").lower() == "true"
)

# Number of documents in a batch during indexing (further batching done by chunks before passing to bi-encoder)
try:
    INDEX_BATCH_SIZE = int(os.environ.get("INDEX_BATCH_SIZE", 16))
except ValueError:
    INDEX_BATCH_SIZE = 16


# notset, debug, info, warning, error, or critical
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")
