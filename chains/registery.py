from chains.dto import ChainConfig


class ChainRegistry:
    def __init__(self, chains: list[ChainConfig]):
        self._chains: dict[int, ChainConfig] = {}
        for cfg in chains:
            self._chains[cfg.chain_id] = cfg

    def get(self, chain_id: int) -> ChainConfig | None:
        return self._chains.get(chain_id)

    def list(self) -> list[ChainConfig]:
        return list(self._chains.values())
