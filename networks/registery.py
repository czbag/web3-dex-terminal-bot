from models.dtos import NetworkConfig


class NetworkRegistry:
    def __init__(self, networks: list[NetworkConfig]):
        self._networks: dict[int, NetworkConfig] = {}
        for cfg in networks:
            self._networks[cfg.chain_id] = cfg

    def get(self, chain_id: int) -> NetworkConfig | None:
        return self._networks.get(chain_id)

    def list(self) -> list[NetworkConfig]:
        return list(self._networks.values())
