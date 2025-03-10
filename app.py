#!/usr/bin/env python
import os
import fnmatch
import hashlib
import json
import random
import requests
import sys
from ansible.parsing.vault import get_file_vault_secret
from termcolor import cprint, colored
from src.RetrieveRfApi import retrieve_ragflow_api_key

from time import sleep

DATASET = "logseq_dataset"
API_KEY = retrieve_ragflow_api_key()
IMPORT_DIR = os.path.expandvars("${HOME}/LLM_RAG/Logseq")
BASE_URL = "localhost:8989"
FILE_EXTENSIONS = [
    ".md",
    ".txt",
    ".docx",
    ".pptx",
    ".xlsx",
    ".eml",
    ".json",
    ".htm",
    ".html",
]
FILE_STATE_PATH = "file_state.json"
# EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-aL6-v2"
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_METHOD = "naive"  # same as general
CHUNK_TOKEN_NUMBER = 512


# -------------------------------------------------------------------------------
# HTTP API STUFF
# -------------------------------------------------------------------------------


def create_dataset(
    base_url, api_key, dataset_name, embedding_model, chunk_method, chunk_token_number
):
    """
    Creates a dataset using the provided parameters via a Python request.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        dataset_name (str): The name of the dataset to be created.
        chunk_token_number (int): The chunk token number for the parser configuration.

    Returns:
        dict: The JSON response from the API, or None if an error occurred.
    """
    url = f"http://{base_url}/api/v1/datasets"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "name": dataset_name,
        "chunk_method": "naive",
        "embedding_model": embedding_model,
        "parser_config": {
            "chunk_token_num": chunk_token_number,
            "delimiter": "\\n!?;。;!?",
            "html4excel": False,
            "layout_recognize": True,
            "raptor": {"user_raptor": False},
        },
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if "response" in locals() and response is not None:
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
        return None


# -------------------------------------------------------------------------------
# Get Files
# -------------------------------------------------------------------------------


def get_files_with_extensions(directory, file_extensions):
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in FILE_EXTENSIONS):
                absolute_path = os.path.abspath(os.path.join(root, file))
                matching_files.append(absolute_path)
    return matching_files


# -------------------------------------------------------------------------------
# File State
# -------------------------------------------------------------------------------


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


# -------------------------------------------------------------------------------
# HERE BE DRAGONS
# -------------------------------------------------------------------------------


def main():

    response_data = create_dataset(
        BASE_URL, API_KEY, DATASET, EMBEDDING_MODEL, CHUNK_METHOD, CHUNK_TOKEN_NUMBER
    )
    if response_data:
        cprint("Dataset creation successful!", "green")
        # print("Response:", json.dumps(response_data, indent=4))
    else:
        cprint("Dataset creation failed.", "red")

    files = get_files_with_extensions(IMPORT_DIR, FILE_EXTENSIONS)
    file_state = load_file_state()  # Load file state _before_ the loop

    print("Finished processing files.")


if __name__ == "__main__":
    main()
