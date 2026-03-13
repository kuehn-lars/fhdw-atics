from enum import Enum
from typing import List, Any, Optional


class Process(Enum):
    sequential = "sequential"
    parallel = "parallel"


class Agent:
    def __init__(
        self,
        role: str,
        goal: str = None,
        backstory: str = None,
        tools: List[Any] = None,
        verbose: bool = False,
        allow_delegation: bool = False,
        memory: bool = False,
        max_iter: int = 10,
        llm: Any = None,
        function_calling_llm: Any = None,
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.memory = memory
        self.max_iter = max_iter
        self.llm = llm

    def execute_task(self, task):
        if self.verbose:
            print(
                f"[Agent {self.role}] Executing task: {task.description[:80]}"
            )

        # gather context outputs if available
        if getattr(task, "context", None):
            ctx = [getattr(c, "output", None) for c in task.context]
        else:
            ctx = []

        # try running available tools (best-effort)
        tool_outputs = []
        for t in self.tools or []:
            try:
                if hasattr(t, "_run"):
                    out = t._run(task.description)
                    tool_outputs.append(out)
            except Exception as e:
                tool_outputs.append(f"tool_error: {e}")

        if tool_outputs:
            result = "\n".join(tool_outputs)
        else:
            result = f"Executed task: {task.description}"

        task.output = result
        return result


class Task:
    def __init__(
        self,
        description: str,
        expected_output: str = None,
        agent: Agent = None,
        tools: List[Any] = None,
        context: List[Any] = None,
        output_file: Optional[str] = None,
        output_json: Any = None,
        output_pydantic: Any = None,
        callback: Any = None,
        human_input: bool = False,
    ):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.tools = tools or []
        self.context = context or []
        self.output_file = output_file
        self.output_json = output_json
        self.output_pydantic = output_pydantic
        self.callback = callback
        self.human_input = human_input
        self.output = None


class Crew:
    def __init__(
        self,
        agents: List[Agent],
        tasks: List[Task],
        process: Process = Process.sequential,
        verbose: bool = False,
    ):
        self.agents = agents
        self.tasks = tasks
        self.process = process
        self.verbose = verbose

    def kickoff(self):
        if self.verbose:
            print("[Crew] kickoff starting")
        results = []
        if self.process == Process.sequential:
            for task in self.tasks:
                agent = task.agent or (self.agents[0] if self.agents else None)
                if agent:
                    res = agent.execute_task(task)
                else:
                    res = f"No agent for task: {task.description}"
                results.append(res)
        else:
            # fallback: run sequentially but keep behavior simple
            for task in self.tasks:
                agent = task.agent or (self.agents[0] if self.agents else None)
                res = (
                    agent.execute_task(task) if agent else f"No agent for task"
                )
                results.append(res)
        return results


__all__ = ["Agent", "Task", "Crew", "Process"]
