from typing import Any


class BaseTool:
    name: str = "BaseTool"
    description: str = ""

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError(
            "BaseTool._run must be implemented by subclasses"
        )
