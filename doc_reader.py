import requests
import json
from termcolor import cprint, colored
import os
from src.RetrieveRfApi import retrieve_ragflow_api_key

DATASET = "logseq_dataset"
API_KEY = retrieve_ragflow_api_key()
BASE_URL = "localhost:8989"


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
            cprint(f"Dataset with name '{dataset_name}' not found.", "red")
            return None
    except requests.exceptions.RequestException as e:
        cprint(f"An error occurred: {e}", "red")
        if "response" in locals() and response is not None:
            cprint(f"Response Status Code: {response.status_code}", "light_red")
            cprint(f"Response Content: {response.text}", "light_red")
        return None


def get_all_documents(base_url, api_key, dataset_id, page_size=30):
    """
    Retrieves all documents from a dataset.

    Args:
        base_url (str): The base API address.
        dataset_id (str): The ID of the dataset.
        api_key (str): The API key for authorization.
        page_size (int): The number of documents per page. Defaults to 30.

    Returns:
        list: A list of all documents in the dataset.
    """
    all_documents = []
    page_number = 1

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

                all_documents.extend(documents)

                if len(documents) < page_size:
                    break  # Less than a full page, likely the last page

                page_number += 1  # Go to the next page
            else:
                cprint("Error: Unexpected response format", "red")
                return None

        except requests.exceptions.RequestException as e:
            cprint(f"Request failed: {e}", "red")
            return None

    return all_documents


def print_document_info(document):
    """
    Prints the information for a single document with colored output.

    Args:
        document (dict): A dictionary containing document information.
    """
    cprint("--------------------------------------------------", "cyan")
    cprint(f"Document ID: {colored(document['id'], 'yellow')}", "cyan")
    cprint(f"File Name: {colored(document['name'], 'yellow')}", "cyan")
    cprint(f"Created At: {colored(document['created_at'], 'yellow')}", "cyan")
    cprint(f"Updated At: {colored(document['updated_at'], 'yellow')}", "cyan")

    metadata = document.get("metadata", {})
    if metadata:
        cprint("Metadata:", "cyan")
        for key, value in metadata.items():
            cprint(f"  {key}: {colored(value, 'green')}", "cyan")
    else:
        cprint("No metadata found for this document.", "cyan")


def main():
    dataset_id = get_dataset_id_by_name(BASE_URL, API_KEY, DATASET)
    if not dataset_id:
        return

    documents = get_all_documents(BASE_URL, API_KEY, dataset_id)
    if not documents:
        cprint("No documents found in the dataset.", "red")
        return

    for document in documents:
        print_document_info(document)


if __name__ == "__main__":
    main()
