#!/usr/bin/env python3

"""
FortiGate Nextrade - Cloud Native Main Entry Point
CNCF compliant application entry point following 12-factor app principles
"""

import os
import sys
import argparse
import signal
from typing import Optional

# Add src directory to Python path for backward compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from internal.app.server import create_app
from pkg.config.settings import get_configuration
from pkg.monitoring.health import HealthChecker
from utils.unified_logger import setup_module_logger

logger = setup_module_logger("cmd.fortinet.main")

def signal_handler(signum, frame):
    """Graceful shutdown handler for cloud native environments"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def parse_arguments():
    """Parse command line arguments following cloud native practices"""
    parser = argparse.ArgumentParser(
        description="FortiGate Nextrade - Cloud Native Network Security Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  APP_MODE              Application mode (production, development, test)
  WEB_APP_PORT         HTTP server port (default: 7777)
  OFFLINE_MODE         Enable offline mode (true/false)
  LOG_LEVEL            Logging level (DEBUG, INFO, WARNING, ERROR)
  
Examples:
  python main.py --web                    # Start web server
  python main.py --health                 # Run health check
  python main.py --analyze /path/to/file  # Analyze configuration
        """
    )
    
    # Operational commands
    parser.add_argument('--web', action='store_true',
                       help='Start web application server')
    parser.add_argument('--health', action='store_true',
                       help='Perform health check and exit')
    parser.add_argument('--version', action='store_true',
                       help='Show version information')
    
    # Analysis commands
    parser.add_argument('--analyze', metavar='FILE',
                       help='Analyze FortiGate configuration file')
    parser.add_argument('--report', metavar='FORMAT', default='json',
                       choices=['json', 'yaml', 'text'],
                       help='Report format for analysis (default: json)')
    
    # Service discovery and configuration
    parser.add_argument('--config', metavar='PATH',
                       help='Override configuration file path')
    parser.add_argument('--port', type=int, metavar='PORT',
                       help='Override HTTP server port')
    
    return parser.parse_args()

def run_health_check() -> int:
    """Run health check and return exit code"""
    try:
        health_checker = HealthChecker()
        if health_checker.check_all():
            logger.info("✅ All health checks passed")
            print("OK - All services healthy")
            return 0
        else:
            logger.error("❌ Health check failed")
            print("FAIL - Some services unhealthy")
            return 1
    except Exception as e:
        logger.error(f"Health check error: {e}")
        print(f"ERROR - Health check failed: {e}")
        return 1

def run_analysis(file_path: str, report_format: str) -> int:
    """Run configuration analysis"""
    try:
        # Import analysis modules conditionally
        from analysis.analyzer import FirewallRuleAnalyzer
        from analysis.visualizer import PathVisualizer
        
        analyzer = FirewallRuleAnalyzer()
        result = analyzer.analyze_file(file_path)
        
        if report_format == 'json':
            import json
            print(json.dumps(result, indent=2))
        elif report_format == 'yaml':
            import yaml
            print(yaml.dump(result, default_flow_style=False))
        else:
            print(f"Analysis Results for {file_path}:")
            print("-" * 50)
            for key, value in result.items():
                print(f"{key}: {value}")
        
        return 0
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"ERROR - Analysis failed: {e}")
        return 1

def show_version():
    """Show version information"""
    try:
        version_file = os.path.join(project_root, 'VERSION')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                version = f.read().strip()
        else:
            version = "development"
        
        print(f"FortiGate Nextrade v{version}")
        print("Cloud Native Network Security Platform")
        print("Build: CNCF Compliant")
        return 0
    except Exception as e:
        logger.error(f"Version check failed: {e}")
        return 1

def main():
    """Main entry point following cloud native best practices"""
    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()
        
        # Parse arguments
        args = parse_arguments()
        
        # Load configuration
        config = get_configuration(args.config)
        
        # Handle version command
        if args.version:
            return show_version()
        
        # Handle health check command
        if args.health:
            return run_health_check()
        
        # Handle analysis command
        if args.analyze:
            return run_analysis(args.analyze, args.report)
        
        # Handle web server command (default)
        if args.web or not any([args.health, args.analyze, args.version]):
            logger.info("Starting FortiGate Nextrade web server...")
            
            # Create Flask application
            app = create_app(config)
            
            # Determine port
            port = args.port or config.get('web_port', 7777)
            
            # Start server with cloud native configurations
            app.run(
                host='0.0.0.0',  # Cloud native: bind to all interfaces
                port=port,
                debug=config.get('debug', False),
                threaded=True,   # Enable threading for better performance
                use_reloader=False  # Disable in production
            )
            return 0
        
        # If no command specified, show help
        parse_arguments().print_help()
        return 1
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        print(f"FATAL: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)