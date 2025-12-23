from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    All agents must follow this contract.
    """

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        pass
