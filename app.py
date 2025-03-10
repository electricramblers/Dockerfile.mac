#!/usr/bin/env python
import os
import fnmatch
import hashlib
import json
import random
import sys
from ansible.parsing.vault import get_file_vault_secret
from termcolor import cprint, colored
from src.RetrieveRfApi import retrieve_ragflow_api_key
from ragflow_sdk import RAGFlow
from ragflow_sdk.modules.dataset import DataSet
from time import sleep

DATASET = "logseq_dataset"
API_KEY = retrieve_ragflow_api_key()
IMPORT_DIR = os.path.expandvars("${HOME}/LLM_RAG/Logseq")
BASE_URL = "http://localhost:8989"
FILE_EXTENSIONS = [".md", ".txt", ".docx", ".pptx", ".xlsx"]
FILE_STATE_PATH = "file_state.json"
# EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-aL6-v2"
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_METHOD = "naive"  # same as general
CHUNK_TOKEN_NUMBER = 512
PARSER_CONFIG = {
    "chunk_token_num": CHUNK_TOKEN_NUMBER,
    "delimiter": "\\n!?;。;!?",
    "html4excel": False,
    "layout_recognize": True,
    "raptor": {"user_raptor": False},
}


def get_files_with_extensions(directory, file_extensions):
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in FILE_EXTENSIONS):
                absolute_path = os.path.abspath(os.path.join(root, file))
                matching_files.append(absolute_path)
    return matching_files


def calculate_sha1(file_path):
    """Calculate the SHA1 hash of a file."""
    hasher = hashlib.sha1()
    try:
        with open(file_path, "rb") as file:
            while chunk := file.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        cprint(f"Error: File not found at {file_path}", "red")
        return None  # Or raise the exception, depending on desired behavior
    except Exception as e:
        cprint(f"Error calculating SHA1 for {file_path}: {e}", "red")
        return None


def load_file_state(file_path=FILE_STATE_PATH):
    """Load the file state from a JSON file."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
    except json.JSONDecodeError:
        cprint(
            f"Error: Could not decode JSON from {file_path}.  Returning empty dict.",
            "red",
        )
        return {}
    except Exception as e:
        cprint(f"Error loading file state from {file_path}: {e}", "red")
        return {}
    return {}


def save_file_state(file_state, file_path=FILE_STATE_PATH):
    """Save the file state to a JSON file."""
    try:
        with open(file_path, "w") as f:
            json.dump(file_state, f, indent=4)
    except Exception as e:
        cprint(f"Error saving file state to {file_path}: {e}", "red")


def main():
    IDS = []
    # -------------------------------------------------------------------------------
    # Create Datast
    # -------------------------------------------------------------------------------
    client = RAGFlow(api_key=f"{API_KEY}", base_url=BASE_URL)
    try:
        dataset = client.create_dataset(
            name=f"{DATASET}",
            embedding_model=EMBEDDING_MODEL,
            chunk_method=CHUNK_METHOD,
            parser_config=DataSet.ParserConfig(**PARSER_CONFIG),
        )
    except Exception as e:
        print(f"Error creating dataset: {e}")
        datasets = client.list_datasets(name=f"{DATASET}")
        if datasets:
            dataset = datasets[0]
        else:
            print("No datasets found, exiting.")
            return

    files = get_files_with_extensions(IMPORT_DIR, FILE_EXTENSIONS)
    file_state = load_file_state()  # Load file state _before_ the loop

    for file in files:
        file_name = os.path.basename(file)
        file_hash = calculate_sha1(file)

        if file_hash is None:
            cprint(f"Skipping {file_name} due to hashing error.", "red")
            continue

        if file in file_state and file_state[file] == file_hash:
            cprint(f"Skipping duplicate file: {file_name}", "yellow")
            continue

        try:
            with open(file, "rb") as f:
                file_content = f.read()
        except Exception as e:
            cprint(f"Error reading file {file_name}: {e}", "red")
            continue  # Skip to the next file

        try:
            cprint(f"Uploading file: {file_name}", "green")
            dataset.upload_documents(
                [
                    {
                        "display_name": f"{file_name}",
                        "blob": file_content.decode(
                            "utf-8", "ignore"
                        ),  # Decode bytes to string
                    },
                ]
            )
            file_state[file] = file_hash  # Update state _after_ successful upload
            save_file_state(file_state)

        except Exception as e:
            cprint(f"Error uploading file {file_name}: {e}", "red")
            continue  # Skip to the next file

    print("Finished processing files.")


if __name__ == "__main__":
    main()
