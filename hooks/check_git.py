import json
import re
import sys

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

patterns = [
    r"\bgit\s+push\b[^\r\n]*\s--force\b",
    r"\bgit\s+push\b[^\r\n]*\s-f(?:\s|$)",
    r"\bgit\b[^\r\n]*\breset\s+--hard\b",
]

if any(re.search(p, command, re.IGNORECASE) for p in patterns):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "BL-02: Небезпечна Git-команда заблокована."
        }
    }))
else:
    print("{}")
