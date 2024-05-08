import json
import re
import ast
import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    TypedDict,
)
import yaml


SLOTS = Sequence[Union[str, Set[str], Dict[str, str]]]


JSON_FORMAT_PROMPT = """, in a JSON format representing the kwargs (e.g. ```{"input": "hello world", "num_beams": 5}```)"""


TOOL_SYSTEM_PROMPT = (
    "You have access to the following tools:\n{tool_text}"
    "Use the following format if using a tool:\n"
    "```\n"
    "Action: tool name (one of [{tool_names}]).\n"
    "Action Input: the input to the tool{format_prompt}.\n"
    "```\n"
)

# TOOL_SYSTEM_PROMPT_RUBRA = (
#     "You have access to the following tools:\n{tool_text}"
#     "Use the following format if using a tool:\n<<functions>>[toolname1(arg1=value1, arg2=value2, ...), toolname2(arg1=value1, arg2=value2, ...)]"
#     "You can choose to respond with 1 or more tool calls at once, or with a chat message back to the user. Only make tool calls once you have all the details to fill in the required params. Feel free to ask the user for more info when appropriate. Any tool call you make must match the name of a function(s) provided above."
# )

TOOL_SYSTEM_PROMPT_RUBRA = (
    "You have access to the following tools: {tool_text}\n"
    "You can choose to respond with one or more tool calls at once, or with a chat message back to the user. "
    "Ensure you have all necessary details before making tool calls. If additional information is needed, "
    "ask the user appropriately. Any tool call you make must correspond to the functions listed above.\n"
    "If you decide to call tools, format your response in JSONL. Start with the keyword `<functions>` followed by the JSON object:\n"
    '`<functions>{{"name": "<function_name>", "arguments": {{"<arg1_name>": "<arg1_value>", "<arg2_name>": "<arg2_value>", ...}}}}`'
)



TOOL_SYSTEM_PROMPT_RUBRA_LLAMA3 = (
    "You have access to the following tools:\n{tool_text}"
    "Respond directly to user queries with accurate and relevant information first. If the user's question directly implies the need for a specific tool or additional data that a tool can provide, then consider using the appropriate tool."
    "When using a tool, format your command as follows:\n[toolname1(arg1=value1, arg2=value2, ...), toolname2(arg1=value1, arg2=value2, ...)]"
    "Always ensure tool use is essential and directly applicable to what the user has asked for. Do not suggest tool use unless it clearly adds value to the response or if the user specifically requests it."
    "If the user's intent is unclear or if the question could have multiple interpretations, clarify the user's needs before providing a response or using any tools. Focus on engaging meaningfully and precisely with the user’s requests."
)


TOOL_SYSTEM_PROMPT_RUBRA_YAML = (
    "You are a helpful assistant equipped with access to various tools. Utilize these tools as needed to enhance your responses or provide specific functionalities, ensuring that all tool uses are justified based on user queries. Do not fabricate tools beyond those specified."
    "YAML formatting guidelines for calling functions are as follows:\n"
    "Example of a Single Function Call:\n"
    "functionCalls:\n"
    "- name: ExampleFunction\n"
    "  arguments:\n"
    "    arg1: value1\n"
    "    arg2: value2\n\n"
    "Example of Multiple Function Calls in Sequence:\n"
    "functionCalls:\n"
    "- name: FirstFunction\n"
    "  arguments:\n"
    "    arg1: value1\n"
    "    ...\n"
    "- name: SecondFunction\n"
    "  arguments:\n"
    "    arg1: value1\n"
    "    ...\n\n"
    "Here's a practical example of function calls in sequence:\n"
    "functionCalls:\n"
    "- name: Midpoint.calculate\n"
    "  arguments:\n"
    "    pointC:\n"
    "    - 5\n"
    "    - 12\n"
    "    pointD:\n"
    "    - 7\n"
    "    - 4\n"
    "- name: register_startup\n"
    "  arguments:\n"
    "    name: SkyHigh\n"
    "    founders:\n"
    "    - Alice\n"
    "    - Bob\n"
    "    funding_amount: 500000\n\n"
    "Always ensure that function calls are correctly formatted in YAML and that their use is directly applicable to the user's request. If the user's intent is unclear, or if a query could be interpreted in multiple ways, clarify the user's needs before responding or using tools. Focus on engaging meaningfully and precisely with user requests."
    "Here are the tools/functions you have access to:\n{tool_text}\n"
)



TOOL_SYSTEM_PROMPT_RUBRA_PYTHON_V1 = (
    "You have access to the following tools, which you can use to perform specific actions:\n{tool_text}"
    "\nTo interact with a tool, format your request as follows:\n[tool_name(arg1=value1, arg2=value2, ...)]"
    "Feel free to respond with either tool calls or chat messages. Make tool calls only once you have all the necessary details. If additional information is needed, ask the user to provide it. Ensure that each tool call accurately reflects the provided function specifications. Do NOT make tool calls to tools that are not defined above. If the user asks to make a tool call to a tool not defined above, you must refuse to and explain why."
)

def rubra_yaml_tool_formatter(specs: List[Dict[str, Any]]) -> str:
    function_definitions = []
    if len(specs) == 1:
        if isinstance(specs[0], list):
            specs = specs[0]
    for spec in specs:
        try:
            if isinstance(spec, list):
                if len(spec) > 1:
                    print("Got a list instead of a single function spec")
                else:
                    spec = spec[0]
            function_definitions.append(function_json_to_yaml(spec))
        except Exception as e:
            print(f"yaml tool Formatter Error {e}")
            print(json.dumps(spec))
            print("specs:\n", specs)
            print("=========================")
            continue

    if len(function_definitions) == 0:
        return ""
    yaml_functions_str = "\n\n".join(function_definitions)
    res = TOOL_SYSTEM_PROMPT_RUBRA_YAML.format(tool_text=yaml_functions_str)
    return res

def process_parameter_from_list(param):
    # Assuming each param in the list is a dictionary representing a parameter
    return process_parameter(param["name"], param, "required" in param)

def function_json_to_yaml(json_data):
    # Change the function to handle a list of functions rather than a single function
    functions_list = [json_data]  # This would be replaced with a list of functions if processing multiple

    formatted_functions = []
    for function in functions_list:
        formatted_data = {
            "functionName": function.get("name", "")
        }

        if function.get("description", "").strip():
            formatted_data["description"] = function["description"]

        if "parameters" in function:
            parameters = function["parameters"]
            if isinstance(parameters, dict):
                formatted_data["parameters"] = process_object(parameters)
            elif isinstance(parameters, list):
                formatted_data["parameters"] = [process_parameter_from_list(param) for param in parameters]
            else:
                print(f"Unexpected type for parameters: {type(parameters)}")

        formatted_functions.append(formatted_data)

    yaml_str = yaml.safe_dump(
        formatted_functions, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    return yaml_str

def process_object(obj_data):
    properties = obj_data.get("properties", {})
    required = obj_data.get("required", [])

    if "required" in properties and not required:
        required = properties["required"]
        del properties["required"]

    param_list = []
    for name, details in properties.items():
        is_required = name in required
        param_info = process_parameter(name, details, is_required)
        if param_info:
            param_list.append(param_info)

    additional_properties = obj_data.get("additionalProperties", None)
    if additional_properties:
        param_info = {"additionalProperties": additional_properties}
        param_list.append(param_info)

    return param_list

def process_parameter(name, details, is_required):
    if not isinstance(details, dict):
        print(f"Invalid parameter details for '{name}'. Expected a dictionary, got {type(details)}. Details: {details}")
        return None

    param_info = {
        "name": name,
        "type": details.get("type", "")
    }

    if details.get("description", "").strip():
        param_info["description"] = details["description"]

    if is_required:
        param_info["required"] = True

    if "enum" in details:
        param_info["enum"] = details["enum"]

    if "format" in details:
        param_info["format"] = details.get("format")

    if details.get("type") == "array" and "items" in details:
        param_info["items"] = process_items(details["items"])

    for key in ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "pattern", "default"]:
        if key in details:
            param_info[key] = details[key]

    if "properties" in details:
        param_info["properties"] = process_object(details)

    additional_properties = details.get("additionalProperties")
    if additional_properties:
        param_info["additionalProperties"] = additional_properties

    return param_info

def process_items(items):
    if "properties" in items:
        return process_object(items)
    else:
        return [{"type": items.get("type", "object")}]

def rubra_python_v1_type_mapping(json_type: str, item_schema=None):
    base_types = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "object": "Dict[str, Any]",
        "array": "List",
        "boolean": "bool",
        "null": "NoneType",
    }
    if json_type == "array" and item_schema:
        item_type = rubra_python_v1_type_mapping(
            item_schema.get("type", "any"), item_schema.get("items")
        )
        return f"List[{item_type}]"
    return base_types.get(json_type, "Any")


def rubra_python_v1_generate_python_types(schema, name_prefix, required_fields):
    properties = schema.get("properties", {})
    type_definitions = []
    type_annotations = {}

    for prop_name, prop_schema in properties.items():
        prop_type = rubra_python_v1_type_mapping(
            prop_schema["type"], prop_schema.get("items")
        )
        if prop_schema["type"] == "object":
            nested_name = f"{name_prefix}_{prop_name.capitalize()}Params"
            nested_required = prop_schema.get("required", [])
            nested_types, nested_annotations = rubra_python_v1_generate_python_types(
                prop_schema, nested_name, nested_required
            )
            type_definitions.extend(nested_types)
            prop_type = nested_name
        is_optional = prop_name not in required_fields
        type_annotations[prop_name] = (prop_type, is_optional)

    type_definitions.append((name_prefix, type_annotations))
    return type_definitions, type_annotations


def rubra_python_v1_generate_python_function(function_schema):
    func_name = function_schema.get("name", "unnamed_function")
    description = function_schema.get("description", "No description provided.")
    parameters = function_schema.get("parameters", {})
    required_params = parameters.get("required", [])

    type_defs, _ = rubra_python_v1_generate_python_types(
        parameters, func_name.capitalize() + "Params", required_params
    )
    function_args = []
    docstring_lines = ['"""', description]
    typed_dict_definitions = []

    for type_name, annotations in type_defs:
        if type_name == func_name.capitalize() + "Params":
            for param, (param_type, is_optional) in annotations.items():
                default_value = " = None" if is_optional else ""
                function_args.append(f"{param}: {param_type}{default_value}")
                param_description = parameters["properties"][param].get(
                    "description", "No description provided."
                )
                docstring_lines.append(f":param {param}: {param_description}")
        else:
            # Define type alias
            fields = ", ".join(f"{k}: {v[0]}" for k, v in annotations.items())
            typed_dict_definitions.append(
                f"class {type_name}(TypedDict, total=False):\n    "
                + "\n    ".join(f"{k}: {v[0]}" for k, v in annotations.items())
            )

    docstring_lines.append('"""')
    docstring = "\n    ".join(docstring_lines)
    args_str = ", ".join(function_args)
    function_definition = f"def {func_name}({args_str}) -> Any:\n    {docstring}\n"

    return "\n".join(typed_dict_definitions) + "\n" + function_definition


def rubra_python_v1_tool_formatter(specs: List[Dict[str, Any]]) -> str:
    function_definitions = []

    for spec in specs:
        try:
            function_definitions.append(rubra_python_v1_generate_python_function(spec))
        except Exception as e:
            print(f"Error {e}")
            print(spec)
            continue

    python_functions_str = "\n".join(function_definitions)
    res = TOOL_SYSTEM_PROMPT_RUBRA_PYTHON_V1.format(tool_text=python_functions_str)
    return res


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


def rubra_fc_v2_tool_formatter(specs: List[Dict[str, Any]]) -> str:
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


def rubra_fc_v2_tool_formatter_llama3(specs: List[Dict[str, Any]]) -> str:
    function_definitions = []
    for spec in specs:
        try:
            function_definitions.append(generate_typescript_function(spec))
        except Exception as e:
            print(f"LLama3 tool Formatter Error {e}")
            print(json.dumps(spec))
            print(specs)
            print("=========================")
            continue

    if len(function_definitions) == 0:
        return ""
    typescript_functions_str = "\n\n".join(function_definitions)
    res = TOOL_SYSTEM_PROMPT_RUBRA_LLAMA3.format(tool_text=typescript_functions_str)
    return res


def rubra_fc_v1_tool_formatter(specs: List[Dict[str, Any]]) -> str:
    function_definitions = []

    type_mapping = {
        "string": "str",
        "number": "float",
        "object": "Dict[str, Any]",
        "number": "float",
        "object": "Dict[str, Any]",
        "number": "float",
        "object": "Dict[str, Any]",
        "array": "List",
        "boolean": "bool",
        "null": "None",
    }

    if isinstance(specs, str):
        print("Oh boy", specs)

    for spec in specs:
        try:
            # print("spec type", type(spec))
            if isinstance(spec, str):
                spec = json.loads(spec)
                print("Converted", spec)

            func_name = spec.get("name", "unnamed_function")
            description = (
                spec.get("description", "No description provided.")
                or "No description provided."
            )

            prop_dict = {}
            required_params = []

            parameters = spec.get("parameters")
            if (
                parameters
                and isinstance(parameters, dict)
                and "properties" in parameters
            ):
                temp_properties = parameters["properties"]
                if isinstance(temp_properties, dict) and (
                    "required" in temp_properties or "optional" in temp_properties
                ):
                    for status in ["required", "optional"]:
                        for item in temp_properties.get(status, []):
                            item["required"] = status == "required"
                            prop_dict[item["name"]] = item
                elif isinstance(temp_properties, list):
                    for item in temp_properties:
                        if isinstance(item, dict) and "name" in item:
                            prop_dict[item["name"]] = item
                elif isinstance(temp_properties, dict):
                    prop_dict = temp_properties
                else:
                    print(f"Unexpected properties format in function {func_name}.")
            elif parameters is None:
                print(f"No parameters defined for function {func_name}.")
                continue  # Skip further processing for this function

            if "required" in parameters and isinstance(parameters["required"], list):
                required_params = parameters["required"]

            func_args = []
            for param, details in prop_dict.items():
                param_type = details.get("type", "Any")
                python_type = (
                    type_mapping.get(param_type.lower(), "Any")
                    if isinstance(param_type, str)
                    else "Any"
                )
                is_required = details.get("required", False)
            func_args = []
            for param, details in prop_dict.items():
                param_type = details.get("type", "Any")
                python_type = (
                    type_mapping.get(param_type.lower(), "Any")
                    if isinstance(param_type, str)
                    else "Any"
                )
                is_required = details.get("required", False)

                arg_str = f"{param}: {python_type}"
                if not is_required:
                    arg_str += " = None"
                func_args.append(arg_str)
                arg_str = f"{param}: {python_type}"
                if not is_required:
                    arg_str += " = None"
                func_args.append(arg_str)
                arg_str = f"{param}: {python_type}"
                if not is_required:
                    arg_str += " = None"
                func_args.append(arg_str)

            func_args_str = ", ".join(func_args) if func_args else ""
            docstring_lines = ['"""', description]
            for param, details in prop_dict.items():
                param_type = details.get("type", "Any")
                python_type = (
                    type_mapping.get(param_type.lower(), "Any")
                    if isinstance(param_type, str)
                    else "Any"
                )
                is_required = details.get("required", False)
                enum_values = details.get("enum")

                # Handle enum values by creating a tuple of possible values for the type hint
                if enum_values:
                    # Format enum values, adding quotes if they are strings
                    formatted_enum_values = [repr(value) for value in enum_values]
                    enum_str = f"Literal[{', '.join(formatted_enum_values)}]"
                    arg_str = f"{param}: {enum_str}"
                else:
                    arg_str = f"{param}: {python_type}"

                if not is_required:
                    arg_str += " = None"
                func_args.append(arg_str)

                # Update docstring with enum values if present
                param_description = details.get(
                    "description", "No description provided."
                )
                if enum_values:
                    # Format enum values for the docstring, adding quotes if they are strings
                    formatted_enum_values = [
                        f'"{value}"' if isinstance(value, str) else str(value)
                        for value in enum_values
                    ]
                    param_description += (
                        f" (Possible values: {', '.join(formatted_enum_values)})"
                    )
                required_text = "" if is_required else "(Optional)"
                docstring_lines.append(
                    f":param {param}: {param_description} {required_text}"
                )
            func_args_str = ", ".join(func_args) if func_args else ""
            docstring_lines = ['"""', description]
            for param, details in prop_dict.items():
                param_type = details.get("type", "Any")
                python_type = (
                    type_mapping.get(param_type.lower(), "Any")
                    if isinstance(param_type, str)
                    else "Any"
                )
                is_required = details.get("required", False)
                enum_values = details.get("enum")

                # Handle enum values by creating a tuple of possible values for the type hint
                if enum_values:
                    # Format enum values, adding quotes if they are strings
                    formatted_enum_values = [repr(value) for value in enum_values]
                    enum_str = f"Literal[{', '.join(formatted_enum_values)}]"
                    arg_str = f"{param}: {enum_str}"
                else:
                    arg_str = f"{param}: {python_type}"

                if not is_required:
                    arg_str += " = None"
                func_args.append(arg_str)

                # Update docstring with enum values if present
                param_description = details.get(
                    "description", "No description provided."
                )
                if enum_values:
                    # Format enum values for the docstring, adding quotes if they are strings
                    formatted_enum_values = [
                        f'"{value}"' if isinstance(value, str) else str(value)
                        for value in enum_values
                    ]
                    param_description += (
                        f" (Possible values: {', '.join(formatted_enum_values)})"
                    )
                required_text = "" if is_required else "(Optional)"
                docstring_lines.append(
                    f":param {param}: {param_description} {required_text}"
                )

            docstring_lines.append('"""')
            docstring = "\n    ".join(docstring_lines)
            function_definition = f"<<function>>\ndef {func_name}({func_args_str}):\n    {docstring}\n<<end_of_function>>"
            function_definitions.append(function_definition)
        except Exception as e:
            print(f"Error {e}")
            print(json.dumps(spec))
            print(specs)
            print(json.dumps(spec))
            print(specs)
            print("=========================")
            continue
            continue

    res = TOOL_SYSTEM_PROMPT_RUBRA.format(tool_text="\n".join(function_definitions))
    return res


def default_tool_formatter(tools: List[Dict[str, Any]]) -> str:
    tool_text = ""
    tool_names = []
    for tool in tools:
        param_text = ""
        for name, param in tool["parameters"]["properties"].items():
            required = (
                ", required" if name in tool["parameters"].get("required", []) else ""
            )
            enum = (
                ", should be one of [{}]".format(", ".join(param["enum"]))
                if param.get("enum", None)
                else ""
            )
            items = (
                ", where each item should be {}".format(param["items"].get("type", ""))
                if param.get("items")
                else ""
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
        tool_text=tool_text,
        tool_names=", ".join(tool_names),
        format_prompt=JSON_FORMAT_PROMPT,
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


def parse_function_call(call):
    func_name, args_str = call.split("(", 1)
    args_str = args_str.rstrip(")")
    args_list = args_str.split(",")
    args_dict = {}
    for arg in args_list:
        key, value = arg.split("=")
        key = key.strip()
        value = value.strip()
        try:
            # Use ast.literal_eval to safely parse the string to its Python type
            parsed_value = ast.literal_eval(value)
        except ValueError as e:
            # If parsing fails, keep the original string.
            # This might happen if the value is a string that's not quoted as a Python literal.
            print(f"Error parsing value {value}: {e}")
            parsed_value = value
        args_dict[key] = parsed_value
    return {"name": func_name.strip(), "arguments": args_dict}


def parse_function_call(call):
    func_name, args_str = call.split("(", 1)
    args_str = args_str.rstrip(")")
    args_list = args_str.split(",")
    args_dict = {}
    for arg in args_list:
        key, value = arg.split("=")
        key = key.strip()
        value = value.strip()
        try:
            # Use ast.literal_eval to safely parse the string to its Python type
            parsed_value = ast.literal_eval(value)
        except ValueError as e:
            # If parsing fails, keep the original string.
            # This might happen if the value is a string that's not quoted as a Python literal.
            print(f"Error parsing value {value}: {e}")
            parsed_value = value
        args_dict[key] = parsed_value
    return {"name": func_name.strip(), "arguments": args_dict}


def rubra_fc_v1_tool_extractor(content: str) -> Union[str, Tuple[str, str]]:
    regex = re.compile(r"<<functions>>\[(.*?)\]", re.DOTALL)
    matches = re.findall(regex, content)

    print("content:", content)

    if not matches:
        return content

    try:
        result_dicts = []
        for match in matches:
            # Splitting each function call from the match. We add ')' back because it was used as a delimiter
            function_calls = [f"{func})" for func in match.split("),") if func]
            print(function_calls)
            for function_call in function_calls:
                # Removing the trailing ')' that was added for the last function call
                if function_call.endswith(")"):
                    function_call = function_call[:-1]
                result_dict = parse_function_call(function_call.strip())
                result_dicts.append(result_dict)
            print(result_dicts)
        return json.dumps(result_dicts, ensure_ascii=False)
    except Exception as e:
        print(f"Exception {e}")
    try:
        result_dicts = []
        for match in matches:
            # Splitting each function call from the match. We add ')' back because it was used as a delimiter
            function_calls = [f"{func})" for func in match.split("),") if func]
            print(function_calls)
            for function_call in function_calls:
                # Removing the trailing ')' that was added for the last function call
                if function_call.endswith(")"):
                    function_call = function_call[:-1]
                result_dict = parse_function_call(function_call.strip())
                result_dicts.append(result_dict)
            print(result_dicts)
        return json.dumps(result_dicts, ensure_ascii=False)
    except Exception as e:
        print(f"Exception {e}")
    try:
        result_dicts = []
        for match in matches:
            # Splitting each function call from the match. We add ')' back because it was used as a delimiter
            function_calls = [f"{func})" for func in match.split("),") if func]
            print(function_calls)
            for function_call in function_calls:
                # Removing the trailing ')' that was added for the last function call
                if function_call.endswith(")"):
                    function_call = function_call[:-1]
                result_dict = parse_function_call(function_call.strip())
                result_dicts.append(result_dict)
            print(result_dicts)
        return json.dumps(result_dicts, ensure_ascii=False)
    except Exception as e:
        print(f"Exception {e}")
        return content


# def rubra_fc_v2_tool_extractor(content: str):
#     # Regex to extract content within <<functions>>[...]
#     regex = re.compile(r"<<functions>>\[(.*?)\]", re.DOTALL)
#     matches = re.findall(regex, content)

#     if not matches:
#         return content

#     # Process each match
#     result_dicts = []
#     for match in matches:
#         # Wrap the extracted string in brackets if it's not a list format expected by ast.parse
#         if not match.strip().startswith("["):
#             match = f"[{match}]"
#         try:
#             parsed = ast.parse(match, mode="eval")
#         except SyntaxError as e:
#             print(f"Syntax error while parsing functions: {e}\n", content)
#             continue

#         # Assuming the outer structure is a list
#         if isinstance(parsed.body, ast.List):
#             for func in parsed.body.elts:
#                 if isinstance(func, ast.Call):
#                     func_name = func.func.id
#                     args_dict = {}
#                     for keyword in func.keywords:
#                         arg_name = keyword.arg
#                         # We use ast.literal_eval to safely evaluate the value
#                         if isinstance(keyword.value, ast.Constant):
#                             arg_value = keyword.value.value
#                         else:
#                             arg_value = ast.dump(keyword.value)
#                         args_dict[arg_name] = arg_value
#                     result_dicts.append({"name": func_name, "arguments": args_dict})

#     # Convert result dictionaries to JSON
#     return json.dumps(result_dicts, ensure_ascii=False)

def rubra_fc_v2_tool_extractor(content: str) -> str:
    # Check if the content starts with <functions>
    if content.startswith('<functions>'):
        # Remove the <functions> tag
        content = content[len('<functions>'):].strip()
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


def rubra_fc_yaml_tool_extractor(content: str):
    print("Original content to rubra_fc_yaml_tool_extractor content-----\n", content)
    regex = re.compile(r"<<functions>>(.*)", re.DOTALL)
    matches = re.findall(regex, content)
    print("Extracted content-----\n", matches)

    if not matches:
        print("No matches found")
        return content

    yaml_content = matches[0].strip()
    yaml_content = re.sub(r"(<<functions>>)*", "", yaml_content)
    corrected_yaml_content = ""
    previous_indent = 0
    indent_stack = [0]  # Manage indentation levels

    for line in yaml_content.splitlines():
        # Remove incorrect quote and parenthesis handling
        line = re.sub(r"['\"]?\)$", "", line)  # Remove trailing quotes and parenthesis
        line = line.replace("'''", "'")        # Fix triple single quotes

        current_indent = len(line) - len(line.lstrip())

        # Adjust indentation based on current structure
        if current_indent > previous_indent:
            indent_stack.append(current_indent)
        elif current_indent < previous_indent and current_indent in indent_stack:
            indent_stack = indent_stack[:indent_stack.index(current_indent) + 1]

        new_indent = (len(indent_stack) - 1) * 2  # Standard YAML indentation
        corrected_yaml_content += " " * new_indent + line.strip() + '\n'

        previous_indent = current_indent

    print("Corrected YAML content-----\n", corrected_yaml_content)

    # Attempt to parse the corrected YAML content
    try:
        parsed_data = yaml.safe_load(corrected_yaml_content)
    except yaml.YAMLError as exc:
        print("Error parsing YAML:", exc)
        return content

    print("Parsed data-----\n", parsed_data)

    # Ensure parsed_data is a list of dictionaries
    if not isinstance(parsed_data, list):
        print("Parsed data is not a list")
        return json.dumps([])

    # Replace 'functionCall' with 'name' in the list of dictionaries
    for item in parsed_data:
        if item and 'functionCall' in item:
            item['name'] = item.pop('functionCall')

    return json.dumps(parsed_data, ensure_ascii=False)

def auto_correct_indentation(content: str):
    """
    Automatically corrects YAML indentation by ensuring each list item or key-value pair
    is properly indented relative to its parent structure.
    """
    lines = content.splitlines()
    corrected_lines = []
    stack = []  # Stack to track the indentation levels of list items

    for line in lines:
        if line.strip() == "":
            corrected_lines.append("")
            continue

        current_indent = len(line) - len(line.lstrip())
        stripped_line = line.lstrip()

        if stripped_line.startswith('-'):
            # It's a list item
            if not stack or current_indent > stack[-1]:
                # New block or sub-item more indented than the last
                if stack:
                    if current_indent <= stack[-1] + 1:
                        current_indent = stack[-1] + 2
                stack.append(current_indent)
            else:
                # Possibly same level or backtracking
                while stack and current_indent <= stack[-1]:
                    stack.pop()
                stack.append(current_indent)
        else:
            # It's a key-value mapping under a list
            if stack:
                expected_indent = stack[-1] + 2
                if current_indent != expected_indent:
                    current_indent = expected_indent

        corrected_lines.append(' ' * current_indent + stripped_line)

    return '\n'.join(corrected_lines)

def rubra_fc_yaml_tool_extractor_v2(content: str):
    """
    Extracts and processes YAML content describing function calls,
    converting them from YAML to a JSON format directly with indentation correction.
    """
    corrected_content = auto_correct_indentation(content)
    try:
        data = yaml.safe_load(corrected_content)
        if not data or 'functionCalls' not in data:
            print("No valid data extracted.")
            return content
        print("Corrected YAML content:::\n", corrected_content)
        print("Extracted data:::\n", data)
        return json.dumps(data['functionCalls'], ensure_ascii=False)
    except yaml.YAMLError as exc:
        print("Error parsing YAML:", exc)
        print("Corrected content:\n-----")
        print(corrected_content)
        return content
    
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
                raise RuntimeError(
                    "Input must be string, set[str] or dict[str, str], got {}".format(
                        type(slot)
                    )
                )

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
            raise ValueError(
                "Name and arguments placeholders are required in the function formatter."
            )

    def apply(self, **kwargs) -> SLOTS:
        try:
            content = kwargs.pop("content")
            function = json.loads(content)
            name = function["name"]
            arguments = json.dumps(function["arguments"], ensure_ascii=False)
        except Exception:
            name, arguments = "", ""

        elements = []
        for slot in self.slots:
            if isinstance(slot, str):
                slot = slot.replace("{{name}}", name).replace(
                    "{{arguments}}", arguments
                )
                elements.append(slot)
            elif isinstance(slot, (dict, set)):
                elements.append(slot)
            else:
                raise RuntimeError(
                    "Input must be string, set[str] or dict[str, str], got {}".format(
                        type(slot)
                    )
                )

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
            elif self.tool_format == "rubra-fc-v1":
                return [rubra_fc_v1_tool_formatter(tools)]
            elif self.tool_format == "rubra-fc-v2":
                tools_formatted = [rubra_fc_v2_tool_formatter(tools)]
                # print(tools_formatted)
                return tools_formatted
            elif self.tool_format == "rubra-fc-yaml":
                tools_formatted = [rubra_yaml_tool_formatter(tools)]
                # print(tools_formatted)
                return tools_formatted
            elif self.tool_format == "rubra-fc-v2-llama3":
                tools_formatted = [rubra_fc_v2_tool_formatter_llama3(tools)]
                # print(tools_formatted)
                return tools_formatted
            elif self.tool_format == "rubra_python_v1_tool_formatter":
                tools_formatted = [rubra_python_v1_tool_formatter(tools)]
                # print(tools_formatted)
                # print("====")
                return tools_formatted
            else:
                raise NotImplementedError
        except Exception as e:
            print(e)
            return [""]

    def extract(self, content: str) -> Union[str, Tuple[str, str]]:
        # print("tool_format", self.tool_format)
        if self.tool_format == "default":
            return default_tool_extractor(content)
        elif self.tool_format == "rubra-fc-v1":
            return rubra_fc_v1_tool_extractor(content)
        elif self.tool_format == "rubra-fc-v2":
            return rubra_fc_v2_tool_extractor(content)
        elif self.tool_format == "rubra-fc-v2-llama3":
            return rubra_fc_v2_tool_extractor(content)
        elif self.tool_format == "rubra-fc-yaml":
            return rubra_fc_yaml_tool_extractor_v2(content)
        elif self.tool_format == "rubra_python_v1_tool_formatter":
            return rubra_fc_v2_tool_extractor(content)
        else:
            raise NotImplementedError
