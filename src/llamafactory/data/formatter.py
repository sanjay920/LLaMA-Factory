import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple, Union


SLOTS = Sequence[Union[str, Set[str], Dict[str, str]]]


JSON_FORMAT_PROMPT = (
    """, in a JSON format representing the kwargs (e.g. ```{"input": "hello world", "num_beams": 5}```)"""
)


TOOL_SYSTEM_PROMPT = (
    "You have access to the following tools:\n{tool_text}"
    "Use the following format if using a tool:\n"
    "```\n"
    "Action: tool name (one of [{tool_names}]).\n"
    "Action Input: the input to the tool{format_prompt}.\n"
    "```\n"
)

TOOL_SYSTEM_PROMPT_RUBRA = (
    "You have access to the following tools: {tool_text}\n"
    "You can choose to respond with one or more tool calls at once, or with a chat message back to the user. "
    "Ensure you have all necessary details before making tool calls. If additional information is needed, "
    "ask the user appropriately. Any tool call you make must correspond to the functions listed above.\n"
    "If you decide to call a tool, format it like this: "
    '[TOOL_CALLS]{{"name": "<function_name>", "arguments": {{"<arg1_name>": "<arg1_value>", "<arg2_name>": "<arg2_value>", ...}}}}[/TOOL_CALLS] '
    "where the JSON wrapped between [TOOL_CALLS] and [/TOOL_CALLS] represents the function call."
)

##################################
# BEGIN TYPESCRIPT TOOL FORMATTER
##################################
def json_schema_to_typescript_type(schema, param_name):
    ts_type = "any"  # default type
    enum_comment = ""
    integer_comment = ""
    description_comment = ""

    if isinstance(schema, dict) and "type" in schema:
        json_type = schema["type"]
        if json_type == "array":
            item_type = (
                "any"
                if "items" not in schema
                else json_schema_to_typescript_type(schema["items"], param_name)[0]
            )
            ts_type = f"{item_type}[]"
        elif json_type == "number":
            ts_type = "number"
        elif json_type == "integer":
            ts_type = (
                "number"  # TypeScript doesn't differentiate between number and integer
            )
            integer_comment = f" * @param {param_name} - Integer"
        elif json_type == "object":
            ts_type, _ = generate_typescript_interface(schema, param_name)
        elif json_type == "boolean":
            ts_type = "boolean"
        elif json_type == "null":
            ts_type = "null"
        elif json_type == "string":
            ts_type = "string"

    if "enum" in schema:
        enum_comment = f" * @enum {param_name} - Possible values: " + ", ".join(
            [f'"{enum_value}"' for enum_value in schema["enum"]]
        )
        ts_type = "string"
    if "description" in schema:
        description_comment = f' * @param {param_name} - {schema["description"]}'

    # Return only the type for nested objects to avoid duplicating comments
    if isinstance(schema, dict) and schema.get("type") == "object":
        return ts_type, "", "", ""

    return ts_type, enum_comment, integer_comment, description_comment


def generate_typescript_interface(schema, interface_name):
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    interface_body = []
    descriptions = []
    for prop_name, prop_schema in properties.items():
        prop_type, enum_comment, integer_comment, description_comment = (
            json_schema_to_typescript_type(prop_schema, prop_name)
        )
        is_optional = prop_name not in required
        interface_body.append(
            f'    {prop_name}{"?" if is_optional else ""}: {prop_type};'
        )
        if description_comment:
            descriptions.append(description_comment)
        if enum_comment:
            descriptions.append(enum_comment)
        if integer_comment:
            descriptions.append(integer_comment)

    comments = "\n".join(descriptions)
    interface_definition = (
        f"interface {interface_name} {{\n" + "\n".join(interface_body) + "\n}"
    )
    return interface_definition, comments


def convert_parameters_list_to_dict(parameters):
    properties = {}
    required = []
    for param in parameters:
        properties[param["name"]] = param
        if "default" not in param:
            required.append(param["name"])
    return {"properties": properties, "required": required}


def generate_typescript_function(function_schema):
    func_name = function_schema["name"]
    description = function_schema.get("description", "")

    # Check if parameters is a list and convert if necessary
    parameters_info = function_schema.get("parameters", {})
    if isinstance(parameters_info, list):
        parameters_info = convert_parameters_list_to_dict(parameters_info)

    parameters_schema = parameters_info.get("properties", {})
    required_params = parameters_info.get("required", [])

    args_list = []
    comments_list = []
    interfaces = []
    for param_name, param_schema in parameters_schema.items():
        ts_type, enum_comment, integer_comment, description_comment = (
            json_schema_to_typescript_type(param_schema, param_name)
        )
        if ts_type.startswith("interface"):
            interface_definition, nested_comments = generate_typescript_interface(
                param_schema, f"{func_name}_{param_name.capitalize()}Params"
            )
            interfaces.append(interface_definition)
            comments_list.append(nested_comments)
            ts_type = f"{func_name}_{param_name.capitalize()}Params"
        else:
            if description_comment:
                comments_list.append(description_comment)
            if enum_comment:
                comments_list.append(enum_comment)
            if integer_comment:
                comments_list.append(integer_comment)
        is_optional = param_name not in required_params
        args_list.append(f'{param_name}{"?" if is_optional else ""}: {ts_type}')

    args_str = ", ".join(args_list)
    comments_str = "\n".join(comments_list)
    interfaces_str = "\n\n".join(interfaces)

    description_comment = f" * {description}\n" if description else ""
    typescript_func_declaration = (
        "/**\n"
        + description_comment
        + (comments_str + "\n" if comments_str else "")
        + " */\n"
        + (interfaces_str + "\n\n" if interfaces_str else "")
        + f"function {func_name}({args_str}): any {{}}"
    )

    return typescript_func_declaration
##################################
# END TYPESCRIPT TOOL FORMATTER
##################################

def rubra_fc_v3_tool_formatter(specs: List[Dict[str, Any]]) -> str:
    function_definitions = []
    for spec in specs:
        try:
            function_definitions.append(generate_typescript_function(spec))
        except Exception as e:
            print(f"Error {e}")
            print(json.dumps(spec))
            print(specs)
            print("=========================")
            continue

    if len(function_definitions) == 0:
        return ""
    typescript_functions_str = "\n\n".join(function_definitions)
    res = TOOL_SYSTEM_PROMPT_RUBRA.format(tool_text=typescript_functions_str)
    return res


def default_tool_formatter(tools: List[Dict[str, Any]]) -> str:
    tool_text = ""
    tool_names = []
    for tool in tools:
        param_text = ""
        for name, param in tool["parameters"]["properties"].items():
            required = ", required" if name in tool["parameters"].get("required", []) else ""
            enum = ", should be one of [{}]".format(", ".join(param["enum"])) if param.get("enum", None) else ""
            items = (
                ", where each item should be {}".format(param["items"].get("type", "")) if param.get("items") else ""
            )
            param_text += "  - {name} ({type}{required}): {desc}{enum}{items}\n".format(
                name=name,
                type=param.get("type", ""),
                required=required,
                desc=param.get("description", ""),
                enum=enum,
                items=items,
            )

        tool_text += "> Tool Name: {name}\nTool Description: {desc}\nTool Args:\n{args}\n".format(
            name=tool["name"], desc=tool.get("description", ""), args=param_text
        )
        tool_names.append(tool["name"])

    return TOOL_SYSTEM_PROMPT.format(
        tool_text=tool_text, tool_names=", ".join(tool_names), format_prompt=JSON_FORMAT_PROMPT
    )


def default_tool_extractor(content: str) -> Union[str, Tuple[str, str]]:
    regex = re.compile(r"Action:\s*([a-zA-Z0-9_]+).*?Action Input:\s*(.*)", re.DOTALL)
    action_match = re.search(regex, content)
    if not action_match:
        return content

    tool_name = action_match.group(1).strip()
    tool_input = action_match.group(2).strip().strip('"').strip("```")
    try:
        arguments = json.loads(tool_input)
    except json.JSONDecodeError:
        return content

    return tool_name, json.dumps(arguments, ensure_ascii=False)


@dataclass
class Formatter(ABC):
    slots: SLOTS = field(default_factory=list)
    tool_format: Optional[Literal["default"]] = None

    @abstractmethod
    def apply(self, **kwargs) -> SLOTS: ...

    def extract(self, content: str) -> Union[str, Tuple[str, str]]:
        raise NotImplementedError


@dataclass
class EmptyFormatter(Formatter):
    def __post_init__(self):
        has_placeholder = False
        for slot in filter(lambda s: isinstance(s, str), self.slots):
            if re.search(r"\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}", slot):
                has_placeholder = True

        if has_placeholder:
            raise ValueError("Empty formatter should not contain any placeholder.")

    def apply(self, **kwargs) -> SLOTS:
        return self.slots


@dataclass
class StringFormatter(Formatter):
    def __post_init__(self):
        has_placeholder = False
        for slot in filter(lambda s: isinstance(s, str), self.slots):
            if re.search(r"\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}", slot):
                has_placeholder = True

        if not has_placeholder:
            raise ValueError("A placeholder is required in the string formatter.")

    def apply(self, **kwargs) -> SLOTS:
        elements = []
        for slot in self.slots:
            if isinstance(slot, str):
                for name, value in kwargs.items():
                    if not isinstance(value, str):
                        raise RuntimeError("Expected a string, got {}".format(value))

                    slot = slot.replace("{{" + name + "}}", value, 1)
                elements.append(slot)
            elif isinstance(slot, (dict, set)):
                elements.append(slot)
            else:
                raise RuntimeError("Input must be string, set[str] or dict[str, str], got {}".format(type(slot)))

        return elements


@dataclass
class FunctionFormatter(Formatter):
    def __post_init__(self):
        has_name, has_args = False, False
        for slot in filter(lambda s: isinstance(s, str), self.slots):
            if "{{name}}" in slot:
                has_name = True
            if "{{arguments}}" in slot:
                has_args = True

        if not has_name or not has_args:
            raise ValueError("Name and arguments placeholders are required in the function formatter.")

    def apply(self, **kwargs) -> SLOTS:
        content = kwargs.pop("content")
        try:
            function = json.loads(content)
            name = function["name"]
            arguments = json.dumps(function["arguments"], ensure_ascii=False)
        except Exception:
            name, arguments = "", ""

        elements = []
        for slot in self.slots:
            if isinstance(slot, str):
                slot = slot.replace("{{name}}", name).replace("{{arguments}}", arguments)
                elements.append(slot)
            elif isinstance(slot, (dict, set)):
                elements.append(slot)
            else:
                raise RuntimeError("Input must be string, set[str] or dict[str, str], got {}".format(type(slot)))

        return elements


@dataclass
class ToolFormatter(Formatter):
    def __post_init__(self):
        if self.tool_format is None:
            raise ValueError("Tool format was not found.")

    def apply(self, **kwargs) -> SLOTS:
        content = kwargs.pop("content")
        try:
            tools = json.loads(content)
            if not len(tools):
                return [""]

            if self.tool_format == "default":
                return [default_tool_formatter(tools)]
            elif self.tool_format == "rubra-fc-v3":
                tools_formatted = [rubra_fc_v3_tool_formatter(tools)]
                # print(tools_formatted)
                return tools_formatted
            else:
                raise NotImplementedError
        except Exception:
            return [""]

    def extract(self, content: str) -> Union[str, Tuple[str, str]]:
        if self.tool_format == "default":
            return default_tool_extractor(content)
        else:
            raise NotImplementedError
