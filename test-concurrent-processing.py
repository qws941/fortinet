#!/usr/bin/env python3
"""
Test concurrent processing capabilities of Claude Agent System
"""

import redis
import json
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

def submit_task(task_type, priority=5):
    """Submit a single task to Redis"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    task = {
        "id": str(uuid.uuid4()),
        "type": task_type,
        "priority": priority,
        "payload": {
            "test": "concurrent",
            "timestamp": time.time()
        },
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "pending"
    }

    # Map task type to queue
    queue_map = {
        "code_analysis": "tasks:analyzer",
        "testing": "tasks:executor",
        "monitoring": "tasks:monitor",
        "research": "tasks:researcher"
    }

    queue = queue_map.get(task_type, "tasks:general")
    r.lpush(queue, json.dumps(task))

    return task["id"]

def wait_for_result(task_id, timeout=10):
    """Wait for task result"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    start = time.time()
    while time.time() - start < timeout:
        result = r.rpop(f"results:{task_id}")
        if result:
            return json.loads(result), time.time() - start
        time.sleep(0.1)

    return None, timeout

def test_concurrent_batch(task_type, count):
    """Test concurrent processing for a specific task type"""
    print(f"\n📊 Testing {count} concurrent {task_type} tasks...")

    start_time = time.time()
    task_ids = []

    # Submit all tasks
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(submit_task, task_type) for _ in range(count)]
        task_ids = [future.result() for future in as_completed(futures)]

    submission_time = time.time() - start_time
    print(f"  ⚡ Submitted {count} tasks in {submission_time:.2f}s")

    # Wait for all results
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(wait_for_result, task_id): task_id
                  for task_id in task_ids}

        for future in as_completed(futures):
            result, duration = future.result()
            if result:
                results.append({
                    'task_id': futures[future],
                    'result': result,
                    'wait_time': duration
                })

    total_time = time.time() - start_time

    # Analyze results
    if results:
        wait_times = [r['wait_time'] for r in results]
        processing_times = [r['result'].get('processing_time', 0) for r in results]

        print(f"  ✅ Completed: {len(results)}/{count} tasks")
        print(f"  ⏱️  Total time: {total_time:.2f}s")
        print(f"  📈 Throughput: {len(results)/total_time:.2f} tasks/sec")
        print(f"  ⏳ Avg wait time: {statistics.mean(wait_times):.2f}s")
        print(f"  🔄 Avg processing: {statistics.mean(processing_times):.2f}s")

        # Check which agents processed tasks
        agents = {}
        for r in results:
            agent_id = r['result'].get('agent_id', 'unknown')
            agents[agent_id] = agents.get(agent_id, 0) + 1

        print(f"  👥 Agent distribution:")
        for agent, count in sorted(agents.items()):
            print(f"     - {agent[:12]}: {count} tasks")
    else:
        print(f"  ❌ No tasks completed within timeout")

    return results

def check_agent_metrics():
    """Check agent utilization metrics"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    print("\n🔍 Agent Metrics:")
    print("-" * 50)

    # Get all registered agents
    agents = r.hgetall("agents:registry")

    for agent_id, agent_data in agents.items():
        data = json.loads(agent_data)

        # Get heartbeat data
        heartbeat = r.get(f"agents:heartbeat:{agent_id}")
        if heartbeat:
            hb_data = json.loads(heartbeat)
            metrics = hb_data.get('metrics', {})

            print(f"\n Agent: {agent_id[:12]} ({data.get('agent_type')})")
            print(f"  Status: {hb_data.get('status', 'unknown')}")
            print(f"  CPU: {metrics.get('cpu_usage', 0):.1f}%")
            print(f"  Memory: {metrics.get('memory_usage', 0):.1f}%")
            print(f"  Tasks: {metrics.get('tasks_processed', 0)}")
            print(f"  Avg Time: {metrics.get('avg_task_time', 0):.2f}s")

def main():
    print("=" * 60)
    print("Claude Agent System - Concurrent Processing Test")
    print("=" * 60)

    # Test different task types with varying loads
    test_scenarios = [
        ("code_analysis", 10),
        ("testing", 15),
        ("monitoring", 5),
        ("code_analysis", 20),  # Heavy load on analyzers
        ("testing", 30),        # Heavy load on executors
    ]

    all_results = []

    for task_type, count in test_scenarios:
        results = test_concurrent_batch(task_type, count)
        all_results.extend(results)
        time.sleep(2)  # Brief pause between batches

    # Final metrics
    check_agent_metrics()

    print("\n" + "=" * 60)
    print("Summary:")
    print("-" * 60)

    total_submitted = sum(count for _, count in test_scenarios)
    total_completed = len(all_results)

    print(f"Total tasks submitted: {total_submitted}")
    print(f"Total tasks completed: {total_completed}")
    print(f"Success rate: {total_completed/total_submitted*100:.1f}%")

    if all_results:
        all_wait_times = [r['wait_time'] for r in all_results]
        print(f"Overall avg wait time: {statistics.mean(all_wait_times):.2f}s")
        print(f"Min wait time: {min(all_wait_times):.2f}s")
        print(f"Max wait time: {max(all_wait_times):.2f}s")

if __name__ == "__main__":
    main()