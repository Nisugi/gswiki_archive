"""Tests for WikiAPI client."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.wiki_api import WikiAPI


class TestWikiAPIInit:
    """Tests for WikiAPI initialization."""

    def test_default_initialization(self):
        """WikiAPI should initialize with sensible defaults."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )
        assert api.api_url == "https://wiki.example.com/api.php"
        assert api.wiki_name == "TestWiki"
        assert api.delay == 2.0
        assert api.timeout == 30.0
        assert api.max_retries == 3

    def test_custom_parameters(self):
        """WikiAPI should accept custom parameters."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
            delay=5.0,
            timeout=60.0,
            max_retries=5,
            user_agent="CustomBot/1.0",
        )
        assert api.delay == 5.0
        assert api.timeout == 60.0
        assert api.max_retries == 5

    def test_session_created(self):
        """WikiAPI should create a requests session."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )
        assert api.session is not None
        assert "User-Agent" in api.session.headers


class TestWikiAPIRequest:
    """Tests for WikiAPI.request method."""

    @patch('lib.wiki_api.time.sleep')
    def test_request_adds_format_json(self, mock_sleep):
        """Request should add format=json to params."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        mock_response = Mock()
        mock_response.json.return_value = {"query": {}}
        mock_response.raise_for_status = Mock()
        api.session.get = Mock(return_value=mock_response)

        api.request({"action": "query"})

        call_args = api.session.get.call_args
        assert call_args[1]["params"]["format"] == "json"

    @patch('lib.wiki_api.time.sleep')
    def test_request_returns_json(self, mock_sleep):
        """Request should return parsed JSON."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        expected_data = {"query": {"pages": {}}}
        mock_response = Mock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = Mock()
        api.session.get = Mock(return_value=mock_response)

        result = api.request({"action": "query"})
        assert result == expected_data

    @patch('lib.wiki_api.time.sleep')
    def test_request_respects_delay(self, mock_sleep):
        """Request should sleep for the configured delay."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
            delay=3.0,
        )

        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        api.session.get = Mock(return_value=mock_response)

        api.request({"action": "query"})
        mock_sleep.assert_called_with(3.0)


class TestWikiAPIGetNamespaces:
    """Tests for WikiAPI.get_namespaces method."""

    @patch('lib.wiki_api.time.sleep')
    def test_parses_namespaces(self, mock_sleep):
        """get_namespaces should parse namespace IDs from API response."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "query": {
                "namespaces": {
                    "-1": {"id": -1, "name": "Special"},
                    "0": {"id": 0, "name": ""},
                    "1": {"id": 1, "name": "Talk"},
                    "10": {"id": 10, "name": "Template"},
                }
            }
        }
        mock_response.raise_for_status = Mock()
        api.session.get = Mock(return_value=mock_response)

        namespaces = api.get_namespaces()

        # Should exclude negative namespaces
        assert -1 not in namespaces
        assert 0 in namespaces
        assert 1 in namespaces
        assert 10 in namespaces

    @patch('lib.wiki_api.time.sleep')
    def test_returns_sorted_list(self, mock_sleep):
        """get_namespaces should return a sorted list."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "query": {
                "namespaces": {
                    "10": {"id": 10},
                    "0": {"id": 0},
                    "14": {"id": 14},
                    "1": {"id": 1},
                }
            }
        }
        mock_response.raise_for_status = Mock()
        api.session.get = Mock(return_value=mock_response)

        namespaces = api.get_namespaces()
        assert namespaces == sorted(namespaces)

    @patch('lib.wiki_api.time.sleep')
    def test_returns_default_on_failure(self, mock_sleep):
        """get_namespaces should return [0] on API failure."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        api.session.get = Mock(side_effect=requests.RequestException("Network error"))

        namespaces = api.get_namespaces()
        assert namespaces == [0]


class TestWikiAPIGetAllPages:
    """Tests for WikiAPI.get_all_pages method."""

    @patch('lib.wiki_api.time.sleep')
    def test_returns_page_list(self, mock_sleep):
        """get_all_pages should return a list of page dicts."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        # Mock namespace response
        ns_response = Mock()
        ns_response.json.return_value = {
            "query": {"namespaces": {"0": {"id": 0}}}
        }
        ns_response.raise_for_status = Mock()

        # Mock page list response
        pages_response = Mock()
        pages_response.json.return_value = {
            "query": {
                "allpages": [
                    {"pageid": 1, "title": "Main Page"},
                    {"pageid": 2, "title": "Test Page"},
                ]
            }
        }
        pages_response.raise_for_status = Mock()

        api.session.get = Mock(side_effect=[ns_response, pages_response])

        pages = api.get_all_pages()

        assert len(pages) == 2
        assert pages[0]["title"] == "Main Page"
        assert pages[1]["title"] == "Test Page"

    @patch('lib.wiki_api.time.sleep')
    def test_handles_pagination(self, mock_sleep):
        """get_all_pages should handle API pagination."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        # Mock namespace response
        ns_response = Mock()
        ns_response.json.return_value = {
            "query": {"namespaces": {"0": {"id": 0}}}
        }
        ns_response.raise_for_status = Mock()

        # First page of results
        page1_response = Mock()
        page1_response.json.return_value = {
            "query": {
                "allpages": [{"pageid": 1, "title": "Page 1"}]
            },
            "continue": {"apcontinue": "Page 2"}
        }
        page1_response.raise_for_status = Mock()

        # Second page of results
        page2_response = Mock()
        page2_response.json.return_value = {
            "query": {
                "allpages": [{"pageid": 2, "title": "Page 2"}]
            }
        }
        page2_response.raise_for_status = Mock()

        api.session.get = Mock(side_effect=[ns_response, page1_response, page2_response])

        pages = api.get_all_pages()

        assert len(pages) == 2
        assert pages[0]["title"] == "Page 1"
        assert pages[1]["title"] == "Page 2"


class TestWikiAPIGetPageTitles:
    """Tests for WikiAPI.get_page_titles method."""

    @patch('lib.wiki_api.time.sleep')
    def test_returns_title_strings(self, mock_sleep):
        """get_page_titles should return a list of title strings."""
        api = WikiAPI(
            api_url="https://wiki.example.com/api.php",
            wiki_name="TestWiki",
        )

        # Mock namespace response
        ns_response = Mock()
        ns_response.json.return_value = {
            "query": {"namespaces": {"0": {"id": 0}}}
        }
        ns_response.raise_for_status = Mock()

        # Mock page list response
        pages_response = Mock()
        pages_response.json.return_value = {
            "query": {
                "allpages": [
                    {"pageid": 1, "title": "Main Page"},
                    {"pageid": 2, "title": "Test Page"},
                ]
            }
        }
        pages_response.raise_for_status = Mock()

        api.session.get = Mock(side_effect=[ns_response, pages_response])

        titles = api.get_page_titles()

        assert titles == ["Main Page", "Test Page"]
