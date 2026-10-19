"""Compare explicit binary record layouts without parsing either source language."""
from __future__ import annotations
import json
from pathlib import Path


class InputError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InputError(message)


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, f"Duplicate JSON key: {k}")
        result[k] = v
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(InputError(f"Invalid number: {x}")))


def text(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def power2(value):
    return integer(value, 1) and value & (value - 1) == 0


def fields(layout):
    require(isinstance(layout, dict) and layout.get("format") == "opentools.record-layout.v1", "Unsupported layout format")
    require(layout.get("kind") in ("hardware", "software"), "Unknown layout kind")
    for key in ("record", "interface_ref", "configuration_ref", "source_ref", "frontend_ref"):
        require(text(layout.get(key)), f"Missing {key}")
    require(type(layout.get("inputs_complete")) is bool and type(layout.get("fields_complete")) is bool, "Completeness declarations must be boolean")
    require(integer(layout.get("size_bits"), 8) and layout["size_bits"] % 8 == 0, "Record size must be a positive whole number of bytes")
    if layout["kind"] == "software":
        require(layout.get("basis") == "c-object" and text(layout.get("target_abi")), "Software requires c-object basis and target_abi")
        require(layout.get("integer_representation") == "binary-twos-complement", "Software must declare binary integers without padding and two's-complement signed representation")
        require(layout.get("byte_order") in ("little", "big"), "Software byte order is required")
        require(power2(layout.get("alignment_bytes")), "Software alignment must be a positive power of two")
    else:
        require(layout.get("basis") == "packed-lsb", "Hardware requires packed-lsb basis")
    require(isinstance(layout.get("fields"), list) and layout["fields"], "Nonempty fields are required")
    result, occupied = {}, set()
    for f in layout["fields"]:
        require(isinstance(f, dict) and text(f.get("name")) and f["name"] not in result, "Field names must be unique and nonempty")
        require(set(f) <= {"name", "offset_bits", "width_bits", "signed", "enum_values", "evidence_ref"}, "Unsupported field property")
        require(integer(f.get("offset_bits")) and f["offset_bits"] % 8 == 0, "Only byte-aligned fields are supported")
        require(integer(f.get("width_bits"), 8) and f["width_bits"] <= 64 and f["width_bits"] % 8 == 0, "Only byte-wide scalar fields up to 64 bits are supported")
        require(f["offset_bits"] + f["width_bits"] <= layout["size_bits"], "Field exceeds record")
        require(type(f.get("signed")) is bool and text(f.get("evidence_ref")), "Field requires signedness and evidence")
        values = f.get("enum_values")
        require(isinstance(values, dict) and all(text(k) and type(v) is int for k, v in values.items()), "enum_values must map names to integers")
        low = -(1 << (f["width_bits"] - 1)) if f["signed"] else 0
        high = (1 << (f["width_bits"] - int(f["signed"]))) - 1
        require(all(low <= v <= high for v in values.values()), "Encoding does not fit field")
        bits = set(range(f["offset_bits"], f["offset_bits"] + f["width_bits"]))
        require(not occupied & bits, "Overlapping fields are unsupported")
        occupied |= bits
        result[f["name"]] = f
    if layout["kind"] == "hardware" and layout["fields_complete"]:
        require(len(occupied) == layout["size_bits"], "A complete packed record must account for every bit")
    return result


def padding(layout):
    if not layout["fields_complete"]:
        return None
    intervals, offset = [], 0
    for f in sorted(layout["fields"], key=lambda f: f["offset_bits"]):
        if offset < f["offset_bits"]:
            intervals.append({"offset_bits": offset, "width_bits": f["offset_bits"] - offset})
        offset = f["offset_bits"] + f["width_bits"]
    if offset < layout["size_bits"]:
        intervals.append({"offset_bits": offset, "width_bits": layout["size_bits"] - offset})
    return intervals


def bit_map(layout, field, hardware_order):
    """Return address-byte / LSB-numbered bit for each scalar value bit."""
    offset, width = field["offset_bits"], field["width_bits"]
    if layout["kind"] == "hardware":
        return [((offset + k) // 8 if hardware_order == "little" else layout["size_bits"] // 8 - 1 - (offset + k) // 8,
                 (offset + k) % 8) for k in range(width)]
    return [(offset // 8 + (k // 8 if layout["byte_order"] == "little" else width // 8 - 1 - k // 8), k % 8) for k in range(width)]


def compare(hardware, software, policy):
    h, s = fields(hardware), fields(software)
    require(hardware["kind"] == "hardware" and software["kind"] == "software", "Expected hardware then software layout")
    require(isinstance(policy, dict) and policy.get("format") == "opentools.layout-pair.v1", "Unsupported pairing format")
    require(set(policy) <= {"format", "interface_ref", "hardware_configuration_ref", "software_configuration_ref", "representation", "hardware_byte_order", "required_alignment_bytes", "evidence_ref", "fields"}, "Unsupported pairing property")
    for key in ("interface_ref", "hardware_configuration_ref", "software_configuration_ref", "representation", "evidence_ref"):
        require(text(policy.get(key)), f"Pairing requires {key}")
    issues, mismatches, rows = [], [], []
    if policy["representation"] != "direct-object-copy":
        issues.append("Explicit serialization is outside this profile; C object placement is not a wire-layout verdict")
    else:
        require(policy.get("hardware_byte_order") in ("little", "big"), "Declare packed-vector byte order")
        require(power2(policy.get("required_alignment_bytes")), "Boundary alignment must be a positive power of two")
    for side, layout in (("hardware", hardware), ("software", software)):
        if layout["interface_ref"] != policy["interface_ref"]:
            issues.append(f"{side} interface revision differs from pairing")
        if layout["configuration_ref"] != policy[f"{side}_configuration_ref"]:
            issues.append(f"{side} configuration differs from pairing")
        if not layout["inputs_complete"] or not layout["fields_complete"]:
            issues.append(f"{side} inputs or field inventory are incomplete")

    def mismatch(prop, a, b, field=None, evidence=None):
        mismatches.append({"property": prop, "hardware": a, "software": b, "field": field,
                           "evidence": evidence or [hardware["source_ref"], software["source_ref"], policy["evidence_ref"]]})

    if policy["representation"] == "direct-object-copy":
        if hardware["size_bits"] != software["size_bits"]:
            mismatch("record_size_bits", hardware["size_bits"], software["size_bits"])
        if policy["required_alignment_bytes"] < software["alignment_bytes"]:
            mismatch("insufficient_boundary_alignment", policy["required_alignment_bytes"], software["alignment_bytes"])
        require(isinstance(policy.get("fields"), list), "Pairing fields must be a list")
        seen_h, seen_s = set(), set()
        for pair in policy["fields"]:
            require(isinstance(pair, dict) and set(pair) <= {"hardware", "software", "encodings"}, "Invalid field pairing")
            hn, sn = pair.get("hardware"), pair.get("software")
            require(text(hn) and text(sn), "Pairing names are required")
            require(hn not in seen_h and sn not in seen_s, "Field pairing must be one-to-one")
            seen_h.add(hn); seen_s.add(sn)
            if hn not in h or sn not in s:
                issues.append(f"Paired field absent: {hn} / {sn}")
                continue
            a, b = h[hn], s[sn]
            evidence = [a["evidence_ref"], b["evidence_ref"], policy["evidence_ref"]]
            am, bm = bit_map(hardware, a, policy["hardware_byte_order"]), bit_map(software, b, policy["hardware_byte_order"])
            rows.append({"hardware_field": hn, "software_field": sn,
                         "hardware": {**a, "value_bit_0_address": list(am[0]), "lowest_address_byte": min(x[0] for x in am)},
                         "software": {**b, "value_bit_0_address": list(bm[0]), "lowest_address_byte": min(x[0] for x in bm)}})
            for prop in ("width_bits", "signed"):
                if a[prop] != b[prop]:
                    mismatch(prop, a[prop], b[prop], hn, evidence)
            if am != bm:
                mismatch("value_bit_address_mapping", am, bm, hn, evidence)
            encodings = pair.get("encodings", [])
            require(isinstance(encodings, list), "encodings must be a list")
            eh, es = set(), set()
            for encoding in encodings:
                require(isinstance(encoding, dict) and set(encoding) <= {"hardware", "software"}, "Invalid encoding correspondence")
                x, y = encoding.get("hardware"), encoding.get("software")
                require(text(x) and text(y) and x not in eh and y not in es, "Encoding correspondence must be one-to-one")
                eh.add(x); es.add(y)
                if x not in a["enum_values"] or y not in b["enum_values"]:
                    issues.append(f"Encoding absent: {hn}.{x} / {sn}.{y}")
                elif a["enum_values"][x] != b["enum_values"][y]:
                    mismatch("encoding_value", {x: a["enum_values"][x]}, {y: b["enum_values"][y]}, hn, evidence)
            if eh != a["enum_values"].keys() or es != b["enum_values"].keys():
                issues.append(f"Unpaired declared encodings: {hn} / {sn}")
        if seen_h != h.keys() or seen_s != s.keys():
            issues.append("Every exported field must be explicitly paired")
    return {"format": "opentools.layout-audit.v1", "status": "incomplete" if issues else "mismatch" if mismatches else "matched_within_scope",
            "mismatch_found": bool(mismatches), "issues": issues, "mismatches": mismatches, "fields": rows,
            "inputs": {"hardware": hardware, "software": software, "pairing": policy},
            "padding": {"hardware": padding(hardware), "software": padding(software)},
            "limits": ["Direct object representation only; arbitrary serializers are not interpreted.",
                       "C encoding vocabulary is explicitly supplied, not an exhaustive enumeration by the compiler probe.",
                       "A layout match does not prove transaction behavior, X/Z conversion, coherency or ownership correctness."]}


def markdown(report):
    cell = lambda v: str(v).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = ["# Descriptor layout check", "", f"Status: **{report['status']}**", "",
             "Positions below are lowest byte addresses; numeric bit mapping is checked separately.", "",
             "| Hardware field | Software field | HW byte | C byte | HW width | C width | HW signed | C signed |",
             "|---|---|---:|---:|---:|---:|---|---|"]
    for row in report["fields"]:
        a, b = row["hardware"], row["software"]
        lines.append("| " + " | ".join(cell(v) for v in (row["hardware_field"], row["software_field"], a["lowest_address_byte"], b["lowest_address_byte"], a["width_bits"], b["width_bits"], a["signed"], b["signed"])) + " |")
    lines += ["", "## Mismatches", ""]
    for m in report["mismatches"]:
        a, b = m["hardware"], m["software"]
        if m["property"] == "value_bit_address_mapping":
            differences = [(k, x, y) for k, (x, y) in enumerate(zip(a, b)) if x != y]
            detail = f"first differing value bit / HW address / C address: {differences[0]}" if differences else f"different mapping lengths: {len(a)} / {len(b)}"
        else:
            detail = f"HW {json.dumps(a)}; C {json.dumps(b)}"
        lines.append(f"- {cell(m['field'] or 'record')}: {cell(m['property'])}; {cell(detail)}; evidence: {cell('; '.join(m['evidence']))}")
    if not report["mismatches"]: lines.append("None observed within scope.")
    lines += ["", "## Padding", "", f"`{cell(json.dumps(report['padding']))}`", "", "## Evidence limits", ""]
    lines += [f"- {cell(v)}" for v in report["issues"] + report["limits"]]
    return "\n".join(lines) + "\n"
