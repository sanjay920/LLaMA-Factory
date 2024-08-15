# Copyright 2024 the LlamaFactory team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple, Union

from .data_utils import SLOTS
from .tool_utils import DefaultToolUtils, GLM4ToolUtils


@dataclass
class Formatter(ABC):
    slots: SLOTS = field(default_factory=list)
    tool_format: Optional[Literal["default", "glm4"]] = None

    @abstractmethod
    def apply(self, **kwargs) -> SLOTS: ...

    def extract(self, content: str) -> Union[str, List[Tuple[str, str]]]:
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
    
TOOL_SYSTEM_PROMPT_RUBRA = (
    "You have access to the following tools: {tool_text}\n"
    "You can choose to respond with one or more tool calls at once, or with a chat message back to the user. "
    "Ensure you have all necessary details before making tool calls. If additional information is needed, "
    "ask the user appropriately. Any tool call you make must correspond to the functions listed above.\n"
    "If you decide to call a tool, format it like this: "
    'starttoolcall{{"name": "<function_name>", "arguments": {{"<arg1_name>": "<arg1_value>", "<arg2_name>": "<arg2_value>", ...}}}}endtoolcall '
    "where the JSON wrapped between starttoolcall and endtoolcall represents the function call."
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

def rubra_fc_v3_tool_extractor(content: str) -> str:
    print(content)
    # Check if the content starts with [TOOL_CALLS]
    if content.startswith('[TOOL_CALLS]'):
        # Remove the [TOOL_CALLS] tag
        content = content[len('[TOOL_CALLS]'):].strip()
        # Remove the [/TOOL_CALLS] tag if it exists anywhere in the content
        content = content.replace('[/TOOL_CALLS]', '').strip()
        print(content)
        # Initialize list to hold the resulting dictionaries and raw JSON strings
        result_dicts = []
        # Split the content into individual JSON strings (assuming each JSON is separated by a new line)
        json_strings = content.split('\n')
        # Process each JSON string
        for json_string in json_strings:
            json_string = json_string.strip()  # Remove any leading/trailing whitespace
            if not json_string:
                continue  # Skip empty lines
            try:
                # Try to parse the JSON string into a dictionary
                json_dict = json.loads(json_string)
                # Add the dictionary to the list
                result_dicts.append(json_dict)
            except json.JSONDecodeError:
                # Add the raw JSON string to the list if it cannot be decoded
                result_dicts.append(json_string)
        # Convert the list of dictionaries and strings to a JSON string and return
        return json.dumps(result_dicts, ensure_ascii=False)
    else:
        # Return the content as is if it doesn't start with <functions>
        return content

@dataclass
class FunctionFormatter(Formatter):
    def __post_init__(self):
        if self.tool_format == "default":
            self.slots = DefaultToolUtils.get_function_slots() + self.slots
        elif self.tool_format == "glm4":
            self.slots = GLM4ToolUtils.get_function_slots() + self.slots
        else:
            raise NotImplementedError("Tool format {} was not found.".format(self.tool_format))

    def apply(self, **kwargs) -> SLOTS:
        content = kwargs.pop("content")
        functions: List[Tuple[str, str]] = []
        try:
            tool_calls = json.loads(content)
            if not isinstance(tool_calls, list):  # parallel function call
                tool_calls = [tool_calls]

            for tool_call in tool_calls:
                functions.append((tool_call["name"], json.dumps(tool_call["arguments"], ensure_ascii=False)))

        except json.JSONDecodeError:
            functions = []

        elements = []
        for name, arguments in functions:
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
        if self.tool_format == "default":
            self._tool_formatter = DefaultToolUtils.tool_formatter
            self._tool_extractor = DefaultToolUtils.tool_extractor
        elif self.tool_format == "glm4":
            self._tool_formatter = GLM4ToolUtils.tool_formatter
            self._tool_extractor = GLM4ToolUtils.tool_extractor
        elif self.tool_format == "rubra-fc-v3":
            self._tool_formatter = rubra_fc_v3_tool_formatter
            self._tool_extractor = rubra_fc_v3_tool_extractor
        else:
            raise NotImplementedError("Tool format {} was not found.".format(self.tool_format))

    def apply(self, **kwargs) -> SLOTS:
        content = kwargs.pop("content")
        try:
            tools = json.loads(content)
            return [self._tool_formatter(tools) if len(tools) != 0 else ""]
        except json.JSONDecodeError:
            return [""]

    def extract(self, content: str) -> Union[str, List[Tuple[str, str]]]:
        return self._tool_extractor(content)
