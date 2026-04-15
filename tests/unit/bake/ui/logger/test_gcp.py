import logging

import loguru
import pytest

from bake import GCPJsonSink, GCPLogKey, LogKey, capsys_to_logs, setup_logging
from tests.unit.bake.ui.logger.utils import has_required_keys


class TestGCPJsonSink:
    """Test GCPJsonSink class."""

    def test_gcp_json_sink_inherits_from_json_sink(self) -> None:
        """Test that GCPJsonSink inherits from JsonSink."""
        from bake.ui.logger.utils import JsonSink

        assert issubclass(GCPJsonSink, JsonSink)

    def test_gcp_log_key_enum_values(self) -> None:
        """Test that GCPLogKey enum has correct values."""
        assert GCPLogKey.TIME.value == "time"
        assert GCPLogKey.SEVERITY.value == "severity"

    def test_gcp_log_key_required_keys_includes_log_keys(self) -> None:
        """Test that GCPLogKey.required_keys() includes all LogKey fields plus GCP fields."""
        gcp_required = GCPLogKey.required_keys()
        log_required = LogKey.required_keys()

        # GCP should include all LogKey keys
        assert log_required.issubset(gcp_required)

        # GCP should also include its own keys
        assert GCPLogKey.TIME.value in gcp_required
        assert GCPLogKey.SEVERITY.value in gcp_required

        # GCP should have more keys than LogKey
        assert len(gcp_required) > len(log_required)


class TestGCPJsonOutput:
    """Test GCP JSON log output format."""

    def test_gcp_fields_present_in_json_output(self, capsys: pytest.CaptureFixture) -> None:
        """Test that GCP-specific fields (time, severity) are present in JSON output."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.info("test_message")

        parsed_logs = capsys_to_logs(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # Validate all GCP required keys (including time and severity)
        assert has_required_keys(log, log_key_cls=GCPLogKey)
        # Verify severity value is uppercased
        assert log[GCPLogKey.SEVERITY.value] == "INFO"

    def test_gcp_time_field_matches_timestamp(self, capsys: pytest.CaptureFixture) -> None:
        """Test that GCP 'time' field matches the original 'timestamp' field."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.info("test_message")

        parsed_logs = capsys_to_logs(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # time should be an alias for timestamp
        assert log[GCPLogKey.TIME.value] == log[LogKey.TIMESTAMP.value]

    def test_gcp_severity_field_matches_level_uppercased(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that GCP 'severity' field matches the original 'level' field (uppercased)."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.warning("test_message")

        parsed_logs = capsys_to_logs(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # severity should be level.upper()
        assert log[GCPLogKey.SEVERITY.value] == log[LogKey.LEVEL.value].upper()
        assert log[LogKey.LEVEL.value] == "WARNING"
        assert log[GCPLogKey.SEVERITY.value] == "WARNING"

    def test_backward_compatibility_original_fields_present(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that original fields (timestamp, level) are still present."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.info("test_message")

        parsed_logs = capsys_to_logs(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # GCP format includes all standard fields plus GCP aliases
        assert has_required_keys(log, log_key_cls=GCPLogKey)


class TestSetupLoggingIntegration:
    """Test setup_logging integration with GCPJsonSink."""

    def test_setup_logging_with_gcp_json_sink(self, capsys: pytest.CaptureFixture) -> None:
        """Test that setup_logging works with GCPJsonSink."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.info("test_message")

        parsed_logs = capsys_to_logs(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # Validate with GCPLogKey (includes all standard + GCP fields)
        assert has_required_keys(log, log_key_cls=GCPLogKey)

    def test_setup_logging_default_unchanged(self, capsys: pytest.CaptureFixture) -> None:
        """Test that setup_logging default behavior is unchanged (no json_sink_class)."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
        )

        loguru.logger.info("test_message")

        parsed_logs = capsys_to_logs(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # Should have standard fields (no GCP fields in default mode)
        assert has_required_keys(log)

    def test_setup_logging_pretty_mode_ignores_json_sink_class(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that pretty mode ignores json_sink_class parameter."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=True,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.info("test_message")

        # Pretty output is not JSON, so we use capsys_to_logs_pretty
        from bake import capsys_to_logs_pretty

        parsed_logs = capsys_to_logs_pretty(capsys)

        assert len(parsed_logs) == 1
        log = parsed_logs[0]

        # Should have standard fields (pretty mode doesn't use json_sink_class)
        assert has_required_keys(log)


class TestGCPLogLevels:
    """Test GCP severity field for different log levels."""

    def test_gcp_severity_for_debug(self, capsys: pytest.CaptureFixture) -> None:
        """Test that severity field is DEBUG for debug level."""
        setup_logging(
            level_per_module={"": logging.DEBUG},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.debug("test")

        parsed_logs = capsys_to_logs(capsys)
        assert len(parsed_logs) == 1
        assert parsed_logs[0][GCPLogKey.SEVERITY.value] == "DEBUG"

    def test_gcp_severity_for_info(self, capsys: pytest.CaptureFixture) -> None:
        """Test that severity field is INFO for info level."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.info("test")

        parsed_logs = capsys_to_logs(capsys)
        assert len(parsed_logs) == 1
        assert parsed_logs[0][GCPLogKey.SEVERITY.value] == "INFO"

    def test_gcp_severity_for_warning(self, capsys: pytest.CaptureFixture) -> None:
        """Test that severity field is WARNING for warning level."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.warning("test")

        parsed_logs = capsys_to_logs(capsys)
        assert len(parsed_logs) == 1
        assert parsed_logs[0][GCPLogKey.SEVERITY.value] == "WARNING"

    def test_gcp_severity_for_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test that severity field is ERROR for error level."""
        setup_logging(
            level_per_module={"": logging.INFO},
            thread_local_context=None,
            is_pretty_log=False,
            json_sink_class=GCPJsonSink,
        )

        loguru.logger.error("test")

        parsed_logs = capsys_to_logs(capsys)
        assert len(parsed_logs) == 1
        assert parsed_logs[0][GCPLogKey.SEVERITY.value] == "ERROR"
