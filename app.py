#!/usr/bin/env python
import os
import fnmatch
import json
from pkgutil import get_data
import random
import requests
import sys
from ansible.parsing.vault import get_file_vault_secret
from termcolor import cprint, colored
from src.RetrieveRfApi import retrieve_ragflow_api_key
from src.FileManagement import FileState

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

DEBUG = True  # Add this line

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
            # print(f"Dataset with name '{dataset_name}' not found.") #Commented out because it is expected on first run
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
    """
    Modifies the parser configuration for a dataset.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        chunk_token_value (int): The new chunk token value.
        dataset_id (str): The ID of the dataset to modify.
    """
    if not dataset_id:
        cprint("Skipping parser modification because dataset ID is invalid.", "yellow")
        return

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


def get_all_document_ids(base_url, api_key, dataset_id, page_size=30, max_retries=3):
    """
    Retrieves all document IDs from a dataset, handling pagination and retries.

    Args:
        base_url (str): The base API address.
        dataset_id (str): The ID of the dataset.
        api_key (str): The API key for authorization.
        page_size (int): The number of documents per page. Defaults to 30.
        max_retries (int): The maximum number of retries. Defaults to 3.

    Returns:
        list: A list of all document IDs in the dataset.
    """
    all_document_ids = []
    page_number = 1
    retries = 0

    while True:
        url = f"http://{base_url}/api/v1/datasets/{dataset_id}/documents?page={page_number}&page_size={page_size}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
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
                if retries < max_retries:
                    retries += 1
                    print(f"Retrying in 5 seconds... (Attempt {retries}/{max_retries})")
                    sleep(5)
                    continue  # Retry the request
                else:
                    print("Max retries reached.  Returning empty list.")
                    return []  # Return an empty list to avoid further errors

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if retries < max_retries:
                retries += 1
                print(f"Retrying in 5 seconds... (Attempt {retries}/{max_retries})")
                sleep(5)
                continue  # Retry the request
            else:
                print("Max retries reached.  Returning empty list.")
                return []  # Return an empty list to avoid further errors
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


def update_document_metadata(base_url, api_key, dataset_id, document_id, metadata, file_path):
    """
    Updates the metadata of a specific document.

    Args:
        base_url (str): The base URL of the API.
        api_key (str): The API key for authorization.
        dataset_id (str): The ID of the dataset.
        document_id (str): The ID of the document to update.
        metadata (dict): The metadata to add to the document.
        file_path (str): The path to the file being processed.
    """
    url = f"http://{base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {"meta_fields": metadata}  # Changed 'metadata' to 'meta_fields'

    try:
        cprint(f"Updating document {document_id} metadata for {file_path} with: {metadata}", "blue")  # Add log
        response = requests.put(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()

        if result.get("code") == 0:
            cprint(f"Document {document_id} metadata updated successfully for {file_path}!", "green")
        else:
            cprint(
                f"Error updating document {document_id} metadata for {file_path}: {result.get('message')}",
                "red",
            )
            cprint(f"Response code: {result.get('code')}", "red")
            cprint(f"Response message: {result.get('message')}", "red")


    except requests.exceptions.RequestException as e:
        cprint(f"An error occurred during the API request for {file_path}: {e}", "red")
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
    global file_state  # Declare file_state as global
    file_state = FileState()  # Initialize FileState here
    DATASET_ID = get_dataset_id_by_name(BASE_URL, API_KEY, DATASET)

    if not DATASET_ID:
        cprint(f"Dataset '{DATASET}' not found. Creating...", "yellow")
        response_data = create_dataset(
            BASE_URL,
            API_KEY,
            DATASET,
            EMBEDDING_MODEL,
            CHUNK_METHOD,
            CHUNK_TOKEN_NUMBER,
        )
        if response_data:
            cprint("Dataset creation successful!", "green")
            DATASET_ID = get_dataset_id_by_name(BASE_URL, API_KEY, DATASET)  # Get the dataset ID after creating it
            sleep(5)  # Wait 5 seconds after creating the dataset
        else:
            cprint("Dataset creation failed.", "red")
            return  # Exit if dataset creation failed
    else:
        cprint(f"Dataset '{DATASET}' found with ID: {DATASET_ID}", "green")

    modify_parser(BASE_URL, API_KEY, CHUNK_TOKEN_NUMBER, DATASET_ID)

    files = get_files_with_extensions(IMPORT_DIR, FILE_EXTENSIONS)

    if DEBUG:
        files = files[:5]  # Limit to the first 5 files if DEBUG is True

    uploaded_files = False  # Flag to track if any files were uploaded

    for file in files:
        file_name = os.path.basename(file)

        if not file_state.should_upload(file):
            cprint(f"Skipping '{file_name}' as it already exists and is unchanged.", "yellow")
            continue

        response = upload_document(BASE_URL, API_KEY, DATASET_ID, file)

        if response:
            cprint(f"Upload of '{file_name}' successful!", "green")
            document_id = response.get("data", [{}])[0].get("id")  # Extract document ID from response
            if document_id:
                file_state.add_file(file, document_id)  # Add file to state with document ID
                sha1_hash = file_state.get_file_sha1(file)  # Get SHA1 hash of the file
                metadata = {"hash_value": {"sha1sum": sha1_hash}}
                update_document_metadata(BASE_URL, API_KEY, DATASET_ID, document_id, metadata, file)
            else:
                cprint(f"Could not extract document ID for '{file_name}'.", "red")
        else:
            cprint(f"Upload of '{file_name}' failed.", "red")

        uploaded_files = True  # Set flag to True if at least one file was uploaded

    if not uploaded_files:
        cprint("No new files were uploaded.", "cyan")
        return  # Exit if no files were uploaded

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
