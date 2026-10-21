"""Positive prerequisite closure for a declared clock-transition abstraction."""
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON value")))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " required")


def closure(initial, rules):
    known = set(initial)
    while True:
        added = {r["produces"] for r in rules if set(r["requires"]) <= known} - known
        if not added:
            return known
        known |= added


def cycles(graph):
    """Small bounded graph SCCs; edges are prerequisite candidates, not a temporal proof."""
    index, stack, active, indices, low, result = 0, [], set(), {}, {}, []
    def visit(node):
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        active.add(node)
        for other in sorted(graph[node]):
            if other not in indices:
                visit(other)
                low[node] = min(low[node], low[other])
            elif other in active:
                low[node] = min(low[node], indices[other])
        if low[node] == indices[node]:
            group = []
            while True:
                item = stack.pop()
                active.remove(item)
                group.append(item)
                if item == node:
                    break
            if len(group) > 1 or node in graph[node]:
                result.append(sorted(group))
    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(result)


def analyze(model, request):
    for record, kind in ((model, "model"), (request, "request")):
        require(isinstance(record, dict) and record.get("format") == "opentools.clock." + kind + ".v1", "Unsupported " + kind + " format")
        require(isinstance(record.get("scope"), dict) and set(record["scope"]) == {"project", "configuration", "mode"}, "Exact scope fields required")
        for value in record["scope"].values():
            text(value, "scope")
        text(record.get("basis_ref"), "basis_ref")
        require(type(record.get("inputs_complete")) is bool, "inputs_complete must be boolean")
    require(model.get("semantics") == "positive-monotonic-prerequisites", "Unsupported model semantics")
    report = {"format": "opentools.clock.report.v1", "scope": model["scope"],
              "bindings": {"model_sha256": digest(model), "request_sha256": digest(request)},
              "findings": [], "gaps": [], "goals": [], "candidate_cycles": [], "derivable_facts": [],
              "limits": ["Static positive availability abstraction; no timing, deassertion, fairness, pulse, glitch or deadlock proof.",
                         "Bounded native progress observations and source applicability require separate review. Hashes do not establish semantic roles or completeness."]}
    def gap(kind, **details):
        report["gaps"].append(dict(kind=kind, **details))
    for record, name in ((model, "model"), (request, "request")):
        if not record["inputs_complete"]:
            gap("partial_inputs", record=name)
    if request["scope"] != model["scope"] or request["basis_ref"] != model["basis_ref"] or request.get("model_sha256") != digest(model):
        gap("scope_or_model_binding")
        report["status"] = "incomplete"
        return report
    facts, clocks, rules = {}, {}, []
    require(isinstance(model.get("facts"), list) and 0 < len(model["facts"]) <= 256, "Select 1 to 256 facts")
    for fact in model["facts"]:
        text(fact.get("id"), "fact id")
        require(fact["id"] not in facts, "Duplicate fact")
        require(type(fact.get("initial")) is bool or fact.get("initial") is None, "Initial fact must be boolean or null")
        text(fact.get("evidence_ref"), "fact evidence")
        if fact.get("owner_ref") is None:
            gap("owner_unresolved", fact=fact["id"])
        else:
            text(fact["owner_ref"], "fact owner")
        facts[fact["id"]] = fact
    require(isinstance(model.get("clocks"), list) and model["clocks"], "Explicit clock lineage required")
    for clock in model["clocks"]:
        text(clock.get("id"), "clock id")
        require(clock["id"] not in clocks, "Duplicate clock")
        text(clock.get("evidence_ref"), "clock evidence")
        text(clock.get("available_fact"), "clock availability fact")
        require("parent_ref" in clock, "Explicit parent_ref required; null denotes a root")
        if clock.get("owner_ref") is None:
            gap("clock_owner_unresolved", clock=clock["id"])
        else:
            text(clock["owner_ref"], "clock owner")
        if clock.get("parent_ref") is not None:
            text(clock["parent_ref"], "parent clock")
        clocks[clock["id"]] = clock
    invalid_lineage = False
    def clock_requirements(clock_id):
        nonlocal invalid_lineage
        requirements, seen = set(), set()
        while clock_id is not None:
            if clock_id in seen or clock_id not in clocks:
                gap("clock_lineage_unresolved", clock=clock_id)
                invalid_lineage = True
                break
            seen.add(clock_id)
            clock = clocks[clock_id]
            requirements.add(clock["available_fact"])
            clock_id = clock.get("parent_ref")
        return requirements
    for clock_id in clocks:
        for fact in clock_requirements(clock_id):
            if fact not in facts:
                gap("clock_availability_fact_absent", clock=clock_id, fact=fact)
                invalid_lineage = True
    require(isinstance(model.get("rules"), list), "Rules required")
    names = set()
    for rule in model["rules"]:
        text(rule.get("id"), "rule id")
        require(rule["id"] not in names, "Duplicate rule")
        names.add(rule["id"])
        text(rule.get("produces"), "produced fact")
        text(rule.get("evidence_ref"), "rule evidence")
        require(isinstance(rule.get("requires"), list) and all(isinstance(v, str) and v.strip() for v in rule["requires"]), "Text prerequisite list required")
        require(len(rule["requires"]) == len(set(rule["requires"])), "Duplicate prerequisite")
        dependencies = set(rule["requires"])
        require("clock_ref" in rule, "Explicit clock_ref required; null denotes a declared non-clocked rule")
        if rule.get("clock_ref") is not None:
            dependencies |= clock_requirements(rule["clock_ref"])
        absent = ({rule["produces"]} | dependencies) - facts.keys()
        if absent:
            gap("rule_fact_absent", rule=rule["id"], facts=sorted(absent))
            invalid_lineage = True
        rules.append(dict(rule, requires=sorted(dependencies)))
    require(isinstance(request.get("goals"), list) and request["goals"], "Requested goals required")
    goal_ids = set()
    for goal in request["goals"]:
        text(goal.get("fact_ref"), "goal fact")
        text(goal.get("evidence_ref"), "goal evidence")
        require(goal["fact_ref"] not in goal_ids, "Duplicate goal")
        goal_ids.add(goal["fact_ref"])
        if goal["fact_ref"] not in facts:
            gap("goal_fact_absent", fact=goal["fact_ref"])
    if not invalid_lineage:
        definite = closure([f for f in facts if facts[f]["initial"] is True], rules)
        possible = closure([f for f in facts if facts[f]["initial"] is not False], rules)
        report["derivable_facts"] = sorted(definite)
        graph = {f: set() for f in facts if f not in definite}
        for rule in rules:
            if rule["produces"] in graph:
                graph[rule["produces"]] |= set(rule["requires"]) & graph.keys()
        report["candidate_cycles"] = [{"facts": group, "source_rules": [r["id"] for r in rules if r["produces"] in group and set(r["requires"]) & set(group)]} for group in cycles(graph)]
        complete = model["inputs_complete"] and request["inputs_complete"] and not report["gaps"]
        for goal in request["goals"]:
            fact = goal["fact_ref"]
            if fact not in facts:
                continue
            state = "derivable_in_declared_model" if fact in definite else "depends_on_unknown_initial_facts" if fact in possible else "unreachable_in_declared_model" if complete else "unresolved_with_partial_evidence"
            report["goals"].append({"fact_ref": fact, "state": state, "evidence_ref": goal["evidence_ref"]})
            if state == "unreachable_in_declared_model":
                report["findings"].append({"kind": "goal_unreachable_in_declared_model", "fact_ref": fact, "evidence_ref": goal["evidence_ref"]})
            elif state != "derivable_in_declared_model":
                gap("goal_prerequisites_unresolved", fact=fact)
        report["unprovided_prerequisites"] = sorted(f for f in graph if not any(r["produces"] == f for r in rules) and facts[f]["initial"] is False)
        report["expanded_rules"] = rules
    report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "derivable_within_declared_model"
    return report


def exit_code(report):
    return {"derivable_within_declared_model": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Clock prerequisite review", "", "Status: " + report["status"], ""]
    for key in ("goals", "candidate_cycles", "findings", "gaps"):
        lines += [key.replace("_", " ").capitalize() + ":", ""]
        lines += ["- " + json.dumps(item, ensure_ascii=False) for item in report[key]] or ["- None"]
        lines += [""]
    return "\n".join(lines + report["limits"]) + "\n"
