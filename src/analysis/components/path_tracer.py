"""
경로 추적 컴포넌트

네트워크 트래픽의 경로를 추적하고 라우팅 정보를 분석하는 책임을 담당합니다.
"""

import ipaddress

from utils.unified_logger import setup_logger

logger = setup_logger("path_tracer")


class PathTracer:
    """네트워크 경로 추적을 담당하는 클래스"""

    def __init__(self, data_loader):
        """
        경로 추적기 초기화

        Args:
            data_loader: DataLoader 인스턴스
        """
        self.data_loader = data_loader
        self.logger = logger

    def trace_packet_path(self, src_ip, dst_ip, firewall_id="default"):
        """
        패킷 경로 추적

        Args:
            src_ip (str): 소스 IP 주소
            dst_ip (str): 목적지 IP 주소
            firewall_id (str): 방화벽 식별자

        Returns:
            dict: 경로 추적 결과
        """
        try:
            # 라우팅 테이블 가져오기
            routing_table = self.data_loader.get_routing_tables(firewall_id)
            if not routing_table:
                return {
                    "success": False,
                    "error": "라우팅 테이블 데이터가 없습니다.",
                    "path": [],
                }

            # 소스 IP의 인터페이스 결정
            src_interface = self._determine_interface(src_ip, routing_table)

            # 목적지 IP의 라우트 결정
            dst_route = self._find_best_route(dst_ip, routing_table)

            # 경로 정보 구성
            path_info = {
                "success": True,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_interface": src_interface,
                "dst_route": dst_route,
                "path": self._build_path_details(src_interface, dst_route),
                "next_hop": dst_route.get("gateway") if dst_route else None,
            }

            self.logger.info(f"패킷 경로 추적 완료: {src_ip} -> {dst_ip}")
            return path_info

        except Exception as e:
            self.logger.error(f"패킷 경로 추적 중 오류: {str(e)}")
            return {"success": False, "error": str(e), "path": []}

    def _determine_interface(self, ip, routing_table):
        """IP 주소가 속한 인터페이스 결정"""
        try:
            target_ip = ipaddress.ip_address(ip)

            for route in routing_table:
                destination = route.get("destination", "127.0.0.0/24")
                interface = route.get("interface", "unknown")

                # 직접 연결된 네트워크인지 확인
                if route.get("type") == "connected":
                    try:
                        network = ipaddress.ip_network(destination, strict=False)
                        if target_ip in network:
                            return {
                                "name": interface,
                                "network": destination,
                                "type": "connected",
                            }
                    except ValueError:
                        continue

            # 기본 인터페이스 반환
            return {"name": "unknown", "network": "unknown", "type": "unknown"}

        except Exception as e:
            self.logger.error(f"인터페이스 결정 중 오류: {str(e)}")
            return {"name": "error", "network": "error", "type": "error"}

    def _find_best_route(self, dst_ip, routing_table):
        """목적지 IP에 대한 최적 라우트 찾기"""
        try:
            target_ip = ipaddress.ip_address(dst_ip)
            best_route = None
            longest_prefix = -1

            for route in routing_table:
                destination = route.get("destination", "127.0.0.0/24")

                try:
                    # CIDR 형식이 아닌 경우 처리
                    if "/" not in destination:
                        if destination == "0.0.0.0":
                            destination = "127.0.0.0/24"
                        else:
                            destination = f"{destination}/32"

                    network = ipaddress.ip_network(destination, strict=False)

                    # 타겟 IP가 이 네트워크에 포함되는지 확인
                    if target_ip in network:
                        prefix_length = network.prefixlen

                        # 가장 긴 prefix 매치 찾기
                        if prefix_length > longest_prefix:
                            longest_prefix = prefix_length
                            best_route = route

                except ValueError as e:
                    self.logger.warning(f"라우트 파싱 오류: {destination}, {str(e)}")
                    continue

            return best_route

        except Exception as e:
            self.logger.error(f"최적 라우트 찾기 중 오류: {str(e)}")
            return None

    def _build_path_details(self, src_interface, dst_route):
        """경로 세부 정보 구성"""
        path_details = []

        # 소스 인터페이스 정보 추가
        if src_interface:
            path_details.append(
                {
                    "step": 1,
                    "type": "ingress",
                    "interface": src_interface.get("name", "unknown"),
                    "network": src_interface.get("network", "unknown"),
                    "description": f"패킷이 {src_interface.get('name', 'unknown')} 인터페이스로 유입",
                }
            )

        # 라우팅 정보 추가
        if dst_route:
            step = 2 if src_interface else 1

            route_type = dst_route.get("type", "unknown")
            gateway = dst_route.get("gateway")
            interface = dst_route.get("interface", "unknown")
            destination = dst_route.get("destination", "unknown")

            if route_type == "connected":
                description = f"목적지가 직접 연결된 네트워크 {destination}에 있음"
            elif gateway:
                description = f"게이트웨이 {gateway}를 통해 {interface} 인터페이스로 라우팅"
            else:
                description = f"{interface} 인터페이스로 직접 라우팅"

            path_details.append(
                {
                    "step": step,
                    "type": "routing",
                    "interface": interface,
                    "gateway": gateway,
                    "destination": destination,
                    "route_type": route_type,
                    "description": description,
                }
            )

            # egress 정보 추가
            path_details.append(
                {
                    "step": step + 1,
                    "type": "egress",
                    "interface": interface,
                    "description": f"패킷이 {interface} 인터페이스로 송출",
                }
            )

        return path_details

    def analyze_routing_loops(self, firewall_id="default"):
        """
        라우팅 루프 분석

        Args:
            firewall_id (str): 방화벽 식별자

        Returns:
            list: 발견된 라우팅 루프 목록
        """
        routing_table = self.data_loader.get_routing_tables(firewall_id)
        if not routing_table:
            return []

        loops = []

        # 간단한 루프 검출 - 같은 destination에 대한 순환 참조
        for i, route1 in enumerate(routing_table):
            for j, route2 in enumerate(routing_table[i + 1 :], i + 1):
                if self._is_potential_loop(route1, route2):
                    loops.append(
                        {
                            "route1": route1,
                            "route2": route2,
                            "type": "potential_loop",
                            "description": f"라우트 {i + 1}과 {j + 1} 사이의 잠재적 루프",
                        }
                    )

        return loops

    def _is_potential_loop(self, route1, route2):
        """
        두 라우트 간의 잠재적 루프 확인

        Args:
            route1 (dict): 첫 번째 라우트
            route2 (dict): 두 번째 라우트

        Returns:
            bool: 루프 가능성 여부
        """
        # 간단한 루프 검출 로직
        # 실제로는 더 복잡한 그래프 알고리즘이 필요

        dest1 = route1.get("destination")
        dest2 = route2.get("destination")
        gateway1 = route1.get("gateway")
        gateway2 = route2.get("gateway")

        # 같은 destination에 대한 다른 gateway
        if dest1 == dest2 and gateway1 != gateway2:
            return True

        # 서로를 gateway로 참조하는 경우
        if gateway1 and gateway2:
            try:
                if ipaddress.ip_address(gateway1) in ipaddress.ip_network(dest2, strict=False) and ipaddress.ip_address(
                    gateway2
                ) in ipaddress.ip_network(dest1, strict=False):
                    return True
            except ValueError:
                pass

        return False

    def get_interface_statistics(self, firewall_id="default"):
        """
        인터페이스 통계 정보 반환

        Args:
            firewall_id (str): 방화벽 식별자

        Returns:
            dict: 인터페이스별 통계
        """
        routing_table = self.data_loader.get_routing_tables(firewall_id)
        if not routing_table:
            return {}

        interface_stats = {}

        for route in routing_table:
            interface = route.get("interface", "unknown")
            route_type = route.get("type", "unknown")

            if interface not in interface_stats:
                interface_stats[interface] = {
                    "total_routes": 0,
                    "connected_routes": 0,
                    "static_routes": 0,
                    "dynamic_routes": 0,
                }

            interface_stats[interface]["total_routes"] += 1

            if route_type == "connected":
                interface_stats[interface]["connected_routes"] += 1
            elif route_type == "static":
                interface_stats[interface]["static_routes"] += 1
            else:
                interface_stats[interface]["dynamic_routes"] += 1

        return interface_stats
