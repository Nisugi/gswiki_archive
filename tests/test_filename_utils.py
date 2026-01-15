"""Tests for filename utilities."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.filename_utils import title_to_filename, filename_to_title


class TestTitleToFilename:
    """Tests for title_to_filename function."""

    def test_simple_title(self):
        """Simple titles should just get .html appended."""
        assert title_to_filename("Main Page") == "Main Page.html"
        assert title_to_filename("Sword") == "Sword.html"

    def test_colon_replacement(self):
        """Colons should be replaced with _COLON_."""
        assert title_to_filename("Category:Weapons") == "Category_COLON_Weapons.html"
        assert title_to_filename("Template:Infobox") == "Template_COLON_Infobox.html"

    def test_slash_replacement(self):
        """Slashes should be replaced with _SLASH_."""
        assert title_to_filename("User:John/Sandbox") == "User_COLON_John_SLASH_Sandbox.html"

    def test_question_mark_replacement(self):
        """Question marks should be replaced with _QUESTION_."""
        assert title_to_filename("What is this?") == "What is this_QUESTION_.html"

    def test_multiple_special_chars(self):
        """Multiple special characters should all be replaced."""
        result = title_to_filename("Category:Items/Weapons?")
        assert result == "Category_COLON_Items_SLASH_Weapons_QUESTION_.html"

    def test_star_replacement(self):
        """Stars should be replaced with _STAR_."""
        assert title_to_filename("5* Items") == "5_STAR_ Items.html"

    def test_quote_replacement(self):
        """Double quotes should be replaced with _QUOTE_."""
        assert title_to_filename('The "Best" Sword') == "The _QUOTE_Best_QUOTE_ Sword.html"

    def test_angle_brackets(self):
        """Angle brackets should be replaced."""
        assert title_to_filename("Item <rare>") == "Item _LT_rare_GT_.html"

    def test_pipe_replacement(self):
        """Pipes should be replaced with _PIPE_."""
        assert title_to_filename("Choice|Option") == "Choice_PIPE_Option.html"

    def test_backslash_replacement(self):
        """Backslashes should be replaced with _BACKSLASH_."""
        assert title_to_filename("Path\\File") == "Path_BACKSLASH_File.html"


class TestFilenameToTitle:
    """Tests for filename_to_title function."""

    def test_simple_filename(self):
        """Simple filenames should just have .html removed."""
        assert filename_to_title("Main Page.html") == "Main Page"
        assert filename_to_title("Sword.html") == "Sword"

    def test_colon_restoration(self):
        """_COLON_ should be restored to colons."""
        assert filename_to_title("Category_COLON_Weapons.html") == "Category:Weapons"

    def test_slash_restoration(self):
        """_SLASH_ should be restored to slashes."""
        assert filename_to_title("User_COLON_John_SLASH_Sandbox.html") == "User:John/Sandbox"

    def test_all_replacements_restored(self):
        """All special character replacements should be restored."""
        filename = "Category_COLON_Items_SLASH_Weapons_QUESTION_.html"
        assert filename_to_title(filename) == "Category:Items/Weapons?"


class TestRoundtrip:
    """Tests for roundtrip conversion (title -> filename -> title)."""

    def test_roundtrip_simple(self):
        """Simple titles should survive roundtrip."""
        original = "Main Page"
        assert filename_to_title(title_to_filename(original)) == original

    def test_roundtrip_with_namespace(self):
        """Namespace titles should survive roundtrip."""
        original = "Category:Weapons"
        assert filename_to_title(title_to_filename(original)) == original

    def test_roundtrip_complex(self):
        """Complex titles with multiple special chars should survive roundtrip."""
        original = "User:Admin/Test?Page"
        assert filename_to_title(title_to_filename(original)) == original

    def test_roundtrip_all_special_chars(self):
        """Title with all special characters should survive roundtrip."""
        original = 'A/B\\C:D*E?F"G<H>I|J'
        assert filename_to_title(title_to_filename(original)) == original
