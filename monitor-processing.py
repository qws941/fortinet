#!/usr/bin/env python3
"""
Real-time monitoring of Claude Agent System processing
Press Ctrl+C to interrupt
"""

import redis
import json
import time
import sys
import os
from datetime import datetime
import signal

class ProcessingMonitor:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.running = True
        self.stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'start_time': time.time()
        }

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n⚠️  Monitoring interrupted by user")
        self.running = False
        self.print_summary()
        sys.exit(0)

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def get_agent_status(self):
        """Get current status of all agents"""
        agents = self.redis.hgetall("agents:registry")
        agent_status = []

        for agent_id, agent_data in agents.items():
            data = json.loads(agent_data)
            heartbeat = self.redis.get(f"agents:heartbeat:{agent_id}")

            status_info = {
                'id': agent_id[:8],
                'type': data.get('agent_type', 'unknown'),
                'status': 'offline',
                'cpu': 0,
                'memory': 0,
                'tasks': 0,
                'current_task': None
            }

            if heartbeat:
                hb_data = json.loads(heartbeat)
                status_info['status'] = hb_data.get('status', 'idle')
                status_info['current_task'] = hb_data.get('current_task')
                metrics = hb_data.get('metrics', {})
                status_info['cpu'] = metrics.get('cpu_usage', 0)
                status_info['memory'] = metrics.get('memory_usage', 0)
                status_info['tasks'] = metrics.get('tasks_processed', 0)

            agent_status.append(status_info)

        return sorted(agent_status, key=lambda x: (x['type'], x['id']))

    def get_queue_status(self):
        """Get status of all task queues"""
        queues = ['analyzer', 'executor', 'monitor', 'researcher', 'general']
        queue_status = {}

        for queue in queues:
            length = self.redis.llen(f"tasks:{queue}")
            queue_status[queue] = length

        return queue_status

    def get_recent_results(self, limit=5):
        """Get recent task results"""
        results = []
        result_keys = self.redis.keys("results:*")

        for key in result_keys[-limit:]:
            result_data = self.redis.lrange(key, 0, -1)
            if result_data:
                try:
                    data = json.loads(result_data[0])
                    results.append({
                        'task_id': key.split(':')[1][:8],
                        'status': data.get('status', 'unknown'),
                        'agent': data.get('agent_id', 'unknown')[:8],
                        'time': data.get('processing_time', 0)
                    })
                except:
                    pass

        return results

    def display_dashboard(self):
        """Display real-time monitoring dashboard"""
        self.clear_screen()

        print("=" * 80)
        print(" Claude Agent System - Real-time Processing Monitor".center(80))
        print(" Press Ctrl+C to exit".center(80))
        print("=" * 80)

        # Current time
        print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Agent Status
        agents = self.get_agent_status()
        print("\n👥 Agent Status:")
        print("-" * 70)
        print(f"{'ID':<10} {'Type':<12} {'Status':<12} {'CPU':<8} {'Memory':<8} {'Tasks':<8}")
        print("-" * 70)

        for agent in agents:
            status_emoji = {
                'idle': '🟢',
                'processing': '🔵',
                'offline': '⚫',
                'busy': '🟡'
            }.get(agent['status'], '⚪')

            print(f"{agent['id']:<10} {agent['type']:<12} "
                  f"{status_emoji} {agent['status']:<10} "
                  f"{agent['cpu']:>6.1f}% "
                  f"{agent['memory']:>7.1f}% "
                  f"{agent['tasks']:>7}")

        # Queue Status
        queues = self.get_queue_status()
        print("\n📋 Queue Status:")
        print("-" * 70)

        for queue, length in queues.items():
            bar_length = min(length, 50)
            bar = '█' * bar_length + '░' * (50 - bar_length)
            print(f"{queue:<12}: [{bar}] {length:>3}")

        # Recent Results
        results = self.get_recent_results()
        if results:
            print("\n📊 Recent Tasks:")
            print("-" * 70)
            print(f"{'Task ID':<10} {'Status':<10} {'Agent':<10} {'Time (s)':<10}")
            print("-" * 70)

            for result in results:
                status_icon = '✅' if result['status'] == 'success' else '❌'
                print(f"{result['task_id']:<10} {status_icon} {result['status']:<8} "
                      f"{result['agent']:<10} {result['time']:>8.2f}")

        # Overall Stats
        runtime = time.time() - self.stats['start_time']
        print("\n📈 Session Statistics:")
        print("-" * 70)
        print(f"Runtime: {runtime:.0f}s | "
              f"Submitted: {self.stats['tasks_submitted']} | "
              f"Completed: {self.stats['tasks_completed']} | "
              f"Failed: {self.stats['tasks_failed']}")

        # Processing indicators
        active_agents = sum(1 for a in agents if a['status'] == 'processing')
        total_queued = sum(queues.values())

        print("\n" + "=" * 80)
        if active_agents > 0:
            print(f"🔄 Processing: {active_agents} agents active, {total_queued} tasks queued")
        else:
            print(f"⏸️  Idle: No active processing, {total_queued} tasks queued")

    def print_summary(self):
        """Print final summary"""
        runtime = time.time() - self.stats['start_time']
        print("\n" + "=" * 80)
        print("Final Summary:")
        print("-" * 80)
        print(f"Total runtime: {runtime:.1f} seconds")
        print(f"Tasks submitted: {self.stats['tasks_submitted']}")
        print(f"Tasks completed: {self.stats['tasks_completed']}")
        print(f"Tasks failed: {self.stats['tasks_failed']}")

        if self.stats['tasks_completed'] > 0:
            throughput = self.stats['tasks_completed'] / runtime
            print(f"Average throughput: {throughput:.2f} tasks/second")

    def run(self):
        """Main monitoring loop"""
        signal.signal(signal.SIGINT, self.signal_handler)

        print("Starting Claude Agent System Monitor...")
        print("Press Ctrl+C to exit\n")

        while self.running:
            try:
                self.display_dashboard()
                time.sleep(1)  # Refresh every second
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(2)

if __name__ == "__main__":
    monitor = ProcessingMonitor()
    monitor.run()