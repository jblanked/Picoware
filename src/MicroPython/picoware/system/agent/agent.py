import json
from micropython import const
from ujson import dumps
from picoware.system.agent.tools import dispatch
from picoware.system.agent.llm import LLM, DEEPSEEK

MODE_APP_CREATOR = const(0) # creates/edits Picoware apps
MODE_DEVICE_MANAGER = const(1) # manages files, has network access, can run commands, etc.

MAX_TOOL_ITERATIONS = const(50)
MAX_CONVERSATION_MESSAGES = const(20)

class Agent:
    """Agent that can perform tasks using tools and LLMs."""
    __slots__ = ["mode", "tools", "llm_provider", "view_manager", "http"]

    def __init__(self, view_manager, mode: int, llm_id: int = DEEPSEEK):
        from picoware.system.http import HTTP
        self.view_manager = view_manager
        self.mode = mode
        self.tools = []
        self.llm_provider = LLM(view_manager.storage, llm_id)
        self.http = HTTP(thread_manager=view_manager.thread_manager)

    def _parse_tool_arguments(self, raw_args) -> dict:
        """Parse tool-call arguments defensively and return a dict."""
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
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return {}
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}


    def _run_loop(self, messages: list[dict]) -> str:
        """Run the model/tool loop and return assistant text."""
        tools = [tool.json_openai for tool in dispatch.get_tool_list()]

        for _ in range(MAX_TOOL_ITERATIONS):
            payload: dict = {
                "model": self.llm_provider.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.llm_provider.api_key}", 
            }

            response = self.http.post(self.llm_provider.url, headers=headers, payload=dumps(payload), timeout=120)

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
                self.view_manager.log(f"[Agent] Final response: {content}")
                return content if isinstance(content, str) else str(content)

            assistant_message: dict = {
                "role": "assistant",
                "tool_calls": message["tool_calls"],
            }
            if message.get("content") is not None:
                assistant_message["content"] = message["content"]
            messages.append(assistant_message)

            for tool_call in message["tool_calls"]:
                name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", "{}")
                args = self._parse_tool_arguments(raw_args)

                try:
                    self.view_manager.log(f"[Agent] Executing {name} with args: {args}")
                    result = dispatch.execute_tool(self.view_manager, name, args)
                    self.view_manager.log(f"[Agent] {name} returned: {result}")
                except (TypeError, ValueError, KeyError) as exc:
                    result = f"Tool error in {name}: {exc}"
                    self.view_manager.log(f"[Agent] {result}")

                messages.append(
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
        """Normalize history to user/assistant text messages only."""
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
        """Run the agent for an Agent Builder prompt."""
        system_content = context.strip() if context else ""
        if context is None:
            if self.mode == MODE_APP_CREATOR:
                from picoware.system.agent.context.app_creator import PROMPT, CONTEXT, WORKFLOW
                system_content = f"{PROMPT.decode()}\n\n{WORKFLOW.decode()}\n\n{CONTEXT.decode()}"
            elif self.mode == MODE_DEVICE_MANAGER:
                from picoware.system.agent.context.device_manager import PROMPT, CONTEXT, WORKFLOW
                system_content = f"{PROMPT.decode()}\n\n{WORKFLOW.decode()}\n\n{CONTEXT.decode()}"
        user_message = topic.strip()
        if not user_message:
            return "No message provided."

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self._sanitize_conversation(conversation))
        messages.append({"role": "user", "content": user_message})

        try:
            return self._run_loop(messages)
        except Exception as exc:
            return f"An error occurred during processing: {exc}"


    def run_payload(self, payload: dict) -> dict:
        """Run the agent with a JSON payload and return structured response."""
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

    