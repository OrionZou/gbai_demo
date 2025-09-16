import json
import yaml
import asyncio
import re
from typing import Optional, Dict, List, Tuple
from pydantic import BaseModel
from openai import AsyncOpenAI
from datetime import datetime
from dateutil import parser

from agent_runtime.data_format.feedback import Feedback, FeedbackSetting, query_feedbacks, TAG_PREFIX_STATE_NAME, TAG_PREFIX_OBSERVATION_NAME
from agent_runtime.data_format.tools import BaseTool, SendMessageToUser, RequestTool


class State(BaseModel):
    name: str
    scenario: str
    instruction: str


class StateMachine(BaseModel):
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
        elif self.initial_state_name and self._states_dict and self.initial_state_name in self._states_dict:
            pass
        else:
            raise ValueError(
                f'Invalid initial_state "{self.initial_state_name}" which is not in states "{self._states_dict.keys()}"')

        # Check out_transitions is valid
        for from_state, transitions in self.out_transitions.items():
            if from_state not in self._states_dict:
                raise ValueError(
                    f"Invalid from_state \"{from_state}\" which is not in states")
            for to_state in transitions:
                if to_state not in self._states_dict:
                    raise ValueError(
                        f"Invalid to_state \"{to_state}\" which is not in states")

        # Initialize _in_transitions
        for from_state, to_states in self.out_transitions.items():
            for to_state in to_states:
                if to_state not in self._in_transitions:
                    self._in_transitions[to_state] = []
                self._in_transitions[to_state].append(from_state)

    def get_state(self, state_name: str) -> Optional[State]:
        if state_name not in self._states_dict:
            raise ValueError(
                f"Invalid state_name \"{state_name}\" which is not in states")
        return self._states_dict[state_name]

    def get_next_states(self, from_state_name: Optional[str] = None) -> List[State]:
        if not self._states_dict:
            return []

        if not from_state_name:
            from_state_name = self.initial_state_name

        if from_state_name not in self._states_dict:
            raise ValueError(
                f"Invalid from_state_name \"{from_state_name}\" which is not in states")

        free_states = self._get_free_states()
        if from_state_name in [i.name for i in free_states]:
            next_states = self.states
        else:
            next_states = [self._states_dict[from_state_name]] + [self._states_dict[state]
                                                                  for state in self.out_transitions.get(from_state_name, [])] + free_states

        return next_states

    def _get_free_states(self) -> List[State]:
        return [self._states_dict[state] for state in self._states_dict if state not in self.out_transitions and state not in self._in_transitions]


class V2Action(BaseModel):
    name: str
    arguments: Optional[dict] = None
    result: Optional[dict] = None


class Step(BaseModel):
    state_name: Optional[str] = None
    actions: List[V2Action] = []
    state_feedbacks: List[Feedback] = []
    action_feedbacks: List[Feedback] = []
    timestamp: Optional[str] = None


class Memory(BaseModel):
    history: List[Step] = []

    def print_history(self) -> str:
        def relative_time_string(iso_str: str) -> str:
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


class Setting(BaseModel):
    api_key: str
    chat_model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1/"
    top_p: float = 1.0
    temperature: float = 1.0,

    top_k: int = 5
    vector_db_url: str = ""
    agent_name: str

    global_prompt: str = ""
    max_history_len: int = 128
    state_machine: StateMachine = StateMachine()


class TokenCounter(BaseModel):
    llm_calling_times: int = 0
    total_input_token: int = 0
    total_output_token: int = 0


async def chat(
    settings: Setting,
    memory: Memory,
    request_tools: List[RequestTool] = [],
    token_counter: Optional[TokenCounter] = None,
) -> Tuple[Memory, TokenCounter]:

    if token_counter is None:
        token_counter = TokenCounter()

    send_message_to_user = SendMessageToUser()
    tools = [send_message_to_user] + request_tools

    if len(tools) != len(set([tool.name for tool in tools])):
        raise ValueError("There are duplicated tool names")

    llm_client = AsyncOpenAI(api_key=settings.api_key,  base_url=settings.base_url)

    # Step 0: Initialize the memory with the init_actions.
    if not memory.history:
        memory.history.append(
            Step(
                state_name=settings.state_machine.initial_state_name,
                actions=[
                    V2Action(name=send_message_to_user.name, arguments={
                           "agent_message": ""}, result=None)
                ]
            )
        )
        return memory, token_counter

    # Step 1: Excute actions.
    memory = await _execute_actions(
        memory=memory,
        tools=tools
    )

    # Step 2: Select the next state.
    state_feedbacks = []
    # If there is no state machine, we need to create a new state.
    if settings.state_machine.states:
        if memory.history and memory.history[-1].actions:
            # TODO: We only get the feedbacks from the final action of the last step.
            # We need to get the feedbacks from all actions of the last step.
            observation_tag = [TAG_PREFIX_OBSERVATION_NAME +
                               memory.history[-1].actions[0].name]
            state_feedbacks = await query_feedbacks(
                settings=FeedbackSetting(
                    vector_db_url=settings.vector_db_url,
                    top_k=settings.top_k,
                    agent_name=settings.agent_name,
                ),
                query=json.dumps(
                    memory.history[-1].actions[0].result, ensure_ascii=False),
                tags=observation_tag,
            )

        current_state = await _select_state(
            llm_client=llm_client,
            settings=settings,
            memory=memory,
            feedbacks=state_feedbacks,
            token_counter=token_counter
        )
    else:
        current_state = await _new_state(
            llm_client=llm_client,
            settings=settings,
            memory=memory,
            token_counter=token_counter
        )

    memory.history[-1].state_feedbacks = state_feedbacks

    # Step 3: Select the next actions.
    action_feedbacks = []
    if memory.history and memory.history[-1].actions:
        # TODO: We only get the feedbacks from the final action of the last step.
        # We need to get the feedbacks from all actions of the last step.
        observation_tag = [TAG_PREFIX_OBSERVATION_NAME +
                           memory.history[-1].actions[0].name]
        state_tag = [TAG_PREFIX_STATE_NAME +
                     current_state.name] if current_state.name else []
        action_feedbacks = await query_feedbacks(
            settings=FeedbackSetting(
                vector_db_url=settings.vector_db_url,
                top_k=settings.top_k,
                agent_name=settings.agent_name
            ),
            query=json.dumps(
                memory.history[-1].actions[0].result, ensure_ascii=False),
            tags=observation_tag + state_tag,
        )

    memory = await _select_actions(
        llm_client=llm_client,
        settings=settings,
        memory=memory,
        tools=tools,
        current_state=current_state,
        feedbacks=action_feedbacks,
        token_counter=token_counter,
    )
    memory.history[-1].action_feedbacks = action_feedbacks


    await llm_client.close()

    # Step 4: Return the memory for mentoring reviewing outside.
    return memory, token_counter


async def _select_state(
    llm_client: AsyncOpenAI,
    settings: Setting,
    memory: Memory,
    feedbacks: List[Feedback],
    token_counter: TokenCounter
) -> State:

    if not settings.state_machine.states:
        raise ValueError("There are no states in state_machine")

    if not memory.history:
        return settings.state_machine.get_state(settings.state_machine.initial_state_name)

    if memory.history[-1].state_name not in settings.state_machine._states_dict:
        raise ValueError(
            f"Invalid state_name \"{memory.history[-1].state_name}\" which is not in states")

    current_state = settings.state_machine.get_state(
        memory.history[-1].state_name)
    next_states = settings.state_machine.get_next_states(
        memory.history[-1].state_name)

    prompt = (
        "You are a professional agent follow the instruction as following:\n{global_prompt}\n"
        "Each step includes a timestamp and may contain a user_message.\nTo make the best decision, consider how recently each user_message was made.\n"
        "Here is the history of steps:\n{history}\n"
        "Here is the state list with index:\n{states}\n"
    ).format(
        global_prompt=settings.global_prompt,
        history=memory.print_history(),
        states=yaml.dump(
            {f"State.{i}": {"name": state.name, "scenario": state.scenario}
                for i, state in enumerate(next_states)},
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        ),
    )

    prompt += (
        "You **MUST** follow examples to select the state based on the **SIMILAR** \"name\" and \"result\" of the last action:\n{feedbacks}\n"
    ).format(
        feedbacks=yaml.dump(
            {
                "Last Action": {
                    "name": memory.history[-1].actions[0].name,
                    "result": memory.history[-1].actions[0].result,
                },
                "Examples": [
                    {
                        "Last Action": {
                            "name": feedback.observation_name,
                            "result": feedback.observation_content,
                        },
                        "Selected State": feedback.state_name,
                    } for feedback in feedbacks
                ]
            },
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
    ) if feedbacks else ""

    prompt += (
        "Now, You need to select the proper state for the next action base on the scenario."
        "The recent actions is more important than previous actions.\n"
        'You must return only the "number" that corresponds to the objective you selected.\n'
    )

    response = await llm_client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": prompt},
            # Empty user message is required for Deepinfra platform
            {"role": "user", "content": ""},
        ],
        top_p=settings.top_p,
        temperature=settings.temperature,
    )

    token_counter.llm_calling_times += 1
    token_counter.total_input_token += response.usage.prompt_tokens
    token_counter.total_output_token += response.usage.completion_tokens

    state_index = _safe_to_int(response.choices[0].message.content)
    if state_index < 0 or state_index >= len(next_states):
        return current_state
    else:
        return next_states[state_index]


async def _new_state(
    llm_client: AsyncOpenAI,
    settings: Setting,
    memory: Memory,
    token_counter: TokenCounter
) -> State:

    prompt = (
        "You are a professional agent follow the instruction as following:\n{global_prompt}\n"
        "The recent actions is more important than previous actions.\n"
        "Each step includes a timestamp and may contain a user_message.\nTo make the best decision, consider how recently each user_message was made.\n"
        "History of steps:\n{history}\n"
        "Now, You need to generate assistant\'s instruction for the next action.\n"
    ).format(
        global_prompt=settings.global_prompt,
        history=memory.print_history(),
    )

    response = await llm_client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": prompt},
            # Empty user message is required for Deepinfra platform
            {"role": "user", "content": ""},
        ],
        top_p=settings.top_p,
        temperature=settings.temperature,
    )

    token_counter.llm_calling_times += 1
    token_counter.total_input_token += response.usage.prompt_tokens
    token_counter.total_output_token += response.usage.completion_tokens

    response = response.choices[0].message.content

    return State(
        name="",
        scenario="",
        instruction=response,
    )


async def _select_actions(
    llm_client: AsyncOpenAI,
    settings: Setting,
    memory: Memory,
    tools: List[BaseTool],
    current_state: State,
    feedbacks: List[Feedback],
    token_counter: TokenCounter
) -> Memory:

    prompt = (
        "You are a professional agent follow the instruction as following:\n{global_prompt}\n"
        "Now, consider the history of steps and select the next action; you **MUST** select at least one action.\n"
        "Each step includes a timestamp and may contain a user_message.\n"
        "To make the best decision, consider how recently each user_message was made.\n"
        "History of steps:\n{history}\n"

    ).format(
        global_prompt=settings.global_prompt,
        history=memory.print_history()
    )

    prompt += (
        "You **MUST** follow examples to select next actions and give **SIMILAR** arguments :\n{feedbacks}\n"
    ).format(
        feedbacks=yaml.dump(
            {
                "Last Action": {
                    "name": memory.history[-1].actions[0].name,
                    "result": memory.history[-1].actions[0].result,
                },
                f"Examples": [
                    {
                        "Last Action": {
                            "name": feedback.observation_name,
                            "result": feedback.observation_content,
                        },
                        "Next Action": {
                            "name": feedback.action_name,
                            "arguments": feedback.action_content,
                        },
                    } for i, feedback in enumerate(feedbacks)
                ]
            },
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )
    ) if feedbacks else ""

    prompt += "And the instruction for the next action is:\n{instruction}\n".format(
        instruction=current_state.instruction,
    )

    response = await llm_client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": prompt},
            # Empty user message is required for Deepinfra platform
            {"role": "user", "content": ""},
        ],
        tools=[tool.get_tool_calling_schema() for tool in tools],
        tool_choice="required",
        top_p=settings.top_p,
        temperature=settings.temperature,
    )

    token_counter.llm_calling_times += 1
    token_counter.total_input_token += response.usage.prompt_tokens
    token_counter.total_output_token += response.usage.completion_tokens

    tools_and_args: list[tuple[BaseTool, dict]] = []
    for tool_call in response.choices[0].message.tool_calls:
        tool = next(tool for tool in tools if tool.name == tool_call.function.name)

        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            arguments = {}

        # Deepseek and Qwen may return the string like '"{\\"foo\\": 42}"'
        # which is a JSON string with escaped quotes. We need to unescape it.
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        tools_and_args.append((tool, arguments))

    if not tools_and_args: # If no tools are selected, we need to send a empty message to the user.
        tools_and_args.append(
            (next([tool for tool in tools if tool.name == "send_message_to_user"], SendMessageToUser()), {"agent_message": ""})
        )

    memory.history.append(
        Step(
            state_name=current_state.name,
            actions=[
                V2Action(name=tool.name, arguments=arguments, result=None)
                for tool, arguments in tools_and_args
            ]
        )
    )
    return memory


async def _execute_actions(
    memory: Memory,
    tools: List[BaseTool]
) -> Memory:

    # LLM may generate the wrong schema for the tool_calling_schema, which may cause the error of execute() got an unexpected keyword argument.
    # So we need to handle the error and return the error message.
    async def _task(action: V2Action) -> V2Action:
        if action.result:
            return action
        try:
            tool = next(
                (tool for tool in tools if tool.name == action.name), None)
            if tool is None:
                action.result = {
                    "error": f"No tool found with the name '{action.name}'."}
            else:
                action.result = await tool.execute(**action.arguments)
        except Exception as e:
            action.result = {"error": str(
                e) + ". You may need to check the schema of the tool_calling_schema."}

        return action

    tasks = [_task(action) for action in memory.history[-1].actions]
    memory.history[-1].actions = await asyncio.gather(*tasks)
    memory.history[-1].timestamp = datetime.now().astimezone().isoformat()
    return memory


def _load_sturcture_response(content: str) -> dict:
    if not content:
        raise ValueError("Empty response content")

    # TODO: Find a better way to handle this.
    # OpenAI (gpt-4o-mini) randomly return a json content with backticks. We should remove it before.
    if content[-1] == "`":
        content = content[:-1]

    try:
        content = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Invalid json format: " + content)

    return content


def _safe_to_int(text: str) -> int:
    """Extracts the first valid integer from a given string.

    If no valid integer is found, the function returns `0`. It uses regex to
    search for the first occurrence of a sequence of digits, optionally
    prefixed by a negative sign (`-`).

    Args:
        text (str): The input string that may contain an integer.

    Returns:
        int: The first integer found in the string, or `0` if none is found.

    Example:
        >>> safe_to_int("Price: -42 USD")
        -42
        >>> safe_to_int("No numbers here")
        0
        >>> safe_to_int("100 apples")
        100
        >>> safe_to_int("--45 banana")
        -45
    """
    matched = re.search(r"-?\d+", text)  # Find first integer in `text`

    return int(matched.group()) if matched else 0