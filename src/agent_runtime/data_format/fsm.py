"""
Agent Runtime FSM (有限状态机) 模块

这个模块包含了Agent Runtime的有限状态机相关的核心类和功能，
包括状态定义、状态机管理和状态转换逻辑。
"""

from typing import Optional, Dict, List, TYPE_CHECKING
from pydantic import BaseModel
from datetime import datetime
from dateutil import parser
import yaml

from agent_runtime.data_format.action import V2Action
from agent_runtime.data_format.feedback import Feedback

if TYPE_CHECKING:
    from agent_runtime.interface.api_models import Setting


class Memory(BaseModel):
    """记忆类 - 存储对话历史"""
    history: List["Step"] = []

    def print_history(self) -> str:
        def relative_time_string(iso_str: Optional[str]) -> str:
            if iso_str is None:
                return ""

            now = datetime.now().astimezone()
            past_time = parser.isoparse(iso_str).astimezone()
            delta = now - past_time

            abs_time = past_time.strftime("%Y-%m-%d %H:%M:%S %z")

            if delta.total_seconds() < 60:
                rel = f"{int(delta.total_seconds())} seconds ago"
            elif delta.total_seconds() < 120:
                rel = "a minute ago"
            elif delta.total_seconds() < 3600:
                rel = f"{int(delta.total_seconds() // 60)} minutes ago"
            elif delta.total_seconds() < 7200:
                rel = "an hour ago"
            elif delta.total_seconds() < 86400:
                rel = f"{int(delta.total_seconds() // 3600)} hours ago"
            elif delta.days == 1:
                rel = "yesterday"
            else:
                rel = f"{delta.days} days ago"

            return f"{abs_time} ({rel})"

        return yaml.dump(
            {
                f"Step.{step_idx}": {
                    **{
                        f"Action.{action_idx}": {
                            "name": action.name,
                            "arguments": action.arguments,
                            "result": action.result,
                        }
                        for action_idx, action in enumerate(step.actions)
                    },
                    "timestamp": relative_time_string(step.timestamp)
                }
                for step_idx, step in enumerate(self.history)
            },
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )


class State(BaseModel):
    """状态定义

    Attributes:
        name (str): 状态名称
        scenario (str): 状态场景描述
        instruction (str): 状态指令
    """

    name: str
    scenario: str
    instruction: str


class Step(BaseModel):
    state_name: Optional[str] = None
    actions: List[V2Action] = []
    state_feedbacks: List[Feedback] = []
    action_feedbacks: List[Feedback] = []
    timestamp: Optional[str] = None


class StateMachine(BaseModel):
    """有限状态机

    管理状态和状态转换关系的核心类

    Attributes:
        initial_state_name (str): 初始状态名称
        states (List[State]): 状态列表
        out_transitions (Dict[str, List[str]]): 状态转换关系 {from_state: [to_state1, to_state2, ...]}
    """

    initial_state_name: str = ""
    states: List[State] = []
    # {from_state: [to_state1, to_state2, ...]}
    out_transitions: Dict[str, List[str]] = {}

    _states_dict: Dict[str, State] = {}
    # {to_state: [from_state1, from_state2, ...]}
    _in_transitions: Dict[str, List[str]] = {}

    def __init__(self, **data):
        super().__init__(**data)

        # Initialize _states_dict
        for state in self.states:
            self._states_dict[state.name] = state

        # Check initial_state_name is valid
        if not self.initial_state_name and not self._states_dict:
            pass
        elif (
            self.initial_state_name
            and self._states_dict
            and self.initial_state_name in self._states_dict
        ):
            pass
        else:
            raise ValueError(
                f'Invalid initial_state "{self.initial_state_name}" '
                f'which is not in states "{self._states_dict.keys()}"'
            )

        # Check out_transitions is valid
        for from_state, transitions in self.out_transitions.items():
            if from_state not in self._states_dict:
                raise ValueError(
                    f'Invalid from_state "{from_state}" which is not in states'
                )
            for to_state in transitions:
                if to_state not in self._states_dict:
                    raise ValueError(
                        f'Invalid to_state "{to_state}" which is not in states'
                    )

        # Initialize _in_transitions
        for from_state, to_states in self.out_transitions.items():
            for to_state in to_states:
                if to_state not in self._in_transitions:
                    self._in_transitions[to_state] = []
                self._in_transitions[to_state].append(from_state)

    def get_state(self, state_name: str) -> Optional[State]:
        """获取指定名称的状态

        Args:
            state_name (str): 状态名称

        Returns:
            Optional[State]: 状态对象

        Raises:
            ValueError: 当状态名称不存在时
        """
        if state_name not in self._states_dict:
            raise ValueError(
                f'Invalid state_name "{state_name}" which is not in states'
            )
        return self._states_dict[state_name]

    def get_next_states(self, from_state_name: Optional[str] = None) -> List[State]:
        """获取下一个可能的状态列表

        Args:
            from_state_name (Optional[str]): 起始状态名称，如果为None则使用初始状态

        Returns:
            List[State]: 下一个可能的状态列表

        Raises:
            ValueError: 当起始状态名称不存在时
        """
        if not self._states_dict:
            return []

        if not from_state_name:
            from_state_name = self.initial_state_name

        if from_state_name not in self._states_dict:
            raise ValueError(
                f'Invalid from_state_name "{from_state_name}" which is not in states'
            )

        free_states = self._get_free_states()
        if from_state_name in [i.name for i in free_states]:
            next_states = self.states
        else:
            next_states = (
                [self._states_dict[from_state_name]]
                + [
                    self._states_dict[state]
                    for state in self.out_transitions.get(from_state_name, [])
                ]
                + free_states
            )

        return next_states

    def _get_free_states(self) -> List[State]:
        """获取自由状态（没有转换约束的状态）

        Returns:
            List[State]: 自由状态列表
        """
        return [
            self._states_dict[state]
            for state in self._states_dict
            if state not in self.out_transitions and state not in self._in_transitions
        ]




# 导出所有公共类和函数
__all__ = [
    "Memory",
    "State",
    "Step",
    "StateMachine",
]
