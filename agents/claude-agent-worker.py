#!/usr/bin/env python3
"""
Claude Agent Worker
Individual agent implementation for distributed processing
"""

import asyncio
import aiohttp
import aioredis
import json
import os
import sys
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ClaudeAgentWorker:
    def __init__(self):
        # Agent configuration from environment
        self.agent_id = os.getenv("HOSTNAME", f"agent-{os.getpid()}")
        self.agent_type = os.getenv("AGENT_TYPE", "generic")
        self.capabilities = os.getenv("AGENT_CAPABILITIES", "").split(",")

        # Connection settings
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080")

        # Agent state
        self.status = "initializing"
        self.current_task = None
        self.tasks_completed = 0
        self.started_at = datetime.utcnow()

        # Performance metrics
        self.metrics = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "tasks_processed": 0,
            "errors": 0,
            "avg_task_time": 0
        }

        # Redis connection
        self.redis = None
        self.pubsub = None

        # Shutdown flag
        self.shutdown = False

    async def connect_redis(self):
        """Establish Redis connection for communication"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis.pubsub()

            # Subscribe to agent channel
            channel = f"agent:{self.agent_type}:{self.agent_id}"
            await self.pubsub.subscribe(channel, "broadcast")

            logger.info(f"Connected to Redis and subscribed to channels")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    async def register_with_orchestrator(self):
        """Register agent with the orchestrator"""
        try:
            registration = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "capabilities": self.capabilities,
                "status": "idle",
                "started_at": self.started_at.isoformat(),
                "host": os.getenv("HOSTNAME", "unknown"),
                "resources": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": psutil.virtual_memory().total
                }
            }

            # Send registration via Redis
            await self.redis.hset(
                "agents:registry",
                self.agent_id,
                json.dumps(registration)
            )

            # Set expiry for health check
            await self.redis.expire(f"agents:registry:{self.agent_id}", 60)

            logger.info(f"Agent {self.agent_id} registered with orchestrator")
            self.status = "idle"
            return True

        except Exception as e:
            logger.error(f"Failed to register with orchestrator: {e}")
            return False

    async def heartbeat(self):
        """Send periodic heartbeat to orchestrator"""
        while not self.shutdown:
            try:
                # Update metrics
                self.update_metrics()

                # Send heartbeat
                heartbeat_data = {
                    "agent_id": self.agent_id,
                    "status": self.status,
                    "timestamp": datetime.utcnow().isoformat(),
                    "current_task": self.current_task,
                    "metrics": self.metrics
                }

                await self.redis.setex(
                    f"agents:heartbeat:{self.agent_id}",
                    30,  # TTL 30 seconds
                    json.dumps(heartbeat_data)
                )

                await asyncio.sleep(10)  # Heartbeat every 10 seconds

            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                await asyncio.sleep(10)

    def update_metrics(self):
        """Update agent performance metrics"""
        try:
            # System metrics
            self.metrics["cpu_usage"] = psutil.cpu_percent(interval=1)
            self.metrics["memory_usage"] = psutil.virtual_memory().percent

            # Process metrics
            process = psutil.Process()
            self.metrics["process_cpu"] = process.cpu_percent(interval=0.1)
            self.metrics["process_memory"] = process.memory_info().rss / 1024 / 1024  # MB

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task based on agent type and capabilities"""
        start_time = time.time()

        try:
            self.status = "processing"
            self.current_task = task.get("id")

            logger.info(f"Processing task {task.get('id')} of type {task.get('type')}")

            # Route to appropriate handler based on agent type
            if self.agent_type == "analyzer":
                result = await self.analyze_task(task)
            elif self.agent_type == "executor":
                result = await self.execute_task(task)
            elif self.agent_type == "monitor":
                result = await self.monitor_task(task)
            elif self.agent_type == "researcher":
                result = await self.research_task(task)
            else:
                result = await self.generic_task(task)

            # Update metrics
            task_time = time.time() - start_time
            self.tasks_completed += 1
            self.metrics["tasks_processed"] += 1
            self.metrics["avg_task_time"] = (
                (self.metrics["avg_task_time"] * (self.tasks_completed - 1) + task_time)
                / self.tasks_completed
            )

            # Mark task complete
            self.status = "idle"
            self.current_task = None

            logger.info(f"Task {task.get('id')} completed in {task_time:.2f}s")

            return {
                "status": "success",
                "result": result,
                "agent_id": self.agent_id,
                "processing_time": task_time
            }

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            self.metrics["errors"] += 1
            self.status = "idle"
            self.current_task = None

            return {
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id
            }

    async def analyze_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzer agent task processing"""
        await asyncio.sleep(2)  # Simulate analysis

        return {
            "analysis_type": task.get("payload", {}).get("type", "code"),
            "findings": {
                "complexity": "medium",
                "issues": [],
                "suggestions": ["Add more comments", "Improve error handling"]
            },
            "metrics": {
                "lines_of_code": 500,
                "cyclomatic_complexity": 12,
                "test_coverage": 78
            }
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Executor agent task processing"""
        await asyncio.sleep(3)  # Simulate execution

        return {
            "execution_type": task.get("payload", {}).get("type", "script"),
            "status": "completed",
            "output": "Execution completed successfully",
            "artifacts": ["/tmp/output.log", "/tmp/results.json"]
        }

    async def monitor_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor agent task processing"""
        await asyncio.sleep(1)  # Simulate monitoring

        return {
            "monitoring_type": "system",
            "health": "healthy",
            "metrics": self.metrics,
            "alerts": []
        }

    async def research_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Researcher agent task processing"""
        await asyncio.sleep(4)  # Simulate research

        return {
            "research_topic": task.get("payload", {}).get("topic", "general"),
            "findings": [
                "Key insight 1",
                "Key insight 2",
                "Key insight 3"
            ],
            "sources": 5,
            "confidence": 0.85
        }

    async def generic_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generic task processing for unspecified agent types"""
        await asyncio.sleep(2)

        return {
            "task_type": task.get("type", "unknown"),
            "status": "processed",
            "message": f"Task processed by {self.agent_type} agent"
        }

    async def listen_for_tasks(self):
        """Listen for tasks from the orchestrator"""
        while not self.shutdown:
            try:
                # Check for messages
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                if message and message["type"] == "message":
                    data = json.loads(message["data"])

                    if data.get("type") == "task":
                        # Process the task
                        result = await self.process_task(data["task"])

                        # Send result back
                        await self.redis.lpush(
                            f"results:{data['task']['id']}",
                            json.dumps(result)
                        )

                    elif data.get("type") == "command":
                        await self.handle_command(data["command"])

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in task listener: {e}")
                await asyncio.sleep(1)

    async def handle_command(self, command: Dict[str, Any]):
        """Handle control commands from orchestrator"""
        cmd_type = command.get("type")

        if cmd_type == "shutdown":
            logger.info("Received shutdown command")
            self.shutdown = True

        elif cmd_type == "status":
            # Report current status
            status = {
                "agent_id": self.agent_id,
                "status": self.status,
                "current_task": self.current_task,
                "tasks_completed": self.tasks_completed
            }
            await self.redis.hset(
                "agents:status",
                self.agent_id,
                json.dumps(status)
            )

        elif cmd_type == "reload_config":
            logger.info("Reloading configuration")
            # Reload configuration logic here

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown = True

    async def cleanup(self):
        """Clean up resources before shutdown"""
        try:
            if self.redis:
                # Remove from registry
                await self.redis.hdel("agents:registry", self.agent_id)
                await self.redis.delete(f"agents:heartbeat:{self.agent_id}")

                # Close connections
                if self.pubsub:
                    await self.pubsub.unsubscribe()
                    await self.pubsub.close()
                await self.redis.close()

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    async def run(self):
        """Main agent loop"""
        logger.info(f"Claude Agent Worker {self.agent_id} starting...")

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        # Connect to Redis
        if not await self.connect_redis():
            logger.error("Failed to connect to Redis, exiting")
            return

        # Register with orchestrator
        if not await self.register_with_orchestrator():
            logger.error("Failed to register with orchestrator")
            return

        # Start background tasks
        heartbeat_task = asyncio.create_task(self.heartbeat())
        listener_task = asyncio.create_task(self.listen_for_tasks())

        # Main loop
        while not self.shutdown:
            try:
                # Check task queue
                task_data = await self.redis.rpop(f"tasks:{self.agent_type}")

                if task_data:
                    task = json.loads(task_data)
                    result = await self.process_task(task)

                    # Store result
                    await self.redis.lpush(
                        f"results:{task['id']}",
                        json.dumps(result)
                    )
                else:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)

        # Cancel background tasks
        heartbeat_task.cancel()
        listener_task.cancel()

        # Cleanup
        await self.cleanup()
        logger.info(f"Agent {self.agent_id} shutdown complete")

async def main():
    agent = ClaudeAgentWorker()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())