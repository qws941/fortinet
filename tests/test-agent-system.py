#!/usr/bin/env python3
"""
Test Claude Agent System with Real Tasks
"""

import redis
import json
import time
import uuid
import sys

def submit_task_to_redis(task_type, payload, priority=5):
    """Submit a task to Redis for agent processing"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    task = {
        "id": str(uuid.uuid4()),
        "type": task_type,
        "priority": priority,
        "payload": payload,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "pending"
    }

    # Push task to appropriate queue
    if task_type == "code_analysis":
        queue = "tasks:analyzer"
    elif task_type == "testing":
        queue = "tasks:executor"
    elif task_type == "monitoring":
        queue = "tasks:monitor"
    elif task_type == "research":
        queue = "tasks:researcher"
    else:
        queue = "tasks:general"

    r.lpush(queue, json.dumps(task))
    print(f"📤 Submitted task {task['id']} to queue {queue}")

    return task["id"]

def check_task_result(task_id, timeout=30):
    """Check for task completion"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    start_time = time.time()
    while time.time() - start_time < timeout:
        result = r.rpop(f"results:{task_id}")
        if result:
            return json.loads(result)
        time.sleep(1)

    return None

def test_code_analysis():
    """Test code analysis task"""
    print("\n🔍 Testing Code Analysis Task...")

    task_id = submit_task_to_redis(
        "code_analysis",
        {"file": "test.py", "type": "complexity_analysis"},
        priority=8
    )

    result = check_task_result(task_id)
    if result:
        print(f"✅ Analysis completed by {result.get('agent_id', 'unknown')}")
        print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
        return True
    else:
        print("❌ Analysis task timed out")
        return False

def test_execution():
    """Test execution task"""
    print("\n⚙️ Testing Execution Task...")

    task_id = submit_task_to_redis(
        "testing",
        {"suite": "unit_tests", "type": "pytest"},
        priority=5
    )

    result = check_task_result(task_id)
    if result:
        print(f"✅ Execution completed by {result.get('agent_id', 'unknown')}")
        print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
        return True
    else:
        print("❌ Execution task timed out")
        return False

def test_monitoring():
    """Test monitoring task"""
    print("\n📊 Testing Monitoring Task...")

    task_id = submit_task_to_redis(
        "monitoring",
        {"target": "system", "metrics": ["cpu", "memory", "disk"]},
        priority=3
    )

    result = check_task_result(task_id)
    if result:
        print(f"✅ Monitoring completed by {result.get('agent_id', 'unknown')}")
        print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
        return True
    else:
        print("❌ Monitoring task timed out")
        return False

def check_agent_status():
    """Check status of all registered agents"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    print("\n👥 Agent Status:")
    print("-" * 50)

    agents = r.hgetall("agents:registry")
    if agents:
        for agent_id, agent_data in agents.items():
            data = json.loads(agent_data)
            print(f"Agent: {agent_id}")
            print(f"  Type: {data.get('agent_type', 'unknown')}")
            print(f"  Status: {data.get('status', 'unknown')}")
            print(f"  Capabilities: {', '.join(data.get('capabilities', []))}")
            print()
    else:
        print("No agents registered")

    # Check heartbeats
    heartbeat_keys = r.keys("agents:heartbeat:*")
    active_count = 0
    for key in heartbeat_keys:
        ttl = r.ttl(key)
        if ttl > 0:
            active_count += 1

    print(f"Active agents (with heartbeat): {active_count}")

    return len(agents) > 0

def test_orchestrator_status():
    """Check orchestrator status via Redis"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    print("\n🎯 Orchestrator Status:")
    print("-" * 50)

    # Check if orchestrator has published any status
    status = r.get("orchestrator:status")
    if status:
        data = json.loads(status)
        print(f"Tasks processed: {data.get('tasks_processed', 0)}")
        print(f"Tasks failed: {data.get('tasks_failed', 0)}")
        print(f"Queue size: {data.get('queue_size', 0)}")
    else:
        print("Orchestrator status not available")

    return True

def main():
    print("=" * 60)
    print("Claude Agent System Integration Test")
    print("=" * 60)

    # First check agent status
    if not check_agent_status():
        print("\n⚠️ Warning: No agents registered yet. They may still be starting up.")
        print("Waiting 10 seconds for agents to register...")
        time.sleep(10)
        check_agent_status()

    # Check orchestrator
    test_orchestrator_status()

    # Run task tests
    results = []
    results.append(test_code_analysis())
    results.append(test_execution())
    results.append(test_monitoring())

    # Final summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("-" * 60)

    total_tests = len(results)
    passed_tests = sum(results)

    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    if all(results):
        print("\n✅ All agent system tests PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Agents may still be initializing.")
        sys.exit(1)

if __name__ == "__main__":
    main()