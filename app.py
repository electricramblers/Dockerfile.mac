#!/usr/bin/env python
import os
import fnmatch
import hashlib
import json
from pkgutil import get_data
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
NEW_PARSER_CONFIG = {"chunk_token_num": 512, "delimiter": "\\n!?;。;!?"}

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
        "chunk_method": chunk_method,
        "embedding_model": embedding_model,
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


def get_dataset_id_by_name(base_url, api_key, dataset_name):
    """
    Retrieves the dataset ID by its name.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        dataset_name (str): The name of the dataset to search for.

    Returns:
        str: The dataset ID if found, or None if not found or an error occurred.
    """
    url = f"http://{base_url}/api/v1/datasets?name={dataset_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data["code"] == 0 and data["data"]:
            # Assuming the API returns a list of datasets matching the name
            # Here we return the first dataset ID in the list.
            # You might want a more robust way to handle multiple matches.
            return data["data"][0]["id"]
        else:
            print(f"Dataset with name '{dataset_name}' not found.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if "response" in locals() and response is not None:
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
        return None


def update_dataset(base_url, api_key, dataset_name, new_name=None):
    """
    Updates a dataset's name by first looking up the dataset ID using the dataset name.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        dataset_name (str): The current name of the dataset to be updated.
        new_name (str, optional): The new name of the dataset. Defaults to None.

    Returns:
        dict: The JSON response from the API, or None if an error occurred.
    """
    dataset_id = get_dataset_id_by_name(base_url, api_key, dataset_name)
    if not dataset_id:
        print(f"Could not find dataset ID for name '{dataset_name}'.")
        return None

    url = f"http://{base_url}/api/v1/datasets/{dataset_id}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {}
    if new_name:
        data["name"] = new_name

    if not data:
        print("No update parameters provided.")
        return None

    try:
        response = requests.put(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if "response" in locals() and response is not None:
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
        return None


def modify_parser(base_url, api_key, chunk_token_value, dataset_id):
    url = f"http://{base_url}/api/v1/datasets/{dataset_id}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "parser_config": {
            "chunk_token_num": chunk_token_value,  # Your desired value
            "delimiter": "\\n!?;。;!?",  # Keep other existing config values
        }
    }
    try:
        response = requests.put(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()

        if result.get("code") == 0:
            cprint("Dataset parser_config updated successfully!", "green")
        else:
            cprint(
                f"Error updating dataset parser_config: {result.get('message')}", "red"
            )

    except requests.exceptions.RequestException as e:
        cprint(f"An error occurred during the API request: {e}", "red")
        if hasattr(e, "response") and e.response:
            cprint(f"Response Status Code: {e.response.status_code}", "light_red")
            cprint(f"Response Text: {e.response.text}", "light_red")


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

    DATASET_ID = get_dataset_id_by_name(BASE_URL, API_KEY, DATASET)

    modify_parser(BASE_URL, API_KEY, CHUNK_TOKEN_NUMBER, DATASET_ID)

    sys.exit()
    files = get_files_with_extensions(IMPORT_DIR, FILE_EXTENSIONS)
    file_state = load_file_state()  # Load file state _before_ the loop

    print("Finished processing files.")


if __name__ == "__main__":
    main()
