#!/usr/bin/env python
import os
import fnmatch
from ansible.parsing.vault import get_file_vault_secret
from termcolor import cprint, colored
from src.RetrieveRfApi import retrieve_ragflow_api_key
from ragflow_sdk import RAGFlow
from time import sleep

_dataset = "logseq_dataset"
_rf_api_key = retrieve_ragflow_api_key()
_importDir = os.path.expandvars("${HOME}/LLM_RAG/Logseq")
_base_url = "http://localhost"
_fileExtensions = [
    ".md",
    ".txt",
]


def get_files_with_extensions(directory, file_extensions):
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                absolute_path = os.path.abspath(os.path.join(root, file))
                matching_files.append(absolute_path)
    return matching_files


def chunk_list(data, chunk_size):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def main():
    if not _rf_api_key:
        cprint(f"API Key Missing", "red")
        return  # Exit if API key is missing

    client = RAGFlow(api_key=_rf_api_key, base_url="http://localhost")
    _fileList = get_files_with_extensions(_importDir, _fileExtensions)

    try:
        client.delete_datasets(ids=[f"{_dataset}"])
        cprint(f"Deleted dataset '{_dataset}'", "yellow")
    except Exception as e:
        cprint(f"Exception during dataset deletion: {e}", "red")

    try:
        dataset = client.create_dataset(name=f"{_dataset}")
        cprint(f"Created dataset: '{_dataset}'", "green")
    except Exception as e:
        cprint(f"Dataset might already exist, or another error occurred: {e}", "yellow")
        datasets = client.list_datasets(name=_dataset)
        if datasets:
            dataset = datasets[0]
            cprint(f"Using existing dataset '{_dataset}'", "green")
        else:
            cprint(colored("Failed to retrieve or create dataset.", "red"))
            return

    # UPLOAD
    upLoad = False

    if upLoad:
        for file in _fileList:

        with open(file, "rb") as f:
            file_content = f.read()

        filename = os.path.basename(file)

        document_list = [{"display_name": filename, "blob": file_content}]

        dataset.upload_documents(document_list)

        sleep(1)
        cprint(f"Uploaded {filename}", "green")



    # doclist = dataset.list_documents(orderby="create_time")

    # for doc in doclist:
    #    if doc.run == "UNSTART":
    #        cprint(
    #            f"Document DI: {doc.id}\nName: {doc.name}\nStatus: {doc.run}", "yellow"
    #        )
    #        print("\n")


if __name__ == "__main__":
    main()
