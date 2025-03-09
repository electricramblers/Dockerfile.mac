from ansible_vault import Vault
from dotenv import load_dotenv
from termcolor import cprint
from ragflow_sdk import RAGFlow
import os
import io

from src.RetrieveRfApi import retrieve_ragflow_api_key


class RAGFlowClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.rag_object = RAGFlow(api_key=self.api_key, base_url=self.base_url)

    def create_logseq_dataset(
        self,
        dataset_name,
        avatar="",
        description="This is a Logseq dataset",
        embedding_model="BAAI/bge-large-zh-v1.5",
        permission="me",
        chunk_method="naive",
    ):
        try:
            # Create the dataset
            dataset = self.rag_object.create_dataset(
                name=dataset_name,
                avatar=avatar,
                description=description,
                embedding_model=embedding_model,
                permission=permission,
                chunk_method=chunk_method,
            )
            print(f"Dataset '{dataset_name}' created successfully!")
            return dataset
        except Exception as e:
            print(f"An error occurred while creating the dataset: {e}")
            return None


def main():
    _ragflowApiKey = retrieve_ragflow_api_key()
    client = RAGFlowClient(api_key=_ragflowApiKey, base_url="http://localhost")
    dataset = client.create_logseq_dataset(dataset_name="logseq_dataset")


if __name__ == "__main__":
    main()
