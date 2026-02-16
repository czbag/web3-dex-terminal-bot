from enum import Enum

class ChainStatus(Enum):
    ACTIVE = ("active", "🟢")
    INACTIVE = ("inactive", "🔴")
    MAINTENANCE = ("maintenance", "🛠")

    @property
    def label(self):
        return self.value[0]

    @property
    def emoji(self):
        return self.value[1]
