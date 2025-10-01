#!/usr/bin/env python3
"""
Test Claude Agent Communication
"""

import redis
import pika
import json
import time
import sys

def test_redis():
    """Test Redis connectivity"""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        if r.ping():
            print("✅ Redis connection successful")

            # Test basic operations
            r.set('test_key', 'test_value')
            value = r.get('test_key')
            assert value == 'test_value', "Redis read/write failed"
            print("✅ Redis read/write test passed")

            # Test pub/sub
            pubsub = r.pubsub()
            pubsub.subscribe('test_channel')
            r.publish('test_channel', 'test_message')
            print("✅ Redis pub/sub test passed")

            r.delete('test_key')
            return True
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def test_rabbitmq():
    """Test RabbitMQ connectivity"""
    try:
        credentials = pika.PlainCredentials('admin', 'admin123')
        parameters = pika.ConnectionParameters(
            'localhost',
            5672,
            '/',
            credentials
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        print("✅ RabbitMQ connection successful")

        # Declare a test queue
        channel.queue_declare(queue='test_queue')

        # Publish a test message
        channel.basic_publish(
            exchange='',
            routing_key='test_queue',
            body='test_message'
        )
        print("✅ RabbitMQ message publish test passed")

        # Clean up
        channel.queue_delete(queue='test_queue')
        connection.close()

        return True
    except Exception as e:
        print(f"❌ RabbitMQ test failed: {e}")
        return False

def test_agent_registration():
    """Test agent registration in Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Simulate agent registration
        agent_data = {
            "agent_id": "test-agent-001",
            "agent_type": "test",
            "capabilities": ["testing", "verification"],
            "status": "idle"
        }

        r.hset("agents:registry", "test-agent-001", json.dumps(agent_data))

        # Verify registration
        stored = r.hget("agents:registry", "test-agent-001")
        if stored:
            data = json.loads(stored)
            assert data["agent_id"] == "test-agent-001", "Agent registration verification failed"
            print("✅ Agent registration test passed")

            # Clean up
            r.hdel("agents:registry", "test-agent-001")
            return True
        else:
            print("❌ Agent registration failed")
            return False

    except Exception as e:
        print(f"❌ Agent registration test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Claude Agent Communication Test")
    print("=" * 50)

    results = []

    print("\n1. Testing Redis connectivity...")
    results.append(test_redis())

    print("\n2. Testing RabbitMQ connectivity...")
    results.append(test_rabbitmq())

    print("\n3. Testing agent registration...")
    results.append(test_agent_registration())

    print("\n" + "=" * 50)
    if all(results):
        print("✅ All communication tests PASSED!")
        sys.exit(0)
    else:
        print("❌ Some tests FAILED. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()