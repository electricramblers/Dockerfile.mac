import os
import hashlib
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FileState:
    """
    Manages the state of files to track uploads and detect duplicates.
    """
    STATE_FILE = "file_state.json"

    def __init__(self):
        """
        Initializes the FileState, loading existing state from file if available.
        """
        self.file_states = self._load_state()

    def _load_state(self):
        """
        Loads the file state from the JSON file.
        """
        try:
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading file state: {e}. Starting with an empty state.")
            return {}

    def _save_state(self):
        """
        Saves the current file state to the JSON file.
        """
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self.file_states, f, indent=4)
        except IOError as e:
            logging.error(f"Error saving file state: {e}")

    def get_file_sha1(self, file_path):
        """
        Calculates the SHA1 checksum of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The SHA1 checksum of the file, or None if an error occurred.
        """
        try:
            hasher = hashlib.sha1()
            with open(file_path, 'rb') as afile:
                buf = afile.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except IOError as e:
            logging.error(f"Error reading file {file_path}: {e}")
            return None

    def add_file(self, file_path, document_id, cosine_similarity=None):
        """
        Adds a file to the state, recording its SHA1 checksum, document ID,
        and cosine similarity (if provided).

        Args:
            file_path (str): The full path to the file.
            document_id (str): The ID of the document in Ragflow.
            cosine_similarity (float, optional): The cosine similarity value. Defaults to None.
        """
        sha1_sum = self.get_file_sha1(file_path)
        if not sha1_sum:
            logging.error(f"Could not calculate SHA1 for {file_path}. File not added to state.")
            return

        self.file_states[file_path] = {
            'basename': os.path.basename(file_path),
            'sha1': sha1_sum,
            'document_id': document_id,
            'cosine_similarity': cosine_similarity
        }
        self._save_state()
        logging.info(f"Added file {file_path} to state with SHA1 {sha1_sum} and document ID {document_id}.")

    def should_upload(self, file_path):
        """
        Determines whether a file should be uploaded based on its SHA1 checksum.

        Args:
            file_path (str): The full path to the file.

        Returns:
            bool: True if the file should be uploaded (not a duplicate or has changed), False otherwise.
        """
        sha1_sum = self.get_file_sha1(file_path)
        if not sha1_sum:
            logging.error(f"Could not calculate SHA1 for {file_path}. Assuming upload is needed.")
            return True  # If we can't calculate SHA1, assume it needs to be uploaded

        if file_path in self.file_states:
            if self.file_states[file_path]['sha1'] == sha1_sum:
                logging.info(f"File {file_path} already exists and has not changed. Skipping upload.")
                return False
            else:
                logging.info(f"File {file_path} has changed since last upload.  Re-uploading.")
                return True
        else:
            logging.info(f"File {file_path} is new.  Needs upload.")
            return True

    def update_document_id(self, file_path, new_document_id):
        """
        Updates the document ID for a file in the state.

        Args:
            file_path (str): The full path to the file.
            new_document_id (str): The new document ID to associate with the file.
        """
        if file_path in self.file_states:
            self.file_states[file_path]['document_id'] = new_document_id
            self._save_state()
            logging.info(f"Updated document ID for {file_path} to {new_document_id}.")
        else:
            logging.warning(f"File {file_path} not found in state.  Cannot update document ID.")

    def get_document_id(self, file_path):
        """
        Retrieves the document ID for a file.

        Args:
            file_path (str): The full path to the file.

        Returns:
            str: The document ID, or None if the file is not in the state.
        """
        if file_path in self.file_states:
            return self.file_states[file_path]['document_id']
        else:
            return None

