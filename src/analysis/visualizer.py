from utils.unified_logger import setup_logger

logger = setup_logger("visualizer")


class PathVisualizer:
    """
    방화벽 경로 시각화 클래스

    트래픽 경로 시각화를 위한 데이터를 생성합니다.
    """

    def __init__(self):
        """
        경로 시각화 객체 초기화
        """
        self.logger = logger

    def generate_network_graph(self, path_data):
        """
        네트워크 그래프 데이터 생성

        Args:
            path_data (dict): 분석기에서 생성한 경로 데이터

        Returns:
            dict: D3.js 또는 Cytoscape.js에서 사용할 수 있는 네트워크 그래프 데이터
        """
        try:
            if not path_data or "path" not in path_data:
                self.logger.error("유효하지 않은 경로 데이터")
                return None

            # 그래프 데이터 구조 초기화
            graph_data = {
                "nodes": [],
                "edges": [],
                "allowed": path_data.get("allowed", False),
            }

            # 소스 노드와 목적지 노드 정보 추출
            if len(path_data["path"]) > 0:
                src_ip = path_data["path"][0]["src_ip"]
                dst_ip = path_data.get("final_destination", path_data["path"][-1]["dst_ip"])

                # 소스 노드 추가
                graph_data["nodes"].append(
                    {
                        "id": f"src_{src_ip}",
                        "label": f"Source\n{src_ip}",
                        "type": "host",
                        "ip": src_ip,
                    }
                )

                # 목적지 노드 추가
                graph_data["nodes"].append(
                    {
                        "id": f"dst_{dst_ip}",
                        "label": f"Destination\n{dst_ip}",
                        "type": "host",
                        "ip": dst_ip,
                    }
                )
            else:
                self.logger.warning("경로 데이터가 비어 있습니다.")
                return graph_data

            # 방화벽 노드 및 엣지 추가
            prev_node_id = f"src_{src_ip}"

            for i, hop in enumerate(path_data["path"]):
                firewall_id = hop["firewall_id"]
                firewall_name = hop.get("firewall_name", firewall_id)
                policy_id = hop.get("policy_id", "Unknown")
                action = hop.get("action", "Unknown")

                # 방화벽 노드 추가
                fw_node_id = f"fw_{firewall_id}"

                # 이미 추가된 노드인지 확인
                node_exists = False
                for node in graph_data["nodes"]:
                    if node["id"] == fw_node_id:
                        node_exists = True
                        break

                if not node_exists:
                    graph_data["nodes"].append(
                        {
                            "id": fw_node_id,
                            "label": f"Firewall\n{firewall_name}",
                            "type": "firewall",
                            "firewall_id": firewall_id,
                        }
                    )

                # 노드간 엣지 추가
                graph_data["edges"].append(
                    {
                        "id": f"edge_{i}",
                        "source": prev_node_id,
                        "target": fw_node_id,
                        "policy_id": policy_id,
                        "action": action,
                        "allowed": action != "deny",
                    }
                )

                prev_node_id = fw_node_id

                # 마지막 홉이면 목적지 노드와 연결
                if i == len(path_data["path"]) - 1:
                    # 블록된 경우, 목적지 연결 엣지 표시 변경
                    is_blocked = not path_data.get("allowed", True)

                    graph_data["edges"].append(
                        {
                            "id": "edge_final",
                            "source": fw_node_id,
                            "target": f"dst_{dst_ip}",
                            "policy_id": None,
                            "action": "blocked" if is_blocked else "allowed",
                            "allowed": not is_blocked,
                            "is_final": True,
                        }
                    )

            return graph_data

        except Exception as e:
            self.logger.error(f"네트워크 그래프 생성 중 오류: {str(e)}")
            return None

    def generate_path_table(self, path_data):
        """
        경로 테이블 데이터 생성

        Args:
            path_data (dict): 분석기에서 생성한 경로 데이터

        Returns:
            list: 테이블 형식의 경로 데이터
        """
        try:
            if not path_data or "path" not in path_data:
                self.logger.error("유효하지 않은 경로 데이터")
                return []

            table_data = []

            for i, hop in enumerate(path_data["path"]):
                firewall_id = hop["firewall_id"]
                firewall_name = hop.get("firewall_name", firewall_id)
                src_ip = hop["src_ip"]
                dst_ip = hop["dst_ip"]
                policy = hop.get("policy", {})
                policy_id = hop.get("policy_id", "N/A")
                action = hop.get("action", "N/A")

                policy_name = policy.get("name", "N/A") if policy else "N/A"

                table_entry = {
                    "hop": i + 1,
                    "firewall_name": firewall_name,
                    "firewall_id": firewall_id,
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "policy_id": policy_id,
                    "policy_name": policy_name,
                    "action": action,
                    "status": "Allowed" if action != "deny" else "Blocked",
                }

                table_data.append(table_entry)

            return table_data

        except Exception as e:
            self.logger.error(f"경로 테이블 생성 중 오류: {str(e)}")
            return []

    def generate_detailed_rules(self, path_data):
        """
        상세 룰 정보 생성

        Args:
            path_data (dict): 분석기에서 생성한 경로 데이터

        Returns:
            list: 룰 상세 정보 목록
        """
        try:
            if not path_data or "path" not in path_data:
                self.logger.error("유효하지 않은 경로 데이터")
                return []

            rules_details = []

            for i, hop in enumerate(path_data["path"]):
                policy = hop.get("policy", {})
                if not policy:
                    continue

                firewall_name = hop.get("firewall_name", hop["firewall_id"])
                policy_id = hop.get("policy_id", "N/A")

                # 기본 정책 정보 추출
                rule_detail = {
                    "hop": i + 1,
                    "firewall_name": firewall_name,
                    "policy_id": policy_id,
                    "policy_name": policy.get("name", "N/A"),
                    "action": policy.get("action", "N/A"),
                    "status": policy.get("status", "N/A"),
                    "src_intf": self._extract_interfaces(policy.get("srcintf", [])),
                    "dst_intf": self._extract_interfaces(policy.get("dstintf", [])),
                    "src_addr": self._extract_addresses(policy.get("srcaddr", [])),
                    "dst_addr": self._extract_addresses(policy.get("dstaddr", [])),
                    "services": self._extract_services(policy.get("service", [])),
                    "schedule": policy.get("schedule", "always"),
                    "nat": policy.get("nat", "disable"),
                    "ips_sensor": policy.get("ips-sensor", "N/A"),
                    "comments": policy.get("comments", ""),
                }

                rules_details.append(rule_detail)

            return rules_details

        except Exception as e:
            self.logger.error(f"상세 룰 정보 생성 중 오류: {str(e)}")
            return []

    def _extract_interfaces(self, interfaces):
        """인터페이스 목록에서 이름 추출"""
        if not interfaces:
            return []

        return [intf.get("name", "unknown") for intf in interfaces]

    def _extract_addresses(self, addresses):
        """주소 목록에서 이름 추출"""
        if not addresses:
            return []

        return [addr.get("name", "unknown") for addr in addresses]

    def _extract_services(self, services):
        """서비스 목록에서 이름 추출"""
        if not services:
            return []

        return [svc.get("name", "unknown") for svc in services]

    def generate_visualization_data(self, path_data):
        """
        전체 시각화 데이터 생성

        Args:
            path_data (dict): 분석기에서 생성한 경로 데이터

        Returns:
            dict: 모든 시각화 관련 데이터
        """
        try:
            visualization_data = {
                "graph": self.generate_network_graph(path_data),
                "path_table": self.generate_path_table(path_data),
                "detailed_rules": self.generate_detailed_rules(path_data),
                "allowed": path_data.get("allowed", False),
                "blocked_by": path_data.get("blocked_by"),
                "summary": {
                    "total_hops": len(path_data.get("path", [])),
                    "source_ip": (path_data["path"][0]["src_ip"] if path_data.get("path") else None),
                    "destination_ip": path_data.get(
                        "final_destination",
                        (path_data["path"][-1]["dst_ip"] if path_data.get("path") else None),
                    ),
                },
            }

            return visualization_data

        except Exception as e:
            self.logger.error(f"시각화 데이터 생성 중 오류: {str(e)}")
            return {
                "error": str(e),
                "allowed": False,
                "graph": None,
                "path_table": [],
                "detailed_rules": [],
            }

    def visualize_path(self, path_data):
        """
        경로 시각화 - generate_visualization_data의 별칭

        Args:
            path_data (dict): 분석기에서 생성한 경로 데이터

        Returns:
            dict: 모든 시각화 관련 데이터
        """
        return self.generate_visualization_data(path_data)


def create_topology_visualization(network_data):
    """
    Create network topology visualization data

    Args:
        network_data (dict): Network topology data

    Returns:
        dict: Visualization data for topology
    """
    try:
        visualizer = PathVisualizer()

        # If network_data follows the path format, use it directly
        if "path" in network_data:
            return visualizer.generate_visualization_data(network_data)

        # Otherwise, create a simple topology visualization
        topology_data = {
            "graph": {"nodes": [], "edges": [], "allowed": True},
            "summary": {"total_nodes": 0, "total_connections": 0},
        }

        # Process nodes if available
        nodes = network_data.get("nodes", [])
        for i, node in enumerate(nodes):
            topology_data["graph"]["nodes"].append(
                {
                    "id": f"node_{i}",
                    "label": node.get("name", f"Node {i}"),
                    "type": node.get("type", "unknown"),
                    "ip": node.get("ip", "unknown"),
                }
            )

        # Process connections if available
        connections = network_data.get("connections", [])
        for i, conn in enumerate(connections):
            topology_data["graph"]["edges"].append(
                {
                    "id": f"edge_{i}",
                    "source": conn.get("source", "node_0"),
                    "target": conn.get("target", "node_1"),
                    "type": conn.get("type", "connection"),
                    "allowed": True,
                }
            )

        topology_data["summary"]["total_nodes"] = len(nodes)
        topology_data["summary"]["total_connections"] = len(connections)

        return topology_data

    except Exception as e:
        logger.error(f"Topology visualization creation failed: {str(e)}")
        return {
            "error": str(e),
            "graph": {"nodes": [], "edges": [], "allowed": False},
            "summary": {"total_nodes": 0, "total_connections": 0},
        }
