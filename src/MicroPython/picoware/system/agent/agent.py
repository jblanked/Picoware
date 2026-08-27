"""Agent - LLM-powered assistant with tools."""

import json
from micropython import const
from picoware.system.agent.tools import dispatch
from picoware.system.agent.llm import LLM, DEEPSEEK
from picoware.system.agent.context import chat, app_creator, device_manager
from picoware.system.agent.session import Session
from picoware.system.agent.mcp import (
    MCPClient,
    MCP_LIST_SERVERS_TOOL,
    MCP_LIST_SERVERS_TOOL_NAME,
    MCP_SELECT_SERVER_TOOL,
    MCP_SELECT_SERVER_TOOL_NAME,
)

MODE_CHAT = const(0) # general chat mode
MODE_APP_CREATOR = const(1) # creates/edits Picoware apps
MODE_DEVICE_MANAGER = const(2) # manages files, has network access, can run commands, etc.

MAX_TOOL_ITERATIONS = const(50)
MAX_CONVERSATION_MESSAGES = const(20)

class Agent:
    """Agent that can perform tasks using tools and LLMs."""
    __slots__ = [
        "mode",
        "tools",
        "llm",
        "view_manager",
        "http",
        "_file_path",
        "_conv_path",
        "_mem_path",
        "_msg_path",
        "_mcp",
        "_mcp_tool_routes",
        "_mcp_tool_schemas",
    ]

    def __init__(self, view_manager, mode: int = MODE_CHAT, llm: LLM = None, file_path: str = "picoware/settings/agent_request.json"):
        """Initialize the agent with a mode, LLM, and request file path.

        Args:
            view_manager (ViewManager): The view manager for storage and threading.
            mode (int): The agent mode constant. Defaults to MODE_CHAT.
            llm (LLM): The LLM client to use. Defaults to None.
            file_path (str): Path to the API request file. Defaults to "picoware/settings/agent_request.json".
        """
        from picoware.system.http import HTTP
        self.view_manager = view_manager
        self.mode = mode
        self.tools = []
        self.llm = llm if llm is not None else LLM(view_manager.storage, DEEPSEEK)
        self.http = HTTP(thread_manager=view_manager.thread_manager)
        self._file_path = file_path
        self._conv_path = "picoware/settings/agent_conv.json"
        self._mem_path = "picoware/settings/agent_mem.json"
        self._msg_path = "picoware/settings/agent_msg.json"

        from picoware.system.settings import Settings
        settings = Settings(view_manager.storage)
        self._mcp = MCPClient(
            self.http,
            settings.mcp_servers,
        )
        self._mcp_tool_routes = {}
        self._mcp_tool_schemas = []

        s = self.view_manager.storage
        s.remove(self._conv_path)
        s.remove(self._mem_path)
        s.remove(self._msg_path)
    
    def __del__(self):
        """Cleanup resources on deletion."""
        self.tools.clear()
        self._mcp_tool_routes.clear()
        self._mcp_tool_schemas.clear()
        self._mcp = None
        self.llm = None
        self.http = None
    
    @property
    def file_path(self) -> str:
        """Get the file path associated with the agent."""
        return self._file_path

    def _parse_tool_arguments(self, raw_args) -> dict:
        """Parse tool-call arguments defensively into a dict.

        Args:
            raw_args (str or dict): Raw arguments from the model call.

        Returns:
            dict: The parsed arguments, or an empty dict if unparseable.
        """
        if isinstance(raw_args, dict):
            return raw_args

        if not isinstance(raw_args, str):
            return {}

        text = raw_args.strip()
        if not text:
            return {}

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return {}
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except ValueError:
                return {}

    def _conv_write_initial(self, messages: list[dict]) -> None:
        """Write the initial conversation messages to the conversation file.

        Args:
            messages (list[dict]): The initial messages to store.
        """
        storage = self.view_manager.storage

        for i, msg in enumerate(messages):
            if i == 0:
                if msg.get("role") == "system":
                    self._write_system_message(storage)
                else:
                    storage.write(self._conv_path, json.dumps(msg), mode="w")
            else:
                storage.write(self._conv_path, ',' + json.dumps(msg), mode="a")

    def _conv_append(self, message: dict) -> None:
        """Append one message to the conversation file.

        Args:
            message (dict): The message to append.
        """
        storage = self.view_manager.storage

        if not storage.exists(self._conv_path):
            storage.write(self._conv_path, json.dumps(message), mode="w")
        else:
            storage.write(self._conv_path, ',' + json.dumps(message), mode="a")

    @staticmethod
    def _json_escape(text: str) -> str:
        """Escape a string for embedding in JSON.

        Args:
            text (str): The raw string to escape.

        Returns:
            str: The JSON-escaped string.
        """
        return (text
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))

    @staticmethod
    def _stream_file_json_escaped(storage, src_path: str, dst_path: str) -> None:
        """Stream a file to the destination with JSON escaping.

        Args:
            storage (Storage): The storage interface.
            src_path (str): The source file path.
            dst_path (str): The destination file path.
        """
        src = storage.file_open(src_path)
        if src is None:
            return
        try:
            buf = bytearray(2048)
            carry = ""
            while True:
                n = storage.file_readinto(src, buf)
                if not n:
                    break
                chunk = carry + buf[:n].decode('utf-8')
                if chunk.endswith('\\'):
                    carry = '\\'
                    chunk = chunk[:-1]
                else:
                    carry = ""
                if not chunk:
                    continue
                storage.write(dst_path, Agent._json_escape(chunk), mode="a")
            if carry:
                storage.write(dst_path, '\\\\', mode="a")
        finally:
            storage.file_close(src)

    def _write_system_message(self, storage) -> None:
        """Write the system message to the conversation file.

        Args:
            storage (Storage): The storage interface.
        """
        storage.write(self._conv_path, '{"role":"system","content":"', mode="w")
        if storage.exists(self._mem_path):
            self._stream_file_json_escaped(storage, self._mem_path, self._conv_path)
        storage.write(self._conv_path, '"}', mode="a")

    def _build_tools(self) -> list[dict]:
        """Build built-in and currently selected MCP tool schemas."""
        tools = [tool.json_openai for tool in dispatch.get_tool_list()]
        if self._mcp.enabled:
            tools.extend(
                [
                    MCP_LIST_SERVERS_TOOL,
                    MCP_SELECT_SERVER_TOOL,
                ]
            )
            tools.extend(self._mcp_tool_schemas)
        return tools

    def _select_mcp_server(self, args: dict) -> dict:
        """Select an MCP server and expose its discovered tools."""
        server_id = args.get("server_id") if isinstance(args, dict) else None
        server, tools = self._mcp.select_server(server_id)
        self._mcp_tool_routes.clear()
        self._mcp_tool_schemas.clear()
        used_names = [
            MCP_LIST_SERVERS_TOOL_NAME,
            MCP_SELECT_SERVER_TOOL_NAME,
        ]
        tool_summaries = []

        for tool in tools:
            tool_name = tool.get("name")
            if not isinstance(tool_name, str) or not tool_name:
                continue
            exposed_name = self._mcp_tool_name(server["id"], tool_name, used_names)
            used_names.append(exposed_name)
            self._mcp_tool_routes[exposed_name] = (server["id"], tool_name)

            description = tool.get("description", "")
            if not isinstance(description, str) or not description:
                description = "MCP tool " + tool_name
            input_schema = tool.get("inputSchema")
            if not isinstance(input_schema, dict):
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
            self._mcp_tool_schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": exposed_name,
                        "description": description,
                        "parameters": input_schema,
                    },
                }
            )
            tool_summaries.append(
                {
                    "name": tool_name,
                    "description": description,
                }
            )

        return {
            "server": server,
            "tools": tool_summaries,
        }

    @staticmethod
    def _mcp_tool_name(server_id: str, tool_name: str, used_names: list[str]) -> str:
        """Create a unique model-safe name for an MCP tool."""
        base = "mcp_" + Agent._sanitize_tool_name(server_id) + "_" + Agent._sanitize_tool_name(tool_name)
        candidate = base[:64]
        suffix = 1
        while candidate in used_names:
            suffix_text = "_" + str(suffix)
            candidate = base[: 64 - len(suffix_text)] + suffix_text
            suffix += 1
        return candidate

    @staticmethod
    def _sanitize_tool_name(name: str) -> str:
        """Replace characters unsupported by common tool-name schemas."""
        result = ""
        for character in name:
            if character.isalnum() or character in "_-":
                result += character
            else:
                result += "_"
        return result or "tool"

    def _execute_tool(self, name: str, args: dict):
        """Execute a built-in or selected MCP tool."""
        if name == MCP_LIST_SERVERS_TOOL_NAME:
            return self._mcp.list_servers()
        if name == MCP_SELECT_SERVER_TOOL_NAME:
            return self._select_mcp_server(args)
        route = self._mcp_tool_routes.get(name)
        if route is not None:
            return self._mcp.call_tool(route[0], route[1], args)
        return dispatch.execute_tool(self.view_manager, name, args)

    def _build_request(self, tools: list[dict]) -> None:
        """Stream the conversation and metadata into the API request file.

        Args:
            tools (list[dict]): The tool schemas to include in the request.
        """
        storage = self.view_manager.storage

        # Preamble: model + messages open
        storage.write(
            self._file_path,
            '{"model":"' + self.llm.model + '","messages":[',
            mode="w",
        )

        # Stream conversation file
        conv_file = storage.file_open(self._conv_path)
        if conv_file is not None:
            try:
                buf = bytearray(2048)
                while True:
                    n = storage.file_readinto(conv_file, buf)
                    if not n:
                        break
                    storage.write(self._file_path, buf[:n], mode="b")
            finally:
                storage.file_close(conv_file)

        # tools
        storage.write(
            self._file_path,
            '],"tools":' + json.dumps(tools) + ',"tool_choice":"auto",',
            mode="a",
        )

        # thinking 
        _payload = self.llm.thinking_payload
        _payload_str = json.dumps(_payload)
        # strip { }
        _payload_str = _payload_str[1:-1]
        storage.write(self._file_path, _payload_str, mode="a")

        # close
        storage.write(self._file_path, "}", mode="a")


    def _run_loop(self) -> str:
        """Run the model/tool loop until a final reply is produced.

        Returns:
            str: The final assistant text, or an error message.
        """
        storage = self.view_manager.storage

        for _ in range(MAX_TOOL_ITERATIONS):
            # Build request from conversation
            tools = self._build_tools()
            self._build_request(tools)

            response = self.http.post(
                self.llm.url,
                headers=self.llm.headers,
                payload=None,
                timeout=120,
                storage=storage,
                send_file=self._file_path,
            )

            try:
                data = response.json()
            except ValueError:
                body = response.text.strip()
                if len(body) > 500:
                    body = body[:500] + "..."
                return f"API error: Invalid JSON response from model API: {body}"

            if "choices" not in data:
                error_detail = data.get("error", {})
                if isinstance(error_detail, dict):
                    error_msg = error_detail.get("message", str(data))
                else:
                    error_msg = str(data)
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + "..."
                return f"API error: {error_msg}"

            message = data["choices"][0]["message"]

            if not message.get("tool_calls"):
                content = message.get("content", "")
                # Store final reply
                self._conv_append({"role": "assistant", "content": content})
                self.view_manager.log(f"[Agent] Final response: {content}")
                return content if isinstance(content, str) else str(content)

            # Store assistant message
            assistant_message: dict = {
                "role": "assistant",
                "tool_calls": message["tool_calls"],
            }
            if message.get("content") is not None:
                assistant_message["content"] = message["content"]
            self._conv_append(assistant_message)

            for tool_call in message["tool_calls"]:
                name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", "{}")
                args = self._parse_tool_arguments(raw_args)

                try:
                    self.view_manager.log(f"[Agent] Executing {name} with args: {args}")
                    result = self._execute_tool(name, args)
                    self.view_manager.log(f"[Agent] {name} returned: {result}")
                except (TypeError, ValueError, KeyError) as exc:
                    result = f"Tool error in {name}: {exc}"
                    self.view_manager.log(f"[Agent] {result}")

                # Store tool result
                self._conv_append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "unknown_tool_call"),
                        "content": str(result),
                    }
                )

        return "An error occurred during processing: Tool loop exceeded max iterations."
    
    def _sanitize_conversation(
        self,
        conversation: list[dict] | None,
        max_messages: int = MAX_CONVERSATION_MESSAGES,
    ) -> list[dict[str, str]]:
        """Normalize history to user and assistant text messages only.

        Args:
            conversation (list[dict] or None): Raw message history. Defaults to None.
            max_messages (int): Maximum messages to keep. Defaults to MAX_CONVERSATION_MESSAGES.

        Returns:
            list[dict[str, str]]: The sanitized message list.
        """
        if not isinstance(conversation, list):
            return []

        sanitized: list[dict[str, str]] = []
        for message in conversation:
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str):
                continue

            text = content.strip()
            if not text:
                continue

            sanitized.append({"role": role, "content": text})

        if len(sanitized) > max_messages > 0:
            return sanitized[-max_messages:]
        return sanitized


    def run(self,topic: str, conversation: list[dict] | None = None, context=None) -> str:
        """Run the agent for a prompt and return the response text.

        Args:
            topic (str): The user prompt.
            conversation (list[dict] or None): Prior message history. Defaults to None.
            context (str or None): Extra context prepended to the system prompt. Defaults to None.

        Returns:
            str: The assistant response text, or an error message.
        """
        user_message = topic.strip()
        if not user_message:
            return "No message provided."
        
        s = self.view_manager.storage
        if context is not None:
            s.write(self._mem_path, f"{context.strip()}\n", mode="a")
        else:
            f = s.file_open(self._mem_path)
            if f is not None:
                try:
                    if self.mode == MODE_CHAT:
                        s.file_write(f, chat.PROMPT, mode="b")
                        s.file_write(f, b"\n", mode="b")
                        s.file_write(f, chat.WORKFLOW, mode="b")
                        s.file_write(f, b"\n", mode="b")
                        s.file_write(f, chat.CONTEXT, mode="b")
                        s.file_write(f, b"\n", mode="b")
                    elif self.mode == MODE_APP_CREATOR:
                        s.file_write(f, app_creator.PROMPT, mode="b")
                        s.file_write(f, b"\n", mode="b")
                        s.file_write(f, app_creator.WORKFLOW, mode="b")
                        s.file_write(f, b"\n", mode="b")
                        s.file_write(f, app_creator.CONTEXT, mode="b")
                        s.file_write(f, b"\n", mode="b")
                    elif self.mode == MODE_DEVICE_MANAGER:
                        s.file_write(f, device_manager.PROMPT, mode="b")
                        s.file_write(f, b"\n", mode="b")
                        s.file_write(f, device_manager.WORKFLOW, mode="b")
                        s.file_write(f, b"\n", mode="b")
                        s.file_write(f, device_manager.CONTEXT, mode="b")
                        s.file_write(f, b"\n", mode="b")
                finally:
                    s.file_close(f)

        # Write initial messages to storage
        messages = [{"role": "system", "content": ""}]
        messages.extend(self._sanitize_conversation(conversation))
        messages.append({"role": "user", "content": user_message})

        try:
            self._mcp.reset()
            self._mcp_tool_routes.clear()
            self._mcp_tool_schemas.clear()
            self._conv_write_initial(messages)
            return self._run_loop()
        except Exception as exc:
            return f"An error occurred during processing: {exc}"

    def run_payload(self, payload: dict) -> dict:
        """Run the agent with a JSON payload and return a structured response.

        Args:
            payload (dict): The request payload with message and conversation keys.

        Returns:
            dict: The response with status, message, and conversation keys.
        """
        if not isinstance(payload, dict):
            return {
                "status": "error",
                "message": "Invalid payload format.",
                "conversation": [],
            }

        topic = payload.get("message") or payload.get("topic")
        conversation = self._sanitize_conversation(payload.get("conversation"))

        if not isinstance(topic, str) or not topic.strip():
            return {
                "status": "error",
                "message": "No message provided.",
                "conversation": conversation,
            }

        topic = topic.strip()
        message = self.run(topic, conversation=conversation)
        updated_conversation = self._sanitize_conversation(
            conversation
            + [
                {"role": "user", "content": topic},
                {"role": "assistant", "content": message},
            ]
        )

        status = (
            "error"
            if isinstance(message, str) and message.startswith((
            "API error",
            "An error occurred during processing:",
        ))
            else "completed"
        )

        return {
            "status": status,
            "message": message,
            "conversation": updated_conversation,
        }

    def run_session(self, session_id: str, user_message: str) -> dict:
        """Run the agent with a session ID and user message, returning a structured response.

        Args:
            session_id (str): The unique identifier for the session.
            user_message (str): The user's message to process.

        Returns:
            dict: The response with status, message, and conversation keys.
        """
        try:
            session = Session(self.view_manager, session_id=session_id)
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Failed to load session: {exc}",
                "conversation": [],
            }

        payload = {
            "message": user_message,
            "conversation": session.conversation,
        }
        result = self.run_payload(payload)

        if result["status"] == "completed":
            session.append({"role": "user", "content": user_message})
            session.append({"role": "assistant", "content": result["message"]})

        return result

    