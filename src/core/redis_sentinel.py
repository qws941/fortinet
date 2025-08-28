#!/usr/bin/env python3
"""
Redis Sentinel/Cluster Configuration
High availability Redis setup with automatic failover
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import redis
import redis.sentinel

logger = logging.getLogger(__name__)


class RedisSentinelManager:
    """Manages Redis Sentinel connections with automatic failover"""

    def __init__(self, sentinels: List[tuple] = None, service_name: str = None):
        """
        Initialize Redis Sentinel manager

        Args:
            sentinels: List of (host, port) tuples for sentinels
            service_name: Name of the Redis service
        """
        self.sentinels = sentinels or self._get_sentinels_from_env()
        self.service_name = service_name or os.getenv("REDIS_SERVICE_NAME", "fortinet-master")
        self.sentinel = None
        self.master = None
        self.slaves = []
        self.connection_pool = None
        self._initialize_sentinel()

    def _get_sentinels_from_env(self) -> List[tuple]:
        """Get sentinel configuration from environment"""
        sentinel_hosts = os.getenv("REDIS_SENTINELS", "localhost:26379").split(",")
        sentinels = []

        for host_port in sentinel_hosts:
            try:
                host, port = host_port.strip().split(":")
                sentinels.append((host, int(port)))
            except ValueError:
                logger.warning(f"Invalid sentinel configuration: {host_port}")

        return sentinels or [("localhost", 26379)]

    def _initialize_sentinel(self):
        """Initialize Redis Sentinel connection"""
        try:
            self.sentinel = redis.sentinel.Sentinel(
                self.sentinels,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 2,  # TCP_KEEPINTVL
                    3: 3,  # TCP_KEEPCNT
                },
            )

            # Discover master and slaves
            self.master = self.sentinel.master_for(
                self.service_name,
                socket_timeout=0.5,
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_DB", "0")),
            )

            self.slaves = self.sentinel.slave_for(
                self.service_name,
                socket_timeout=0.5,
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_DB", "0")),
            )

            logger.info(f"Redis Sentinel initialized for service: {self.service_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis Sentinel: {e}")
            # Fall back to standard Redis
            self._fallback_to_standard_redis()

    def _fallback_to_standard_redis(self):
        """Fallback to standard Redis connection"""
        try:
            self.master = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            logger.info("Fallback to standard Redis connection")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.master = None

    def get_master(self) -> Optional[redis.Redis]:
        """Get Redis master connection"""
        if not self.master:
            self._initialize_sentinel()
        return self.master

    def get_slave(self) -> Optional[redis.Redis]:
        """Get Redis slave connection for read operations"""
        return self.slaves if self.slaves else self.master

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on Redis connections"""
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown",
            "master": None,
            "slaves": [],
            "sentinels": [],
        }

        try:
            # Check master
            if self.master:
                self.master.ping()
                info = self.master.info()
                health["master"] = {
                    "connected": True,
                    "role": info.get("role"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                }

            # Check sentinels
            if self.sentinel:
                slaves = self.sentinel.discover_slaves(self.service_name)

                health["sentinels"] = [{"host": host, "port": port, "status": "up"} for host, port in self.sentinels]

                health["slaves"] = [{"host": host, "port": port} for host, port in slaves]

            health["status"] = "healthy" if health["master"] else "unhealthy"

        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
            logger.error(f"Health check failed: {e}")

        return health

    def execute_with_retry(self, operation, *args, max_retries: int = 3, **kwargs):
        """
        Execute Redis operation with automatic retry and failover

        Args:
            operation: Redis operation to execute
            max_retries: Maximum number of retries

        Returns:
            Operation result
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                client = self.get_master()
                if not client:
                    raise redis.ConnectionError("No Redis connection available")

                # Execute operation
                result = getattr(client, operation)(*args, **kwargs)
                return result

            except redis.ConnectionError as e:
                last_error = e
                logger.warning(f"Redis connection error (attempt {attempt + 1}): {e}")

                # Try to reconnect
                self._initialize_sentinel()

            except Exception as e:
                last_error = e
                logger.error(f"Redis operation failed: {e}")
                break

        raise last_error or Exception("Redis operation failed after retries")


class RedisClusterManager:
    """Manages Redis Cluster connections"""

    def __init__(self, startup_nodes: List[Dict] = None):
        """
        Initialize Redis Cluster manager

        Args:
            startup_nodes: List of cluster node configurations
        """
        self.startup_nodes = startup_nodes or self._get_cluster_nodes_from_env()
        self.cluster = None
        self._initialize_cluster()

    def _get_cluster_nodes_from_env(self) -> List[Dict]:
        """Get cluster nodes from environment"""
        nodes_str = os.getenv(
            "REDIS_CLUSTER_NODES",
            "localhost:7000,localhost:7001,localhost:7002",
        )
        nodes = []

        for node in nodes_str.split(","):
            try:
                host, port = node.strip().split(":")
                nodes.append({"host": host, "port": int(port)})
            except ValueError:
                logger.warning(f"Invalid cluster node: {node}")

        return nodes or [{"host": "localhost", "port": 7000}]

    def _initialize_cluster(self):
        """Initialize Redis Cluster connection"""
        try:
            from rediscluster import RedisCluster

            self.cluster = RedisCluster(
                startup_nodes=self.startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                password=os.getenv("REDIS_PASSWORD"),
                max_connections=32,
                max_connections_per_node=16,
            )

            logger.info("Redis Cluster initialized successfully")

        except ImportError:
            logger.warning("redis-py-cluster not installed, falling back to standard Redis")
            self._fallback_to_standard_redis()

        except Exception as e:
            logger.error(f"Failed to initialize Redis Cluster: {e}")
            self._fallback_to_standard_redis()

    def _fallback_to_standard_redis(self):
        """Fallback to standard Redis connection"""
        self.cluster = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
        )

    def get_connection(self) -> Optional[Union[redis.Redis, Any]]:
        """Get Redis cluster connection"""
        if not self.cluster:
            self._initialize_cluster()
        return self.cluster

    def get_node_info(self) -> Dict[str, Any]:
        """Get cluster node information"""
        if not self.cluster:
            return {}

        try:
            # Get cluster info
            cluster_info = self.cluster.cluster_info()
            nodes = self.cluster.cluster_nodes()

            return {
                "cluster_state": cluster_info.get("cluster_state"),
                "cluster_slots_assigned": cluster_info.get("cluster_slots_assigned"),
                "cluster_slots_ok": cluster_info.get("cluster_slots_ok"),
                "cluster_known_nodes": cluster_info.get("cluster_known_nodes"),
                "nodes": nodes,
            }

        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {"error": str(e)}


class RedisHighAvailability:
    """Unified interface for Redis high availability"""

    def __init__(self, mode: str = None):
        """
        Initialize Redis HA manager

        Args:
            mode: HA mode ('sentinel', 'cluster', or 'standard')
        """
        self.mode = mode or os.getenv("REDIS_HA_MODE", "standard")
        self.sentinel_manager = None
        self.cluster_manager = None
        self.standard_client = None

        self._initialize_ha_mode()

    def _initialize_ha_mode(self):
        """Initialize appropriate HA mode"""
        if self.mode == "sentinel":
            self.sentinel_manager = RedisSentinelManager()
        elif self.mode == "cluster":
            self.cluster_manager = RedisClusterManager()
        else:
            # Standard Redis
            self.standard_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                connection_pool=redis.ConnectionPool(
                    max_connections=50,
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    password=os.getenv("REDIS_PASSWORD"),
                    db=int(os.getenv("REDIS_DB", "0")),
                ),
            )

    def get_client(self) -> Optional[redis.Redis]:
        """Get Redis client based on HA mode"""
        if self.mode == "sentinel" and self.sentinel_manager:
            return self.sentinel_manager.get_master()
        elif self.mode == "cluster" and self.cluster_manager:
            return self.cluster_manager.get_connection()
        else:
            return self.standard_client

    def get_read_client(self) -> Optional[redis.Redis]:
        """Get Redis client for read operations"""
        if self.mode == "sentinel" and self.sentinel_manager:
            return self.sentinel_manager.get_slave()
        else:
            return self.get_client()

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "mode": self.mode,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown",
        }

        try:
            client = self.get_client()
            if client:
                client.ping()
                health["status"] = "healthy"

                if self.mode == "sentinel":
                    health.update(self.sentinel_manager.health_check())
                elif self.mode == "cluster":
                    health["cluster_info"] = self.cluster_manager.get_node_info()
                else:
                    info = client.info()
                    health["redis_info"] = {
                        "version": info.get("redis_version"),
                        "uptime": info.get("uptime_in_seconds"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human"),
                    }

        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)

        return health

    def execute(self, command: str, *args, **kwargs):
        """Execute Redis command with HA support"""
        client = self.get_client()
        if not client:
            raise redis.ConnectionError("No Redis connection available")

        return getattr(client, command)(*args, **kwargs)


# Global HA instance
redis_ha = RedisHighAvailability()
