#!/usr/bin/env python3
"""Synthetic context-provider example. This is not a DVIT implementation."""
import json
import sys


def main():
    request = json.load(sys.stdin)
    discovery = request["action"] == "capabilities"
    reply = {
        "format": "opentools.context-reply.v1", "protocol": "opentools.context.v1",
        "request_id": request["request_id"],
        "source": {"id": request["source_id"], "type": request["source_type"], "version": "synthetic-demo-1"},
        "status": "ok", "scope": request["scope"],
        "capabilities": [
            {"id": "context", "kind": "context", "description": "Synthetic engineering guidance, not project facts"},
            {"id": "explain-gap", "kind": "helper", "description": "Suggest what original evidence could settle a gap"}
        ],
        "observations": [] if discovery else [{"id": "review-basis", "text": "Inspect original run inputs and checker scope before reusing a result.",
            "status": "proposal", "source_ref": "synthetic:demo-guidance", "revision_ref": "demo-1"}],
        "questions": [] if discovery else [{"id": "checker-scope", "text": "Which original checker and configuration produced the selected result?",
            "reason": "A tool completion and the requested functional claim can concern different checks."}],
        "seeds": [{"id": "keep-origin", "description": "Illustrative engineering review seed",
            "content": "Keep original observations, requested claims, missing provenance and proposed reuse separate. Use the engineer's existing tools when a bundled checker does not fit.",
            "source_ref": "synthetic:demo-guidance", "revision_ref": "demo-1"}],
        "helpers": [{"id": "gap-review", "description": "Ask explain-gap for illustrative review guidance; no installer or external package is invoked.",
            "capability_id": "explain-gap", "source_ref": "synthetic:demo-capabilities"}],
        "unknowns": []
    }
    print(json.dumps(reply, ensure_ascii=False))


if __name__ == "__main__":
    main()
