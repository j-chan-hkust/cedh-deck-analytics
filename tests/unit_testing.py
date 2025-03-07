import unittest
import os
import sys
import glob
import tempfile
import shutil

# Add the parent directory to the path so we can import the preprocessing module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DecklistTests(unittest.TestCase):
    """Test suite for processed decklists."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures.
        This runs once before all tests in the class.
        """
        # Use paths relative to the project root
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        cls.processed_dir = os.path.join(cls.project_root, "processed_decklists")

    def setUp(self):
        """Set up test fixtures.
        This runs before each test method.
        """
        self.deck_files = glob.glob(os.path.join(self.processed_dir, "*.txt"))

    def test_directory_exists(self):
        """Test that the processed decklists directory exists."""
        self.assertTrue(os.path.exists(self.processed_dir),
                        f"Directory {self.processed_dir} does not exist")

    def test_files_exist(self):
        """Test that there are deck files in the directory."""
        self.assertTrue(len(self.deck_files) > 0,
                        f"No deck files found in {self.processed_dir}")

    def test_deck_size(self):
        """Test that each deck contains exactly 100 cards."""
        # Skip the test if no files are found
        if not self.deck_files:
            self.skipTest(f"No deck files found in {self.processed_dir}")

        # Track files with incorrect card counts for detailed reporting
        incorrect_files = []

        for file_path in self.deck_files:
            file_name = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                card_count = len(lines)

                if card_count != 100:
                    incorrect_files.append((file_name, card_count))

        # If any files have incorrect counts, fail the test with details
        if incorrect_files:
            error_message = "The following files don't have exactly 100 cards:\n"
            for file_name, count in incorrect_files:
                error_message += f"  - {file_name}: {count} cards\n"
            self.fail(error_message)

    def test_file_format(self):
        """Test that each line in each file follows the expected format."""
        # Skip the test if no files are found
        if not self.deck_files:
            self.skipTest(f"No deck files found in {self.processed_dir}")

        format_errors = []

        for file_path in self.deck_files:
            file_name = os.path.basename(file_path)
            line_errors = []

            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Check that the line ends with a number (card_name1, card_name2, etc.)
                    if not line[-1].isdigit():
                        line_errors.append((i, line, "Line does not end with a number"))

            if line_errors:
                format_errors.append((file_name, line_errors))

        # If any format errors were found, fail the test with details
        if format_errors:
            error_message = "The following files contain format errors:\n"
            for file_name, errors in format_errors:
                error_message += f"  File: {file_name}\n"
                for line_num, content, error in errors[:5]:  # Show first 5 errors
                    error_message += f"    Line {line_num}: '{content}' - {error}\n"
                if len(errors) > 5:
                    error_message += f"    ... and {len(errors) - 5} more errors\n"
            self.fail(error_message)

class PreprocessingIntegrationTest(unittest.TestCase):
    """Integration test for the preprocessing function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories for testing
        self.test_input_dir = tempfile.mkdtemp()
        self.test_output_dir = tempfile.mkdtemp()

        # Create a sample deck file
        self.sample_deck = os.path.join(self.test_input_dir, "sample_deck.txt")
        with open(self.sample_deck, 'w', encoding='utf-8') as f:
            # Write 100 cards (1 copy each)
            for i in range(1, 101):
                f.write(f"1 Test Card {i} (TST) 123\n")
            # Add a sideboard section that should be ignored
            f.write("SIDEBOARD:\n")
            f.write("1 Sideboard Card (SB) 456\n")

    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directories
        shutil.rmtree(self.test_input_dir)
        shutil.rmtree(self.test_output_dir)

if __name__ == "__main__":
    unittest.main()
