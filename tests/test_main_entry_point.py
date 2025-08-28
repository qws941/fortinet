#!/usr/bin/env python3
"""
Test suite for main.py - Application Entry Point
Comprehensive testing for command-line parsing, environment detection, and application startup
"""

import argparse
import os
import sys
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import (
    analyze_packet_path,
    determine_target_environment,
    get_env_port,
    is_docker_environment,
    load_environment_config,
    main,
    parse_args,
    save_output,
    validate_environment_consistency,
    visualize_path,
)


class TestEnvironmentDetection:
    """Test environment detection and configuration"""

    def test_determine_target_environment_development(self):
        """Test development environment detection"""
        with patch.dict(os.environ, {"NODE_ENV": "development"}, clear=False):
            assert determine_target_environment() == "dev"

        with patch.dict(os.environ, {"APP_MODE": "test"}, clear=False):
            assert determine_target_environment() == "dev"

        with patch.dict(os.environ, {"FLASK_DEBUG": "true"}, clear=False):
            assert determine_target_environment() == "dev"

    def test_determine_target_environment_production(self):
        """Test production environment detection (default)"""
        with patch.dict(os.environ, {"NODE_ENV": "", "APP_MODE": "", "FLASK_DEBUG": "false"}, clear=True):
            assert determine_target_environment() == "prd"

        with patch.dict(os.environ, {"NODE_ENV": "production"}, clear=True):
            assert determine_target_environment() == "prd"

    def test_get_env_port_development(self):
        """Test port retrieval for development environment"""
        with patch("config.services.APP_CONFIG", {"web_port": 7777}):
            with patch.dict(os.environ, {"DEV_PORT": "8888"}, clear=False):
                port = get_env_port("dev")
                assert port == 8888

            with patch.dict(os.environ, {"PORT": "9999"}, clear=True):
                port = get_env_port("dev")
                assert port == 9999

    def test_get_env_port_production(self):
        """Test port retrieval for production environment"""
        with patch("config.services.APP_CONFIG", {"web_port": 7777}):
            with patch.dict(os.environ, {"PRD_PORT": "8080"}, clear=False):
                port = get_env_port("prd")
                assert port == 8080

            with patch.dict(os.environ, {}, clear=True):
                port = get_env_port("prd")
                assert port == 7777

    def test_is_docker_environment_with_dockerenv(self):
        """Test Docker environment detection via .dockerenv file"""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            assert is_docker_environment() is True
            mock_exists.assert_called_with("/.dockerenv")

    def test_is_docker_environment_with_env_var(self):
        """Test Docker environment detection via environment variable"""
        with patch.dict(os.environ, {"DOCKER_CONTAINER": "true"}, clear=False):
            with patch("os.path.exists", return_value=False):
                assert is_docker_environment() is True

    def test_is_docker_environment_false(self):
        """Test non-Docker environment detection"""
        with patch("os.path.exists", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                assert is_docker_environment() is False

    def test_load_environment_config_existing_file(self):
        """Test loading environment configuration from existing .env file"""
        env_content = "TEST_VAR=test_value\n# This is a comment\nANOTHER_VAR=another_value\n"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", unittest.mock.mock_open(read_data=env_content)):
                with patch.dict(os.environ, {}, clear=True):
                    load_environment_config()
                    # Function should run without error

    def test_load_environment_config_missing_file(self):
        """Test handling of missing .env file"""
        with patch("pathlib.Path.exists", return_value=False):
            # Should not raise an exception
            load_environment_config()

    def test_load_environment_config_file_error(self):
        """Test handling of .env file read errors"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=IOError("File read error")):
                with patch("main.logger.warning") as mock_warning:
                    load_environment_config()
                    mock_warning.assert_called_once()

    @patch("main.logger")
    def test_validate_environment_consistency(self, mock_logger):
        """Test environment validation and logging"""
        with patch("main.determine_target_environment", return_value="dev"):
            with patch("main.is_docker_environment", return_value=True):
                with patch("main.get_env_port", return_value=7777):
                    result = validate_environment_consistency()

                    assert result == "dev"
                    mock_logger.info.assert_called()


class TestCommandLineParser:
    """Test command-line argument parsing"""

    def test_parse_args_minimal_web(self):
        """Test parsing minimal arguments for web mode"""
        test_args = ["--web"]

        with patch("sys.argv", ["main.py"] + test_args):
            args = parse_args()
            assert args.web is True
            assert args.protocol == "tcp"  # default
            assert args.log_level == "INFO"  # default

    def test_parse_args_full_cli_mode(self):
        """Test parsing full CLI arguments"""
        test_args = [
            "--src",
            "192.168.1.10",
            "--dst",
            "10.0.0.5",
            "--port",
            "80",
            "--protocol",
            "tcp",
            "--output",
            "/tmp/output.json",
            "--host",
            "fortigate.example.com",
            "--token",
            "test_token",
            "--username",
            "admin",
            "--password",
            "password",
            "--manager",
            "--log-level",
            "DEBUG",
        ]

        with patch("sys.argv", ["main.py"] + test_args):
            args = parse_args()

            assert args.src == "192.168.1.10"
            assert args.dst == "10.0.0.5"
            assert args.port == 80
            assert args.protocol == "tcp"
            assert args.output == "/tmp/output.json"
            assert args.host == "fortigate.example.com"
            assert args.token == "test_token"
            assert args.username == "admin"
            assert args.password == "password"
            assert args.manager is True
            assert args.log_level == "DEBUG"

    def test_parse_args_invalid_protocol(self):
        """Test handling of invalid protocol argument"""
        test_args = ["--protocol", "invalid"]

        with patch("sys.argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_invalid_log_level(self):
        """Test handling of invalid log level argument"""
        test_args = ["--log-level", "INVALID"]

        with patch("sys.argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()


class TestPacketAnalysis:
    """Test packet path analysis functionality"""

    @patch("main.FirewallRuleAnalyzer")
    def test_analyze_packet_path_success_fortigate(self, mock_analyzer_class):
        """Test successful packet analysis with FortiGate"""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.load_data.return_value = True
        mock_analyzer.trace_packet_path.return_value = {"path": ["firewall1", "firewall2"], "allowed": True}

        mock_api_client = Mock()

        result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", mock_api_client, manager=False)

        assert result is not None
        assert result["allowed"] is True
        assert len(result["path"]) == 2
        mock_analyzer.load_data.assert_called_once()
        mock_analyzer.trace_packet_path.assert_called_with("192.168.1.1", "10.0.0.1", 80, "tcp")

    @patch("main.FirewallRuleAnalyzer")
    def test_analyze_packet_path_success_fortimanager(self, mock_analyzer_class):
        """Test successful packet analysis with FortiManager"""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.load_all_firewalls.return_value = True
        mock_analyzer.trace_packet_path.return_value = {
            "path": ["firewall1"],
            "allowed": False,
            "blocked_by": {"firewall_id": "FW1", "policy_id": "123"},
        }

        mock_api_client = Mock()

        result = analyze_packet_path("192.168.1.1", "10.0.0.1", 443, "tcp", mock_api_client, manager=True)

        assert result is not None
        assert result["allowed"] is False
        assert "blocked_by" in result
        mock_analyzer.load_all_firewalls.assert_called_once()

    @patch("main.FirewallRuleAnalyzer")
    def test_analyze_packet_path_load_failure(self, mock_analyzer_class):
        """Test packet analysis with data load failure"""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.load_data.return_value = False

        mock_api_client = Mock()

        result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", mock_api_client, manager=False)

        assert result is None

    def test_analyze_packet_path_no_analyzer(self):
        """Test packet analysis when FirewallRuleAnalyzer is not available"""
        with patch("main.FirewallRuleAnalyzer", None):
            result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", Mock(), manager=False)
            assert result is None

    @patch("main.FirewallRuleAnalyzer")
    def test_analyze_packet_path_exception(self, mock_analyzer_class):
        """Test packet analysis with exception handling"""
        mock_analyzer_class.side_effect = Exception("Analysis error")

        result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", Mock(), manager=False)

        assert result is None


class TestVisualization:
    """Test path visualization functionality"""

    @patch("main.PathVisualizer")
    def test_visualize_path_success(self, mock_visualizer_class):
        """Test successful path visualization"""
        mock_visualizer = Mock()
        mock_visualizer_class.return_value = mock_visualizer
        mock_visualizer.generate_visualization_data.return_value = {
            "nodes": [{"id": "fw1"}, {"id": "fw2"}],
            "edges": [{"from": "fw1", "to": "fw2"}],
        }

        path_data = {"path": ["fw1", "fw2"], "allowed": True}

        result = visualize_path(path_data)

        assert result is not None
        assert "nodes" in result
        assert "edges" in result
        mock_visualizer.generate_visualization_data.assert_called_with(path_data)

    def test_visualize_path_no_visualizer(self):
        """Test visualization when PathVisualizer is not available"""
        with patch("main.PathVisualizer", None):
            result = visualize_path({"path": [], "allowed": True})
            assert result is None

    @patch("main.PathVisualizer")
    def test_visualize_path_exception(self, mock_visualizer_class):
        """Test visualization with exception handling"""
        mock_visualizer_class.side_effect = Exception("Visualization error")

        result = visualize_path({"path": [], "allowed": True})

        assert result is None


class TestFileOutput:
    """Test file output functionality"""

    def test_save_output_success(self):
        """Test successful file saving"""
        test_data = {"test": "data", "number": 123}

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = save_output(test_data, temp_path)
            assert result is True

            # Verify file contents
            with open(temp_path, "r", encoding="utf-8") as f:
                import json

                saved_data = json.load(f)
                assert saved_data == test_data

        finally:
            os.unlink(temp_path)

    def test_save_output_failure(self):
        """Test file saving failure"""
        test_data = {"test": "data"}
        invalid_path = "/invalid/path/file.json"

        result = save_output(test_data, invalid_path)
        assert result is False


class TestMainFunction:
    """Test main function and integration scenarios"""

    @patch("web_app.create_app")
    @patch("config.unified_settings.unified_settings")
    def test_main_web_mode_flask_only(self, mock_settings, mock_create_app):
        """Test main function in web mode with Flask only (no SocketIO)"""
        mock_app = Mock()
        mock_create_app.return_value = mock_app
        mock_settings.webapp.host = "0.0.0.0"
        mock_settings.webapp.debug = False

        test_args = ["--web"]

        with patch("sys.argv", ["main.py"] + test_args):
            with patch.dict(os.environ, {"DISABLE_SOCKETIO": "true"}, clear=False):
                with patch("main.determine_target_environment", return_value="dev"):
                    with patch("main.get_env_port", return_value=7777):
                        with patch("main.is_docker_environment", return_value=False):
                            main()

                            mock_create_app.assert_called_once()
                            mock_app.run.assert_called_once()

    @patch("web_app.create_app")
    @patch("config.unified_settings.unified_settings")
    @patch("flask_socketio.SocketIO")
    def test_main_web_mode_with_socketio(self, mock_socketio_class, mock_settings, mock_create_app):
        """Test main function in web mode with SocketIO"""
        mock_app = Mock()
        mock_create_app.return_value = mock_app
        mock_settings.webapp.host = "0.0.0.0"
        mock_settings.webapp.debug = False

        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio

        test_args = ["--web"]

        with patch("sys.argv", ["main.py"] + test_args):
            with patch.dict(os.environ, {}, clear=True):
                with patch("main.determine_target_environment", return_value="prd"):
                    with patch("main.get_env_port", return_value=7777):
                        with patch("main.is_docker_environment", return_value=True):
                            main()

                            mock_create_app.assert_called_once()
                            mock_socketio.run.assert_called_once()

    @patch("web_app.create_app")
    def test_main_web_mode_socketio_import_error(self, mock_create_app):
        """Test main function handling SocketIO import error"""
        mock_app = Mock()
        mock_create_app.return_value = mock_app

        test_args = ["--web"]

        with patch("sys.argv", ["main.py"] + test_args):
            with patch("flask_socketio.SocketIO", side_effect=ImportError("flask-socketio not found")):
                with patch("config.unified_settings.unified_settings") as mock_settings:
                    mock_settings.webapp.host = "0.0.0.0"
                    mock_settings.webapp.debug = False
                    with patch("main.determine_target_environment", return_value="dev"):
                        with patch("main.get_env_port", return_value=7777):
                            main()

                            mock_app.run.assert_called_once()

    def test_main_cli_mode_missing_required_args(self):
        """Test main function in CLI mode with missing required arguments"""
        test_args = ["--src", "192.168.1.1"]  # Missing dst and port

        with patch("sys.argv", ["main.py"] + test_args):
            with patch("builtins.print") as mock_print:
                result = main()

                assert result == 1
                mock_print.assert_called_once()

    @patch("main.FortiGateAPIClient")
    @patch("main.analyze_packet_path")
    @patch("main.visualize_path")
    def test_main_cli_mode_success_fortigate(self, mock_visualize, mock_analyze, mock_client_class):
        """Test successful CLI mode execution with FortiGate"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_analyze.return_value = {"path": ["fw1", "fw2"], "allowed": True}

        mock_visualize.return_value = {"nodes": [], "edges": []}

        test_args = [
            "--src",
            "192.168.1.1",
            "--dst",
            "10.0.0.1",
            "--port",
            "80",
            "--host",
            "fortigate.example.com",
            "--token",
            "test_token",
        ]

        with patch("sys.argv", ["main.py"] + test_args):
            with patch("builtins.print") as mock_print:
                result = main()

                assert result == 0
                mock_print.assert_called()

    @patch("main.FortiManagerAPIClient")
    @patch("main.analyze_packet_path")
    @patch("main.visualize_path")
    @patch("main.save_output")
    def test_main_cli_mode_with_output_file(self, mock_save, mock_visualize, mock_analyze, mock_client_class):
        """Test CLI mode with output file"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_analyze.return_value = {
            "path": ["fw1"],
            "allowed": False,
            "blocked_by": {"firewall_name": "FW1", "policy_id": "123"},
        }

        mock_visualize.return_value = {"data": "visualization"}
        mock_save.return_value = True

        test_args = [
            "--src",
            "192.168.1.1",
            "--dst",
            "10.0.0.1",
            "--port",
            "443",
            "--output",
            "/tmp/test_output.json",
            "--manager",
        ]

        with patch("sys.argv", ["main.py"] + test_args):
            with patch("builtins.print") as mock_print:
                result = main()

                assert result == 0
                mock_save.assert_called_with({"data": "visualization"}, "/tmp/test_output.json")

    @patch("main.analyze_packet_path")
    def test_main_cli_mode_analysis_failure(self, mock_analyze):
        """Test CLI mode with analysis failure"""
        mock_analyze.return_value = None

        test_args = ["--src", "192.168.1.1", "--dst", "10.0.0.1", "--port", "80"]

        with patch("sys.argv", ["main.py"] + test_args):
            result = main()
            assert result == 1

    @patch("main.analyze_packet_path")
    @patch("main.visualize_path")
    def test_main_cli_mode_visualization_failure(self, mock_visualize, mock_analyze):
        """Test CLI mode with visualization failure"""
        mock_analyze.return_value = {"path": [], "allowed": True}
        mock_visualize.return_value = None

        test_args = ["--src", "192.168.1.1", "--dst", "10.0.0.1", "--port", "80"]

        with patch("sys.argv", ["main.py"] + test_args):
            result = main()
            assert result == 1

    @patch("main.load_environment_config")
    def test_main_environment_setup(self, mock_load_env):
        """Test main function environment setup"""
        test_args = ["--web", "--log-level", "DEBUG"]

        with patch("sys.argv", ["main.py"] + test_args):
            with patch("web_app.create_app"):
                with patch("config.unified_settings.unified_settings") as mock_settings:
                    mock_settings.webapp.host = "0.0.0.0"
                    mock_settings.webapp.debug = False
                    with patch("main.determine_target_environment", return_value="dev"):
                        with patch("main.get_env_port", return_value=7777):
                            with patch.dict(os.environ, {"DISABLE_SOCKETIO": "true"}):
                                main()

                                mock_load_env.assert_called_once()
                                assert os.environ.get("LOG_LEVEL") == "DEBUG"


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases"""

    def test_environment_configuration_priority(self):
        """Test environment variable priority in configuration"""
        with patch.dict(
            os.environ,
            {
                "NODE_ENV": "development",
                "APP_MODE": "production",  # Should be overridden
                "FLASK_DEBUG": "false",  # Should be overridden by NODE_ENV
            },
            clear=False,
        ):
            env = determine_target_environment()
            assert env == "dev"  # NODE_ENV should take precedence

    @patch("main.logger")
    def test_debug_mode_force_enable(self, mock_logger):
        """Test forced debug mode in production"""
        with patch.dict(os.environ, {"FORCE_DEBUG": "true", "DISABLE_SOCKETIO": "true"}, clear=False):
            with patch("main.determine_target_environment", return_value="prd"):
                with patch("main.validate_environment_consistency"):
                    with patch("web_app.create_app"):
                        with patch("config.unified_settings.unified_settings") as mock_settings:
                            mock_settings.webapp.host = "0.0.0.0"
                            mock_settings.webapp.debug = False
                            with patch("main.get_env_port", return_value=7777):
                                with patch("sys.argv", ["main.py", "--web"]):
                                    main()

                                    # Should log warning about forced debug mode
                                    mock_logger.warning.assert_called()

    def test_packet_analysis_full_workflow(self):
        """Test complete packet analysis workflow"""
        with patch("main.FirewallRuleAnalyzer") as mock_analyzer_class:
            with patch("main.PathVisualizer") as mock_visualizer_class:
                # Setup mocks
                mock_analyzer = Mock()
                mock_analyzer_class.return_value = mock_analyzer
                mock_analyzer.load_data.return_value = True
                mock_analyzer.trace_packet_path.return_value = {
                    "path": [{"firewall": "FW1"}, {"firewall": "FW2"}],
                    "allowed": True,
                }

                mock_visualizer = Mock()
                mock_visualizer_class.return_value = mock_visualizer
                mock_visualizer.generate_visualization_data.return_value = {"visualization": "data"}

                # Test analysis
                api_client = Mock()
                analysis_result = analyze_packet_path("10.1.1.1", "10.2.2.2", 443, "tcp", api_client)

                # Test visualization
                viz_result = visualize_path(analysis_result)

                assert analysis_result["allowed"] is True
                assert viz_result["visualization"] == "data"
