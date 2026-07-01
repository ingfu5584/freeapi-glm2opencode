import json
import re
import time
import uuid


def generate_id(prefix: str = "chatcmpl") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def format_tools_as_prompt(tools: list) -> str:
    if not tools:
        return ""

    lines = [
        "【重要规则】你是一个工具调用助手。你必须使用提供的工具来完成任务，不要自己编造答案。",
        "",
        "当需要执行操作时，你必须严格按照以下格式输出工具调用：",
        "",
        "```tool_call",
        '{"name": "工具名称", "arguments": {"参数名": "参数值"}}',
        "```",
        "",
        "可用工具列表：",
    ]

    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "")
        desc = func.get("description", "")
        params = func.get("parameters", {})
        lines.append(f"### {name}")
        lines.append(f"   描述: {desc}")
        if params:
            props = params.get("properties", {})
            required = params.get("required", [])
            for pname, pinfo in props.items():
                req = " (必填)" if pname in required else " (可选)"
                lines.append(f"   参数 {pname}: {pinfo.get('description', '')}{req}")
        lines.append("")

    lines.append("示例：")
    lines.append("用户: 帮我查看当前目录")
    lines.append("助手:")
    lines.append("```tool_call")
    lines.append('{"name": "bash", "arguments": {"command": "ls -la"}}')
    lines.append("```")
    lines.append("")
    lines.append("现在请根据用户请求，输出工具调用格式。")

    return "\n".join(lines)

    return "\n".join(lines)


def openai_to_zhipu_messages(openai_messages: list, tools: list = None) -> list:
    zhipu_messages = []

    tool_prompt = format_tools_as_prompt(tools) if tools else ""
    if tool_prompt:
        zhipu_messages.append({"role": "system", "content": tool_prompt})

    for msg in openai_messages:
        role = msg.get("role", "user")
        if role == "system":
            zhipu_messages.append({"role": "system", "content": msg["content"]})
        elif role == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part["text"])
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)
            zhipu_messages.append({"role": "user", "content": content})
        elif role == "assistant":
            content = msg.get("content", "")
            if content:
                zhipu_messages.append({"role": "assistant", "content": content})
        elif role == "tool":
            content = msg.get("content", "")
            tool_call_id = msg.get("tool_call_id", "")
            zhipu_messages.append({
                "role": "user",
                "content": f"[工具调用结果 (ID: {tool_call_id})]\n{content}"
            })

    return zhipu_messages


def _find_json_tool_calls(text: str) -> list:
    """用大括号计数法找到所有裸 JSON 工具调用"""
    results = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            depth = 0
            for j in range(i, len(text)):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(text[i:j + 1])
                            if "name" in data and "arguments" in data:
                                results.append((i, j + 1, data))
                                i = j + 1
                        except:
                            pass
                        break
        i += 1
    return results


def _parse_simple_tool_call(line: str) -> dict:
    """解析 tool_call 工具名称 参数 格式"""
    line = line.strip()
    if not line.startswith("tool_call "):
        return None

    parts = line[len("tool_call "):].strip().split(None, 1)
    if not parts:
        return None

    name = parts[0]
    args = {}

    if len(parts) > 1:
        arg_str = parts[1]
        for match in re.finditer(r'(\w+)="([^"]*)"', arg_str):
            args[match.group(1)] = match.group(2)
        for match in re.finditer(r"(\w+)='([^']*)'", arg_str):
            if match.group(1) not in args:
                args[match.group(1)] = match.group(2)

    return {"name": name, "arguments": args}


def parse_tool_calls(text: str) -> list:
    tool_calls = []

    # 格式1: ```tool_call ... ```
    pattern = r'```tool_call\s*\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match.strip())
            tool_calls.append({
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {
                    "name": data.get("name", ""),
                    "arguments": json.dumps(data.get("arguments", {}), ensure_ascii=False),
                },
            })
        except json.JSONDecodeError:
            parsed = _parse_simple_tool_call(match.strip())
            if parsed:
                tool_calls.append({
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                    "type": "function",
                    "function": {
                        "name": parsed["name"],
                        "arguments": json.dumps(parsed["arguments"], ensure_ascii=False),
                    },
                })

    # 格式2: tool_call 工具名称 参数（独占一行）
    if not tool_calls:
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("tool_call "):
                parsed = _parse_simple_tool_call(line)
                if parsed:
                    tool_calls.append({
                        "id": f"call_{uuid.uuid4().hex[:12]}",
                        "type": "function",
                        "function": {
                            "name": parsed["name"],
                            "arguments": json.dumps(parsed["arguments"], ensure_ascii=False),
                        },
                    })

    # 格式3: 裸 JSON
    if not tool_calls:
        found = _find_json_tool_calls(text)
        for start, end, data in found:
            tool_calls.append({
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {
                    "name": data["name"],
                    "arguments": json.dumps(data["arguments"], ensure_ascii=False),
                },
            })

    return tool_calls


def clean_response_text(text: str) -> str:
    # 清理 ```tool_call 块
    cleaned = re.sub(r'```tool_call\s*\n.*?\n```', '', text, flags=re.DOTALL)

    # 清理 tool_call 行
    lines = cleaned.split("\n")
    cleaned_lines = [l for l in lines if not l.strip().startswith("tool_call ")]
    cleaned = "\n".join(cleaned_lines)

    # 清理裸 JSON
    found = _find_json_tool_calls(cleaned)
    for start, end, data in reversed(found):
        cleaned = cleaned[:start] + cleaned[end:]

    return cleaned.strip()


def zhipu_to_openai_response(zhipu_data: dict, model: str = "glm-4", tools: list = None) -> dict:
    result = zhipu_data.get("result", {})
    if isinstance(result, str):
        content = result
    elif isinstance(result, dict):
        content = result.get("content", str(result))
    else:
        content = str(result)

    tool_calls = parse_tool_calls(content)
    clean_content = clean_response_text(content)

    message = {"role": "assistant"}
    if tool_calls:
        message["tool_calls"] = tool_calls
    else:
        message["content"] = clean_content

    response = {
        "id": generate_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": f"fp_{uuid.uuid4().hex[:12]}",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

    return response


TOOL_CALL_MARKERS = [
    '```tool_call',
    'tool_call ',
    'tool_call\n',
]


def detect_tool_call_start(text: str) -> int:
    """检测text中是否包含tool_call起始标记，返回起始位置，未找到返回-1"""
    earliest = -1
    for marker in TOOL_CALL_MARKERS:
        idx = text.find(marker)
        if idx >= 0:
            if earliest < 0 or idx < earliest:
                earliest = idx
    return earliest


def extract_safe_content(full_text: str, new_text: str) -> tuple:
    """
    从累积文本和新增量文本中提取安全的content内容。
    返回 (safe_content, is_in_tool_call_mode)
    如果检测到tool_call标记，返回标记之前的安全内容和True。
    """
    combined = full_text + new_text
    marker_pos = detect_tool_call_start(combined)
    if marker_pos >= 0:
        safe_part = combined[:marker_pos]
        already_sent = full_text[:marker_pos] if marker_pos <= len(full_text) else full_text
        new_safe = safe_part[len(already_sent):]
        return new_safe, True
    return new_text, False


def safe_send_length(full_text: str) -> tuple:
    """
    返回 (safe_len, in_tool_call_mode)。
    safe_len: 可以安全发送的字符数。
    如果检测到完整marker，返回marker位置和True。
    如果末尾可能是marker前缀，hold back并返回False。
    """
    marker_pos = detect_tool_call_start(full_text)
    if marker_pos >= 0:
        return marker_pos, True

    max_holdback = 0
    for marker in TOOL_CALL_MARKERS:
        for length in range(1, min(len(marker), len(full_text)) + 1):
            if full_text.endswith(marker[:length]):
                if length > max_holdback:
                    max_holdback = length

    if max_holdback > 0:
        return len(full_text) - max_holdback, False

    return len(full_text), False


def zhipu_to_openai_stream_chunk(chunk: dict, model: str, stream_id: str, created_time: int) -> dict:
    if chunk.get("done"):
        return None

    result = chunk.get("result", {})
    if isinstance(result, str):
        content = result
    elif isinstance(result, dict):
        content = result.get("content", "")
    else:
        content = str(result)

    delta = {}
    if content:
        delta = {"content": content}

    return {
        "id": stream_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": model,
        "system_fingerprint": f"fp_{uuid.uuid4().hex[:12]}",
        "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
    }


def create_stream_end_chunk(model: str, stream_id: str, created_time: int, tool_calls: list = None) -> dict:
    chunk = {
        "id": stream_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": model,
        "system_fingerprint": f"fp_{uuid.uuid4().hex[:12]}",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    if tool_calls:
        chunk["choices"][0]["finish_reason"] = "tool_calls"
        chunk["choices"][0]["delta"]["tool_calls"] = tool_calls
    return chunk
