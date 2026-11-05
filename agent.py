"""Primary AI agent: Gemini LLM + function calling over RAG, MCP and memory tools."""
import asyncio, json, os, sys
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import config, memory, rag
from prompts import SYSTEM_PROMPT

SERVER = StdioServerParameters(command=sys.executable, args=[os.path.join(config.BASE, "mcp_server.py")])


# ---------------- MCP client ----------------
async def _mcp_list():
    async with stdio_client(SERVER) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return (await s.list_tools()).tools


async def _mcp_call(name, args):
    async with stdio_client(SERVER) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(name, args)
            return "".join(c.text for c in res.content if getattr(c, "text", None))


def run_async(coro):
    return asyncio.run(coro)


_MCP_TOOLS = None
def mcp_tools():
    global _MCP_TOOLS
    if _MCP_TOOLS is None:
        _MCP_TOOLS = run_async(_mcp_list())
    return _MCP_TOOLS


LOCAL_DECLS = [
    types.FunctionDeclaration(
        name="search_regulations",
        description="RAG search over university regulations/policy documents. Returns cited passages.",
        parameters_json_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
    types.FunctionDeclaration(
        name="save_student_memory",
        description="Save a lasting academic preference/goal/constraint of the student to long-term memory.",
        parameters_json_schema={"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]}),
]


class AdvisorAgent:
    def __init__(self, student_id):
        self.student_id = student_id
        self.client = genai.Client(api_key=config.API_KEY)
        self.history = []  # short-term memory: session conversation

    def _config(self):
        mem = memory.recall(self.student_id)
        prompt = SYSTEM_PROMPT + f"\n# CURRENT STUDENT\nstudent_id = {self.student_id} (use it for MCP tool calls)\n" \
                 + "\n# KNOWN STUDENT MEMORY\n" + ("\n".join(f"- {m}" for m in mem) if mem else "(none yet)")
        decls = LOCAL_DECLS + [types.FunctionDeclaration(name=t.name, description=t.description,
                               parameters_json_schema=t.inputSchema) for t in mcp_tools()]
        return types.GenerateContentConfig(
            system_instruction=prompt, tools=[types.Tool(function_declarations=decls)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))

    def _run_tool(self, name, args):
        try:
            if name == "search_regulations":
                hits = rag.search(args["query"])
                return "\n\n".join(f"[{h['source']}] (score {h['score']})\n{h['text']}" for h in hits)
            if name == "save_student_memory":
                return "saved" if memory.save(self.student_id, args["fact"]) else "already known"
            return run_async(_mcp_call(name, args))
        except Exception as e:  # graceful failure -> LLM explains to the user
            return f"ERROR: tool '{name}' failed: {e}"

    def chat(self, user_msg):
        """Returns (reply_text, trace) where trace lists every tool call + result."""
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_msg)]))
        cfg, trace = self._config(), []
        for _ in range(8):
            resp = self.client.models.generate_content(model=config.CHAT_MODEL, contents=self.history, config=cfg)
            content = resp.candidates[0].content
            self.history.append(content)
            if not resp.function_calls:
                return resp.text or "(no response)", trace
            parts = []
            for fc in resp.function_calls:
                args = dict(fc.args or {})
                result = self._run_tool(fc.name, args)
                kind = "RAG" if fc.name == "search_regulations" else "MEMORY" if fc.name == "save_student_memory" else "MCP"
                trace.append({"tool": fc.name, "kind": kind, "args": args, "result": result})
                parts.append(types.Part.from_function_response(name=fc.name, response={"result": result}))
            self.history.append(types.Content(role="user", parts=parts))
        return "I could not finish this request; please rephrase.", trace
