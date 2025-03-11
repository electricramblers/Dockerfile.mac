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


def upload_document(base_url, api_key, dataset_id, file_path):
    """
    Uploads a document to a specified dataset.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        dataset_id (str): The ID of the dataset to which the document will be uploaded.
        file_path (str): The path to the file to upload.

    Returns:
        dict: The JSON response from the API, or None if an error occurred.
    """
    url = f"http://{base_url}/api/v1/datasets/{dataset_id}/documents"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"file": (os.path.basename(file_path), open(file_path, "rb"))}

    try:
        files = {"file": (os.path.basename(file_path), open(file_path, "rb"))}
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if "response" in locals() and response is not None:
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
        return None
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def get_all_document_ids(base_url, api_key, dataset_id, page_size=30):
    """
    Retrieves all document IDs from a dataset, handling pagination.

    Args:
        address (str): The base API address.
        dataset_id (str): The ID of the dataset.
        api_key (str): The API key for authorization.
        page_size (int): The number of documents per page. Defaults to 30.

    Returns:
        list: A list of all document IDs in the dataset.
    """
    all_document_ids = []
    page_number = 1

    while True:
        url = f"http://{base_url}/api/v1/datasets/{dataset_id}/documents?page={page_number}&page_size={page_size}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()

        if "data" in data and "docs" in data["data"]:
            documents = data["data"]["docs"]

            if not documents:
                break  # No more documents, exit loop

            for doc in documents:
                all_document_ids.append(doc["id"])

            if len(documents) < page_size:
                break  # Less than a full page, likely the last page

            page_number += 1  # Go to the next page
        else:
            print("Error: Unexpected response format")
            break

    return all_document_ids


def parse_document(base_url, api_key, dataset_id, document_id):
    """Parses the specified document within a dataset.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        dataset_id (str): The ID of the dataset.
        document_id (str): The ID of the document to parse.

    Returns:
        dict: The JSON response from the API, or None if an error occurred.
    """
    url = f"http://{base_url}/api/v1/datasets/{dataset_id}/chunks"  # Corrected URL for parsing documents
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {"document_ids": [document_id]}  # Corrected data format

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}")
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
# Information Extraction
# -------------------------------------------------------------------------------


def extract_file_info(data):
    """
    Extracts and prints the filename and document ID from the given data.

    Args:
        data (dict): A dictionary containing file information.
    """
    if not isinstance(data, dict):
        print("Error: Input data must be a dictionary.")
        return

    if "data" not in data:
        print("Error: 'data' key not found in the dictionary.")
        return

    file_list = data["data"]

    if not isinstance(file_list, list):
        print("Error: 'data' field must be a list.")
        return

    for file_info in file_list:
        if not isinstance(file_info, dict):
            print("Error: Each item in 'data' list must be a dictionary.")
            continue  # Use continue, not return, to process the remaining items in the list if one fails

        if "name" not in file_info or "id" not in file_info:
            print("Error: 'name' or 'id' key not found in a file_info dictionary.")
            continue  # Use continue to proceed if any one is missing

        file_name = file_info["name"]
        document_id = file_info["id"]
        print(f"File Name: {file_name}, Document ID: {document_id}")


# -------------------------------------------------------------------------------
# HERE BE DRAGONS
# -------------------------------------------------------------------------------


def main():
    DATASET_ID = get_dataset_id_by_name(BASE_URL, API_KEY, DATASET)

    response_data = create_dataset(
        BASE_URL, API_KEY, DATASET, EMBEDDING_MODEL, CHUNK_METHOD, CHUNK_TOKEN_NUMBER
    )
    if response_data:
        cprint("Dataset creation successful!", "green")
    else:
        cprint("Dataset creation failed.", "red")

    modify_parser(BASE_URL, API_KEY, CHUNK_TOKEN_NUMBER, DATASET_ID)

    files = get_files_with_extensions(IMPORT_DIR, FILE_EXTENSIONS)
    file_state = load_file_state()

    for file in files:
        file_name = os.path.basename(file)
        file_hash = calculate_sha1(file)

        if file_hash is None:
            continue  # Skip to the next file if hash calculation failed

        if file_name in file_state and file_state[file_name] == file_hash:
            cprint(f"File '{file_name}' already up-to-date. Skipping.", "yellow")
            continue  # Skip upload if file is already up-to-date

        response = upload_document(BASE_URL, API_KEY, DATASET_ID, file)
        print(extract_file_info(response))
        sys.exit()
        if response:
            file_state[file_name] = file_hash  # Update file state
            save_file_state(file_state)  # Save updated file state
            cprint(f"Upload of '{file_name}' successful!", "green")
        else:
            cprint(f"Upload of '{file_name}' failed.", "red")

    document_id_list = get_all_document_ids(BASE_URL, API_KEY, DATASET_ID)

    for id in document_id_list:
        result = parse_document(BASE_URL, API_KEY, DATASET_ID, id)
        if result:
            cprint(f"ID Processed: {id}", "green")
        else:
            cprint("ID Failed to process.", "red")
        sleep(2)


if __name__ == "__main__":
    main()
