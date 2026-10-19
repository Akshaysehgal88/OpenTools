"""Small shared JSON/path primitives for the portable integration layer."""
import hashlib
import json
from pathlib import Path


class InputError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InputError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pairs(items):
    result = {}
    for name, value in items:
        require(name not in result, f"Duplicate JSON key: {name}")
        result[name] = value
    return result


def parse_json(data):
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(InputError(f"Invalid JSON number: {value}")))


def read_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def shape(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value) <= set(required) | set(optional),
            f"Expected fields {sorted(required)}, optional {sorted(optional)}")


def inside(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    return path != parent and parent in path.parents


def relative_file(root, value):
    require(text(value), "Relative file path required")
    relative = Path(value)
    require("\\" not in value and ":" not in value and not relative.is_absolute() and not relative.drive and ".." not in relative.parts,
            "Path must stay inside its package")
    path = Path(root) / relative
    require(inside(path, root) and path.is_file() and not path.is_symlink(), "Expected a package-owned regular file")
    return path
