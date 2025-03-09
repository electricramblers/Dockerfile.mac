#!/usr/bin/env python
import os
import fnmatch
from ansible.parsing.vault import get_file_vault_secret
from termcolor import cprint, colored
from src.RetrieveRfApi import retrieve_ragflow_api_key
from ragflow_sdk import RAGFlow

_dataset = "logseq_dataset"
_rf_api_key = retrieve_ragflow_api_key()
_importDir = os.path.expandvars("${HOME}/LLM_RAG/Logseq")
_base_url = "http://localhost"

_fileExtensions = [
    ".md",
    ".docx",
    ".pptx",
    ".pdf",
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


def main():
    if not _rf_api_key:
        cprint(f"API Key Missing", "red")

    client = RAGFlow(api_key=_rf_api_key, base_url="http://localhost")

    _fileList = get_files_with_extensions(_importDir, _fileExtensions)

    try:
        client.delete_datasets(ids=[f"{_dataset}"])
    except Exception as e:
        cprint(f"Exception is: {e}", "red")

    try:
        dataset = client.create_dataset(name=f"{_dataset}")
    except:
        cprint(f"Dataset Exists: {_dataset}\n", "green")

    datasets = client.list_datasets(name=_dataset)
    if datasets:
        dataset = datasets[0]
    else:
        raise ValueError(colored("Dataset is borked.", "red"))

    for _file in _fileList:
        with open(_file, "rb") as f:
            file_content = f.read()

        # Prepare the document for upload
        document = {
            "display_name": _file.split("/")[
                -1
            ],  # Use the file name as the display name
            "blob": file_content,
        }

        # Upload the document to the dataset
        try:
            dataset.upload_documents([document])
            print(f"File '{_file}' uploaded successfully to dataset '{_dataset}'.")
        except:
            pass

    documents = dataset.list_documents()
    ids = []
    for document in documents:
        ids.append(document.id)
    dataset.async_parse_documents(ids)

    cprint("Async bulk parsing initiated.", "green")


if __name__ == "__main__":
    main()
