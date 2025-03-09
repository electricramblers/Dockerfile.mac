#!/usr/bin/env python
import os
import fnmatch
from ansible.parsing.vault import get_file_vault_secret
from termcolor import cprint
from src.RetrieveRfApi import retrieve_ragflow_api_key
from src.CreateDataset import RAGFlowClient
from ragflow_sdk import RAGFlow

_dataset = "logseq_dataset"
_rf_api_key = retrieve_ragflow_api_key()
_importDir = os.path.expandvars("${HOME}/LLM_RAG/Logseq")
_base_url = "http://localhost"

_fileExtensions = [
    ".md",
    ".docx",
    ".pdf",
    ".txt",
]


def get_files_with_extensions(directory, file_extensions):
    """
    Recursively reads a directory and creates a list of absolute filenames
    of files with the specified extensions.

    :param directory: The directory to search.
    :param file_extensions: A list of file extensions to filter by.
    :return: A list of absolute filenames with the specified extensions.
    """
    matching_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                absolute_path = os.path.abspath(os.path.join(root, file))
                matching_files.append(absolute_path)

    return matching_files


def upload_file_to_ragflow(
    file_path: str,
    dataset_name: str,
    api_key: str,
    base_url: str = "http://localhost:9380",
):
    """
    Uploads a file to a local RAGFlow instance.

    Args:
        file_path (str): The absolute path to the file to upload.
        dataset_name (str): The name of the dataset to which the file will be uploaded.
        api_key (str): The API key for authentication.
        base_url (str): The base URL of the local RAGFlow instance. Defaults to "http://localhost:9380".
    """
    try:
        # Initialize the RAGFlow client
        rag_object = RAGFlow(api_key=api_key, base_url=base_url)

        # Create or retrieve the dataset
        datasets = rag_object.list_datasets(name=dataset_name)
        if datasets:
            dataset = datasets[0]
        else:
            dataset = rag_object.create_dataset(name=dataset_name)

        # Read the file content
        with open(file_path, "rb") as file:
            file_content = file.read()

        # Prepare the document for upload
        document = {
            "display_name": file_path.split("/")[
                -1
            ],  # Use the file name as the display name
            "blob": file_content,
        }

        # Upload the document to the dataset
        dataset.upload_documents([document])
        print(f"File '{file_path}' uploaded successfully to dataset '{dataset_name}'.")

    except Exception as e:
        print(f"An error occurred while uploading the file: {e}")


def main():
    client = RAGFlowClient(api_key=_rf_api_key, base_url="http://localhost")
    xdataset = client.create_logseq_dataset(dataset_name=f"{_dataset}")
    _fileList = get_files_with_extensions(_importDir, _fileExtensions)

    for _file in _fileList:
        upload_file_to_ragflow(
            file_path=_file,
            dataset_name=_dataset,
            api_key=_rf_api_key,
        )


if __name__ == "__main__":
    main()
