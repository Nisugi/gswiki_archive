"""Tests for logging configuration."""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.logging_config import setup_logging, get_log_dir


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_logger(self, temp_log_dir):
        """setup_logging should create a logger instance."""
        logger = setup_logging(
            name="test",
            log_dir=str(temp_log_dir),
        )
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_creates_log_file(self, temp_log_dir):
        """setup_logging should create a log file."""
        logger = setup_logging(
            name="test",
            log_dir=str(temp_log_dir),
        )
        logger.info("Test message")

        log_file = temp_log_dir / "test.log"
        assert log_file.exists()

    def test_includes_wiki_id_in_filename(self, temp_log_dir):
        """setup_logging should include wiki_id in filename when provided."""
        logger = setup_logging(
            name="import",
            wiki_id="gswiki",
            log_dir=str(temp_log_dir),
        )
        logger.info("Test message")

        log_file = temp_log_dir / "gswiki-import.log"
        assert log_file.exists()

    def test_logs_message_to_file(self, temp_log_dir):
        """setup_logging should log messages to file."""
        logger = setup_logging(
            name="test",
            log_dir=str(temp_log_dir),
            console=False,  # Disable console to avoid test output noise
        )
        logger.info("Test log message")

        log_file = temp_log_dir / "test.log"
        content = log_file.read_text()
        assert "Test log message" in content

    def test_respects_log_level(self, temp_log_dir):
        """setup_logging should respect the configured log level."""
        logger = setup_logging(
            name="test",
            log_dir=str(temp_log_dir),
            level=logging.WARNING,
            console=False,
        )
        logger.debug("Debug message")
        logger.warning("Warning message")

        log_file = temp_log_dir / "test.log"
        content = log_file.read_text()
        assert "Debug message" not in content
        assert "Warning message" in content

    def test_creates_log_directory(self, tmp_path):
        """setup_logging should create log directory if it doesn't exist."""
        log_dir = tmp_path / "new_logs"
        assert not log_dir.exists()

        logger = setup_logging(
            name="test",
            log_dir=str(log_dir),
        )
        logger.info("Test")

        assert log_dir.exists()


class TestGetLogDir:
    """Tests for get_log_dir function."""

    def test_returns_default(self, monkeypatch):
        """get_log_dir should return default when LOG_DIR not set."""
        monkeypatch.delenv("LOG_DIR", raising=False)
        result = get_log_dir()
        assert result == Path("./logs")

    def test_returns_custom_default(self, monkeypatch):
        """get_log_dir should accept custom default."""
        monkeypatch.delenv("LOG_DIR", raising=False)
        result = get_log_dir("/var/log/custom")
        assert result == Path("/var/log/custom")

    def test_returns_env_var(self, monkeypatch):
        """get_log_dir should return LOG_DIR env var when set."""
        monkeypatch.setenv("LOG_DIR", "/custom/logs")
        result = get_log_dir()
        assert result == Path("/custom/logs")
