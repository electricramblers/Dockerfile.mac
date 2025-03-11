import unittest
import os
import json
import hashlib
from unittest.mock import patch, mock_open
from termcolor import cprint, colored
from src.FileManagement import FileState
import logging

# Configure logging to capture messages during tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestFileState(unittest.TestCase):

    def setUp(self):
        """
        Set up for the tests.  This includes creating a temporary state file
        and initializing the FileState object.
        """
        self.test_file = "test_file.txt"
        self.test_file_content = "This is a test file."
        with open(self.test_file, "w") as f:
            f.write(self.test_file_content)

        self.state_file = "test_file_state.json"
        self.file_state = FileState()
        self.file_state.STATE_FILE = self.state_file  # Override the default state file
        self.file_state.file_states = {}  # Ensure it starts empty
        self.file_state._save_state()  # Save the empty state to the test file

        self.document_id = "test_document_id"
        self.sha1_hash = hashlib.sha1(self.test_file_content.encode()).hexdigest()

    def tearDown(self):
        """
        Tear down after the tests.  This includes removing the temporary state file
        and the test file.
        """
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_file_hashing(self):
        """
        Test case to verify the SHA1 hash generation for a file.
        """
        cprint("\nRunning test_file_hashing...", "cyan")
        sha1_hash = self.file_state.get_file_sha1(self.test_file)
        self.assertEqual(sha1_hash, self.sha1_hash, colored("SHA1 hash verification failed!", "red"))
        cprint(colored("SHA1 hash verification successful!", "green"), "green")

    def test_add_file(self):
        """
        Test case to verify adding a file to the state.
        """
        cprint("\nRunning test_add_file...", "cyan")
        self.file_state.add_file(self.test_file, self.document_id)
        self.assertIn(self.test_file, self.file_state.file_states, colored("File not added to state!", "red"))
        self.assertEqual(self.file_state.file_states[self.test_file]['document_id'], self.document_id, colored("Document ID mismatch!", "red"))
        cprint(colored("File added to state successfully!", "green"), "green")

    def test_should_upload_new_file(self):
        """
        Test case to verify that a new file should be uploaded.
        """
        cprint("\nRunning test_should_upload_new_file...", "cyan")
        should_upload = self.file_state.should_upload(self.test_file)
        self.assertTrue(should_upload, colored("New file should be uploaded!", "red"))
        cprint(colored("New file upload check passed!", "green"), "green")

    def test_should_not_upload_existing_file(self):
        """
        Test case to verify that an existing file with the same SHA1 should not be uploaded.
        """
        cprint("\nRunning test_should_not_upload_existing_file...", "cyan")
        self.file_state.add_file(self.test_file, self.document_id)
        should_upload = self.file_state.should_upload(self.test_file)
        self.assertFalse(should_upload, colored("Existing file should not be uploaded!", "red"))
        cprint(colored("Existing file upload check passed!", "green"), "green")

    def test_should_upload_modified_file(self):
        """
        Test case to verify that a modified file should be uploaded.
        """
        cprint("\nRunning test_should_upload_modified_file...", "cyan")
        self.file_state.add_file(self.test_file, self.document_id)
        with open(self.test_file, "w") as f:
            f.write("This is a modified test file.")
        should_upload = self.file_state.should_upload(self.test_file)
        self.assertTrue(should_upload, colored("Modified file should be uploaded!", "red"))
        cprint(colored("Modified file upload check passed!", "green"), "green")

    def test_update_document_id(self):
        """
        Test case to verify updating the document ID of a file.
        """
        cprint("\nRunning test_update_document_id...", "cyan")
        self.file_state.add_file(self.test_file, self.document_id)
        new_document_id = "new_test_document_id"
        self.file_state.update_document_id(self.test_file, new_document_id)
        self.assertEqual(self.file_state.file_states[self.test_file]['document_id'], new_document_id, colored("Document ID update failed!", "red"))
        cprint(colored("Document ID updated successfully!", "green"), "green")

    def test_load_state_from_file(self):
        """
        Test case to verify loading the file state from a JSON file.
        """
        cprint("\nRunning test_load_state_from_file...", "cyan")
        # Create a state file with some data
        initial_state = {self.test_file: {'basename': 'test_file.txt', 'sha1': self.sha1_hash, 'document_id': self.document_id, 'cosine_similarity': None}}
        with open(self.state_file, 'w') as f:
            json.dump(initial_state, f)

        # Load the state from the file
        loaded_file_state = FileState()
        loaded_file_state.STATE_FILE = self.state_file
        loaded_file_state.file_states = loaded_file_state._load_state()

        # Assert that the state was loaded correctly
        self.assertEqual(loaded_file_state.file_states, initial_state, colored("File state loading failed!", "red"))
        cprint(colored("File state loaded successfully!", "green"), "green")

    def test_save_state_to_file(self):
        """
        Test case to verify saving the file state to a JSON file.
        """
        cprint("\nRunning test_save_state_to_file...", "cyan")
        # Add a file to the state
        self.file_state.add_file(self.test_file, self.document_id)

        # Save the state to the file
        self.file_state._save_state()

        # Load the state from the file
        with open(self.state_file, 'r') as f:
            loaded_state = json.load(f)

        # Assert that the state was saved correctly
        self.assertEqual(self.file_state.file_states, loaded_state, colored("File state saving failed!", "red"))
        cprint(colored("File state saved successfully!", "green"), "green")

if __name__ == '__main__':
    unittest.main()
