from ansible_vault import Vault
from dotenv import load_dotenv
from termcolor import cprint
from ragflow_sdk import RAGFlow
import os
import io


def retrieve_ragflow_api_key():
    """
    Load and decrypt an encrypted .env file using Ansible Vault.
    The vault passphrase is read from a file specified by the ANSIBLE_VAULT_PASSWORD_FILE environment variable.
    After decryption, the environment variables are loaded and the RAGFLOW_API_KEY is printed.
    """
    try:
        vault_passphrase_file = os.getenv("ANSIBLE_VAULT_PASSWORD_FILE")

        if not vault_passphrase_file:
            raise ValueError(
                "ANSIBLE_VAULT_PASSWORD_FILE environment variable is not set"
            )

        with open(vault_passphrase_file, "r") as file:
            vault_password = file.read().strip()

        # Define the path to the encrypted .env file
        encrypted_env_file = ".env"

        # Initialize the Vault object with the passphrase
        vault = Vault(vault_password)

        # Read the encrypted data from the .env file
        with open(encrypted_env_file, "r") as file:
            encrypted_data = file.read()

        # Decrypt the data using Ansible Vault
        decrypted_data = vault.load(encrypted_data)
        decrypted_file = io.StringIO(decrypted_data)
        load_dotenv(stream=decrypted_file)

        RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY")

        # Print the RAGFLOW_API_KEY in green color
        if RAGFLOW_API_KEY:
            return RAGFLOW_API_KEY

    except FileNotFoundError as e:
        cprint(f"File not found: {e}", "red")
    except ValueError as e:
        cprint(f"Value error: {e}", "red")
    except Exception as e:
        cprint(f"An unexpected error occurred: {e}", "red")
