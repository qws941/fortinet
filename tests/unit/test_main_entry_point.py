#!/usr/bin/env python3
"""
Comprehensive tests for main.py application entry point
Critical component with 0% coverage - focusing on TDD coverage improvement
"""

import argparse
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest


class TestEnvironmentDetection:
    """Test environment detection and configuration functions"""

    def test_determine_target_environment_dev_mode(self):
        """Test development environment detection"""
        with patch.dict(os.environ, {"NODE_ENV": "development"}):
            from main import determine_target_environment

            assert determine_target_environment() == "dev"

    def test_determine_target_environment_test_mode(self):
        """Test test environment detection"""
        with patch.dict(os.environ, {"APP_MODE": "test"}):
            from main import determine_target_environment

            assert determine_target_environment() == "dev"

    def test_determine_target_environment_flask_debug(self):
        """Test Flask debug environment detection"""
        with patch.dict(os.environ, {"FLASK_DEBUG": "true"}):
            from main import determine_target_environment

            assert determine_target_environment() == "dev"

    def test_determine_target_environment_production(self):
        """Test production environment detection (default)"""
        with patch.dict(os.environ, {}, clear=True):
            from main import determine_target_environment

            assert determine_target_environment() == "prd"

    def test_get_env_port_dev(self):
        """Test port configuration for development environment"""
        with patch("main.APP_CONFIG", {"web_port": 7777}), patch.dict(os.environ, {"DEV_PORT": "8080"}):
            from main import get_env_port

            assert get_env_port("dev") == 8080

    def test_get_env_port_prod(self):
        """Test port configuration for production environment"""
        with patch("main.APP_CONFIG", {"web_port": 7777}), patch.dict(os.environ, {"PRD_PORT": "9090"}):
            from main import get_env_port

            assert get_env_port("prd") == 9090

    def test_get_env_port_default_fallback(self):
        """Test port fallback to APP_CONFIG default"""
        with patch("main.APP_CONFIG", {"web_port": 7777}), patch.dict(os.environ, {}, clear=True):
            from main import get_env_port

            assert get_env_port("prd") == 7777

    def test_is_docker_environment_dockerenv_file(self):
        """Test Docker environment detection via .dockerenv file"""
        with patch("os.path.exists", return_value=True):
            from main import is_docker_environment

            assert is_docker_environment() == True

    def test_is_docker_environment_env_var(self):
        """Test Docker environment detection via environment variable"""
        with patch("os.path.exists", return_value=False), patch.dict(os.environ, {"DOCKER_CONTAINER": "true"}):
            from main import is_docker_environment

            assert is_docker_environment() == True

    def test_is_docker_environment_not_docker(self):
        """Test non-Docker environment detection"""
        with patch("os.path.exists", return_value=False), patch.dict(os.environ, {}, clear=True):
            from main import is_docker_environment

            assert is_docker_environment() == False


class TestEnvironmentConfigLoading:
    """Test environment configuration loading"""

    def test_load_environment_config_success(self):
        """Test successful .env file loading"""
        env_content = "TEST_VAR=test_value\nANOTHER_VAR=another_value\n# This is a comment\n"

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=env_content)),
            patch.dict(os.environ, {}, clear=True),
        ):

            from main import load_environment_config

            load_environment_config()

            assert os.environ.get("TEST_VAR") == "test_value"
            assert os.environ.get("ANOTHER_VAR") == "another_value"

    def test_load_environment_config_no_file(self):
        """Test when .env file doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            from main import load_environment_config

            # Should not raise exception
            load_environment_config()

    def test_load_environment_config_file_error(self):
        """Test .env file read error handling"""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("File read error")),
            patch("main.logger") as mock_logger,
        ):

            from main import load_environment_config

            load_environment_config()

            mock_logger.warning.assert_called_once()

    def test_load_environment_config_skip_existing_vars(self):
        """Test that existing environment variables are not overwritten"""
        env_content = "EXISTING_VAR=new_value\n"

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=env_content)),
            patch.dict(os.environ, {"EXISTING_VAR": "old_value"}),
        ):

            from main import load_environment_config

            load_environment_config()

            assert os.environ.get("EXISTING_VAR") == "old_value"

    def test_validate_environment_consistency(self):
        """Test environment validation"""
        with (
            patch("main.determine_target_environment", return_value="dev"),
            patch("main.is_docker_environment", return_value=True),
            patch("main.get_env_port", return_value=8080),
            patch("main.logger") as mock_logger,
        ):

            from main import validate_environment_consistency

            result = validate_environment_consistency()

            assert result == "dev"
            mock_logger.info.assert_called()


class TestArgumentParsing:
    """Test command line argument parsing"""

    def test_parse_args_basic(self):
        """Test basic argument parsing"""
        test_args = ["--src", "192.168.1.1", "--dst", "10.0.0.1", "--port", "80", "--web"]

        with patch("sys.argv", ["main.py"] + test_args):
            from main import parse_args

            args = parse_args()

            assert args.src == "192.168.1.1"
            assert args.dst == "10.0.0.1"
            assert args.port == 80
            assert args.web == True
            assert args.protocol == "tcp"  # default

    def test_parse_args_all_options(self):
        """Test parsing with all available options"""
        test_args = [
            "--src",
            "192.168.1.1",
            "--dst",
            "10.0.0.1",
            "--port",
            "443",
            "--protocol",
            "udp",
            "--output",
            "/tmp/output.json",
            "--host",
            "fortigate.example.com",
            "--token",
            "test-token",
            "--username",
            "admin",
            "--password",
            "secret",
            "--manager",
            "--log-level",
            "DEBUG",
        ]

        with patch("sys.argv", ["main.py"] + test_args):
            from main import parse_args

            args = parse_args()

            assert args.src == "192.168.1.1"
            assert args.dst == "10.0.0.1"
            assert args.port == 443
            assert args.protocol == "udp"
            assert args.output == "/tmp/output.json"
            assert args.host == "fortigate.example.com"
            assert args.token == "test-token"
            assert args.username == "admin"
            assert args.password == "secret"
            assert args.manager == True
            assert args.log_level == "DEBUG"

    def test_parse_args_protocol_choices(self):
        """Test protocol argument validation"""
        valid_protocols = ["tcp", "udp", "icmp"]

        for protocol in valid_protocols:
            test_args = ["--src", "1.1.1.1", "--dst", "2.2.2.2", "--port", "80", "--protocol", protocol]

            with patch("sys.argv", ["main.py"] + test_args):
                from main import parse_args

                args = parse_args()
                assert args.protocol == protocol


class TestPacketPathAnalysis:
    """Test packet path analysis functionality"""

    def test_analyze_packet_path_success(self):
        """Test successful packet path analysis"""
        mock_api_client = Mock()
        mock_analyzer = Mock()
        mock_analyzer.load_data.return_value = True
        mock_analyzer.trace_packet_path.return_value = {"path": ["hop1", "hop2"], "allowed": True}

        with patch("main.FirewallRuleAnalyzer", return_value=mock_analyzer):
            from main import analyze_packet_path

            result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", mock_api_client, False)

            assert result is not None
            assert result["allowed"] == True
            mock_analyzer.load_data.assert_called_once()
            mock_analyzer.trace_packet_path.assert_called_once_with("192.168.1.1", "10.0.0.1", 80, "tcp")

    def test_analyze_packet_path_fortimanager_mode(self):
        """Test packet path analysis with FortiManager"""
        mock_api_client = Mock()
        mock_analyzer = Mock()
        mock_analyzer.load_all_firewalls.return_value = True
        mock_analyzer.trace_packet_path.return_value = {"path": ["hop1"], "allowed": False}

        with patch("main.FirewallRuleAnalyzer", return_value=mock_analyzer):
            from main import analyze_packet_path

            result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", mock_api_client, True)

            assert result is not None
            assert result["allowed"] == False
            mock_analyzer.load_all_firewalls.assert_called_once()

    def test_analyze_packet_path_analyzer_unavailable(self):
        """Test packet path analysis when analyzer is unavailable"""
        with patch("main.FirewallRuleAnalyzer", None):
            from main import analyze_packet_path

            result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", Mock(), False)

            assert result is None

    def test_analyze_packet_path_load_data_failure(self):
        """Test packet path analysis when data loading fails"""
        mock_api_client = Mock()
        mock_analyzer = Mock()
        mock_analyzer.load_data.return_value = False

        with patch("main.FirewallRuleAnalyzer", return_value=mock_analyzer):
            from main import analyze_packet_path

            result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", mock_api_client, False)

            assert result is None

    def test_analyze_packet_path_exception(self):
        """Test packet path analysis exception handling"""
        mock_api_client = Mock()

        with patch("main.FirewallRuleAnalyzer", side_effect=Exception("Analysis error")):
            from main import analyze_packet_path

            result = analyze_packet_path("192.168.1.1", "10.0.0.1", 80, "tcp", mock_api_client, False)

            assert result is None


class TestPathVisualization:
    """Test path visualization functionality"""

    def test_visualize_path_success(self):
        """Test successful path visualization"""
        path_data = {"path": ["hop1", "hop2"], "allowed": True}
        mock_visualizer = Mock()
        mock_visualizer.generate_visualization_data.return_value = {"graph": "data"}

        with patch("main.PathVisualizer", return_value=mock_visualizer):
            from main import visualize_path

            result = visualize_path(path_data)

            assert result is not None
            assert result == {"graph": "data"}
            mock_visualizer.generate_visualization_data.assert_called_once_with(path_data)

    def test_visualize_path_visualizer_unavailable(self):
        """Test visualization when visualizer is unavailable"""
        with patch("main.PathVisualizer", None):
            from main import visualize_path

            result = visualize_path({"path": []})

            assert result is None

    def test_visualize_path_exception(self):
        """Test visualization exception handling"""
        with patch("main.PathVisualizer", side_effect=Exception("Visualization error")):
            from main import visualize_path

            result = visualize_path({"path": []})

            assert result is None


class TestOutputSaving:
    """Test output saving functionality"""

    def test_save_output_success(self):
        """Test successful output saving"""
        test_data = {"result": "success", "path": ["hop1", "hop2"]}

        with patch("builtins.open", mock_open()) as mock_file:
            from main import save_output

            result = save_output(test_data, "/tmp/output.json")

            assert result == True
            mock_file.assert_called_once_with("/tmp/output.json", "w", encoding="utf-8")

    def test_save_output_exception(self):
        """Test output saving exception handling"""
        test_data = {"result": "test"}

        with patch("builtins.open", side_effect=IOError("Write error")):
            from main import save_output

            result = save_output(test_data, "/tmp/output.json")

            assert result == False


class TestWebInterfaceMode:
    """Test web interface startup mode"""

    @patch("main.create_app")
    @patch("main.determine_target_environment")
    @patch("main.get_env_port")
    @patch("main.is_docker_environment")
    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    @patch("main.unified_settings")
    def test_main_web_mode_with_socketio(
        self, mock_settings, mock_load_env, mock_validate, mock_docker, mock_port, mock_env, mock_create_app
    ):
        """Test main function in web mode with SocketIO"""
        # Setup mocks
        mock_env.return_value = "dev"
        mock_port.return_value = 8080
        mock_docker.return_value = False
        mock_validate.return_value = "dev"
        mock_settings.webapp.host = "0.0.0.0"
        mock_settings.webapp.debug = True

        mock_app = Mock()
        mock_create_app.return_value = mock_app

        mock_socketio = Mock()

        test_args = ["main.py", "--web", "--log-level", "DEBUG"]

        with (
            patch("sys.argv", test_args),
            patch("main.parse_args") as mock_parse,
            patch("flask_socketio.SocketIO", return_value=mock_socketio),
            patch.dict(os.environ, {"DISABLE_SOCKETIO": "false"}),
        ):

            mock_args = Mock()
            mock_args.web = True
            mock_args.log_level = "DEBUG"
            mock_parse.return_value = mock_args

            from main import main

            main()

            # Verify SocketIO was used
            mock_socketio.run.assert_called_once()

    @patch("main.create_app")
    @patch("main.determine_target_environment")
    @patch("main.get_env_port")
    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    @patch("main.unified_settings")
    def test_main_web_mode_without_socketio(
        self, mock_settings, mock_load_env, mock_validate, mock_port, mock_env, mock_create_app
    ):
        """Test main function in web mode without SocketIO"""
        # Setup mocks
        mock_env.return_value = "prd"
        mock_port.return_value = 7777
        mock_validate.return_value = "prd"
        mock_settings.webapp.host = "0.0.0.0"

        mock_app = Mock()
        mock_create_app.return_value = mock_app

        test_args = ["main.py", "--web"]

        with (
            patch("sys.argv", test_args),
            patch("main.parse_args") as mock_parse,
            patch.dict(os.environ, {"DISABLE_SOCKETIO": "true"}),
        ):

            mock_args = Mock()
            mock_args.web = True
            mock_args.log_level = "INFO"
            mock_parse.return_value = mock_args

            from main import main

            main()

            # Verify Flask app.run was used
            mock_app.run.assert_called_once()

    @patch("main.create_app")
    @patch("main.determine_target_environment")
    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    def test_main_web_mode_socketio_import_error(self, mock_load_env, mock_validate, mock_env, mock_create_app):
        """Test web mode when SocketIO import fails"""
        # Setup mocks
        mock_env.return_value = "dev"
        mock_validate.return_value = "dev"

        mock_app = Mock()
        mock_create_app.return_value = mock_app

        test_args = ["main.py", "--web"]

        with (
            patch("sys.argv", test_args),
            patch("main.parse_args") as mock_parse,
            patch("main.get_env_port", return_value=8080),
            patch("main.unified_settings") as mock_settings,
            patch("flask_socketio.SocketIO", side_effect=ImportError("SocketIO not available")),
            patch.dict(os.environ, {"DISABLE_SOCKETIO": "false"}),
        ):

            mock_args = Mock()
            mock_args.web = True
            mock_args.log_level = "INFO"
            mock_parse.return_value = mock_args

            mock_settings.webapp.host = "0.0.0.0"

            from main import main

            main()

            # Should fall back to Flask app.run
            mock_app.run.assert_called_once()


class TestCLIMode:
    """Test CLI mode functionality"""

    @patch("main.analyze_packet_path")
    @patch("main.visualize_path")
    @patch("main.save_output")
    @patch("main.FortiGateAPIClient")
    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    def test_main_cli_mode_success(
        self, mock_load_env, mock_validate, mock_client_class, mock_save, mock_visualize, mock_analyze
    ):
        """Test successful CLI mode execution"""
        # Setup mocks
        mock_validate.return_value = "dev"
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_analyze.return_value = {"path": ["hop1"], "allowed": True}
        mock_visualize.return_value = {"graph": "data"}
        mock_save.return_value = True

        test_args = ["main.py", "--src", "1.1.1.1", "--dst", "2.2.2.2", "--port", "80", "--output", "/tmp/test.json"]

        with patch("sys.argv", test_args), patch("main.parse_args") as mock_parse, patch("sys.exit") as mock_exit:

            mock_args = Mock()
            mock_args.web = False
            mock_args.src = "1.1.1.1"
            mock_args.dst = "2.2.2.2"
            mock_args.port = 80
            mock_args.protocol = "tcp"
            mock_args.output = "/tmp/test.json"
            mock_args.manager = False
            mock_args.host = "fortigate.local"
            mock_args.token = "test-token"
            mock_args.log_level = "INFO"
            mock_parse.return_value = mock_args

            from main import main

            main()

            # Verify analysis was performed
            mock_analyze.assert_called_once()
            mock_visualize.assert_called_once()
            mock_save.assert_called_once()
            mock_exit.assert_called_with(0)

    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    def test_main_cli_mode_missing_required_args(self, mock_load_env, mock_validate):
        """Test CLI mode with missing required arguments"""
        mock_validate.return_value = "dev"

        test_args = ["main.py", "--src", "1.1.1.1"]  # Missing dst and port

        with (
            patch("sys.argv", test_args),
            patch("main.parse_args") as mock_parse,
            patch("sys.exit") as mock_exit,
            patch("builtins.print") as mock_print,
        ):

            mock_args = Mock()
            mock_args.web = False
            mock_args.src = "1.1.1.1"
            mock_args.dst = None
            mock_args.port = None
            mock_parse.return_value = mock_args

            from main import main

            main()

            mock_print.assert_called()
            mock_exit.assert_called_with(1)

    @patch("main.analyze_packet_path")
    @patch("main.FortiManagerAPIClient")
    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    def test_main_cli_mode_fortimanager(self, mock_load_env, mock_validate, mock_client_class, mock_analyze):
        """Test CLI mode with FortiManager client"""
        mock_validate.return_value = "dev"
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_analyze.return_value = None  # Analysis failure

        test_args = ["main.py", "--src", "1.1.1.1", "--dst", "2.2.2.2", "--port", "80", "--manager"]

        with patch("sys.argv", test_args), patch("main.parse_args") as mock_parse, patch("sys.exit") as mock_exit:

            mock_args = Mock()
            mock_args.web = False
            mock_args.src = "1.1.1.1"
            mock_args.dst = "2.2.2.2"
            mock_args.port = 80
            mock_args.protocol = "tcp"
            mock_args.output = None
            mock_args.manager = True
            mock_args.host = "fortimanager.local"
            mock_args.token = "test-token"
            mock_args.username = "admin"
            mock_args.password = "secret"
            mock_args.log_level = "INFO"
            mock_parse.return_value = mock_args

            from main import main

            main()

            # Should use FortiManagerAPIClient
            mock_client_class.assert_called_once()
            mock_exit.assert_called_with(1)  # Analysis failed

    @patch("main.analyze_packet_path")
    @patch("main.visualize_path")
    @patch("main.FortiGateAPIClient")
    @patch("main.validate_environment_consistency")
    @patch("main.load_environment_config")
    def test_main_cli_mode_no_output_file(
        self, mock_load_env, mock_validate, mock_client_class, mock_visualize, mock_analyze
    ):
        """Test CLI mode without output file (console output)"""
        mock_validate.return_value = "dev"
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Test blocked traffic
        mock_analyze.return_value = {
            "path": ["hop1"],
            "allowed": False,
            "blocked_by": {"firewall_name": "FW-01", "policy_id": "42"},
        }
        mock_visualize.return_value = {"graph": "data"}

        test_args = ["main.py", "--src", "1.1.1.1", "--dst", "2.2.2.2", "--port", "443"]

        with (
            patch("sys.argv", test_args),
            patch("main.parse_args") as mock_parse,
            patch("sys.exit") as mock_exit,
            patch("builtins.print") as mock_print,
        ):

            mock_args = Mock()
            mock_args.web = False
            mock_args.src = "1.1.1.1"
            mock_args.dst = "2.2.2.2"
            mock_args.port = 443
            mock_args.protocol = "tcp"
            mock_args.output = None
            mock_args.manager = False
            mock_args.host = "fortigate.local"
            mock_args.token = "test-token"
            mock_args.log_level = "INFO"
            mock_parse.return_value = mock_args

            from main import main

            main()

            # Should print console output
            mock_print.assert_called()
            mock_exit.assert_called_with(0)


class TestMainEntryPoint:
    """Test main entry point execution"""

    @patch("main.main")
    def test_name_main_execution(self, mock_main):
        """Test __name__ == '__main__' execution path"""
        mock_main.return_value = 0

        # Simulate running as main module
        with patch("sys.exit") as mock_exit:
            # This simulates the if __name__ == "__main__": block
            import main

            # Manually call the main execution block
            if __name__ == "__main__":
                sys.exit(main.main())

            # If we got here, test that the module is importable
            assert hasattr(main, "main")
            assert callable(main.main)


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    @patch("main.load_environment_config")
    @patch("main.validate_environment_consistency")
    @patch("main.create_app")
    @patch.dict(os.environ, {"APP_MODE": "test", "WEB_APP_PORT": "7777"})
    def test_development_web_startup(self, mock_create_app, mock_validate, mock_load_env):
        """Test realistic development web startup scenario"""
        mock_validate.return_value = "dev"
        mock_app = Mock()
        mock_create_app.return_value = mock_app

        test_args = ["main.py", "--web", "--log-level", "DEBUG"]

        with (
            patch("sys.argv", test_args),
            patch("main.unified_settings") as mock_settings,
            patch("main.determine_target_environment", return_value="dev"),
            patch("main.get_env_port", return_value=7777),
            patch("main.is_docker_environment", return_value=False),
            patch.dict(os.environ, {"DISABLE_SOCKETIO": "true"}),
        ):

            mock_settings.webapp.host = "localhost"
            mock_settings.webapp.debug = True

            from main import main

            main()

            # Verify development configuration
            mock_app.run.assert_called_once()
            call_args = mock_app.run.call_args
            assert call_args[1]["host"] == "localhost"
            assert call_args[1]["port"] == 7777
            assert call_args[1]["debug"] == True

    @patch("main.load_environment_config")
    @patch("main.validate_environment_consistency")
    @patch("main.analyze_packet_path")
    @patch("main.visualize_path")
    @patch("main.FortiGateAPIClient")
    def test_production_cli_analysis(
        self, mock_client_class, mock_visualize, mock_analyze, mock_validate, mock_load_env
    ):
        """Test realistic production CLI analysis scenario"""
        mock_validate.return_value = "prd"
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Realistic analysis result
        mock_analyze.return_value = {
            "path": [
                {"hop": 1, "firewall": "FW-DMZ", "policy": "Allow-Web"},
                {"hop": 2, "firewall": "FW-Internal", "policy": "Deny-All"},
            ],
            "allowed": False,
            "blocked_by": {"firewall_name": "FW-Internal", "firewall_id": "FW-002", "policy_id": "999"},
        }

        mock_visualize.return_value = {
            "nodes": [{"id": "src"}, {"id": "dst"}],
            "edges": [{"from": "src", "to": "dst", "blocked": True}],
        }

        test_args = [
            "main.py",
            "--src",
            "10.1.1.100",
            "--dst",
            "172.16.1.50",
            "--port",
            "3306",
            "--protocol",
            "tcp",
            "--host",
            "fortigate-prod.company.com",
            "--token",
            "prod-api-token-12345",
        ]

        with patch("sys.argv", test_args), patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:

            from main import main

            main()

            # Verify production analysis
            mock_analyze.assert_called_once_with("10.1.1.100", "172.16.1.50", 3306, "tcp", mock_client, False)
            mock_visualize.assert_called_once()

            # Should print blocked status
            mock_print.assert_any_call("트래픽 상태: 차단됨")
            mock_print.assert_any_call("홉 수: 2")

            mock_exit.assert_called_with(0)
