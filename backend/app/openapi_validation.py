"""Bounded, offline validation of the MVP's OpenAPI schema/reference subset."""
import math
import re
from typing import Any, NoReturn

from fastapi import HTTPException

MAX_DEPTH = 32
MAX_NODES = 10_000
MAX_REFERENCES = 128


def invalid(location: str, reason: str) -> NoReturn:
    raise HTTPException(status_code=422, detail=f"Invalid OpenAPI at {location}: {reason}")


def mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        invalid(location, "must be an object with string keys")
    return value


class DocumentValidator:
    """Resolve only typed component references, without IO or input mutation."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.nodes = 0
        self.references = 0

    def tick(self, depth: int, location: str) -> None:
        self.nodes += 1
        if depth > MAX_DEPTH or self.nodes > MAX_NODES:
            invalid(location, "document/schema validation limit exceeded")

    def target(self, reference: Any, kind: str | None, location: str) -> tuple[str, dict[str, Any]]:
        if not isinstance(reference, str):
            invalid(location, "reference must be a string")
        if not reference.startswith('#/'):
            invalid(location, "only local component references are supported")
        match = re.fullmatch(r'#/components/(schemas|requestBodies|responses)/([^/]+)', reference)
        if match is None or (kind is not None and match[1] != kind):
            invalid(location, "unsupported reference location or component type")
        token = match[2]
        if re.search(r'~(?![01])', token) or '%' in token:
            invalid(location, "unsupported or malformed JSON pointer escape")
        name = token.replace('~1', '/').replace('~0', '~')
        components = self.spec.get('components', {})
        definitions = components.get(match[1], {}) if isinstance(components, dict) else {}
        if not isinstance(definitions, dict):
            invalid(location, 'broken local reference: component definitions must be an object')
        if name not in definitions:
            invalid(location, "broken local reference: component does not exist")
        return reference, mapping(definitions[name], f'components.{match[1]} target')

    def check_tree(self, value: Any, location: str = 'document', depth: int = 0) -> None:
        """Check bounds and references even in otherwise unselected operations.

        Example/default/enum payloads are data, not reference objects.
        """
        self.tick(depth, location)
        if isinstance(value, dict):
            mapping(value, location)
            if '$ref' in value:
                self.target(value['$ref'], None, location)
                if set(value) != {'$ref'}:
                    invalid(location, "reference siblings are unsupported in the MVP")
            for key, child in value.items():
                if key not in {'example', 'examples', 'default', 'enum', 'const'} and not key.startswith('x-'):
                    self.check_tree(child, f'{location}.{key}', depth + 1)
        elif isinstance(value, list):
            for child in value:
                self.check_tree(child, location, depth + 1)

    def validate(self, value: Any, kind: str, location: str, depth: int = 0,
                 active: tuple[str, ...] = ()) -> dict[str, Any]:
        self.tick(depth, location)
        node = mapping(value, location)
        if '$ref' in node:
            reference, target = self.target(node['$ref'], kind, location)
            if set(node) != {'$ref'}:
                invalid(location, "reference siblings are unsupported in the MVP")
            if reference in active:
                invalid(location, "cyclic local reference")
            self.references += 1
            if self.references > MAX_REFERENCES:
                invalid(location, "reference expansion limit exceeded")
            return self.validate(target, kind, location, depth + 1, (*active, reference))
        if kind == 'schemas':
            self.schema(node, location, depth, active)
        elif kind == 'requestBodies':
            if 'description' in node and not isinstance(node['description'], str):
                invalid(location + '.description', 'must be a string')
            if 'required' in node and not isinstance(node['required'], bool):
                invalid(location + '.required', 'must be a boolean')
            schema = self.content(node.get('content'), location + '.content', depth, active, required=True)
            if schema is None or schema.get('type') != 'object':
                invalid(location + '.schema', 'JSON request body must have an object schema')
        elif kind == 'responses':
            if not isinstance(node.get('description'), str):
                invalid(location + '.description', 'response description must be a string')
            if 'content' in node:
                self.content(node['content'], location + '.content', depth, active, required=False)
        return node

    def content(self, value: Any, location: str, depth: int, active: tuple[str, ...],
                required: bool) -> dict[str, Any] | None:
        content = mapping(value, location)
        if required and 'application/json' not in content:
            invalid(location, 'request body requires application/json')
        result = None
        for media_type, media in content.items():
            if media_type.startswith('x-'):
                continue
            if media_type != 'application/json':
                invalid(location, 'only application/json content is supported')
            media = mapping(media, location + '.application/json')
            result = self.validate(media.get('schema'), 'schemas', location + '.schema', depth + 1, active)
        return result

    def schema(self, node: dict[str, Any], location: str, depth: int, active: tuple[str, ...]) -> None:
        unsupported = {'allOf', 'anyOf', 'oneOf', 'not', '$id', '$anchor', '$dynamicRef',
                       '$dynamicAnchor', '$recursiveRef', '$defs', 'if', 'then', 'else',
                       'patternProperties', 'prefixItems', 'contains', 'unevaluatedProperties'}
        if unsupported.intersection(node):
            invalid(location, 'unsupported schema composition or reference keyword')
        supported = {
            'type', 'title', 'description', 'format', 'nullable', 'default', 'example',
            'enum', 'properties', 'required', 'items', 'additionalProperties',
            'readOnly', 'writeOnly', 'deprecated', 'uniqueItems', 'minLength',
            'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',
            'minimum', 'maximum', 'multipleOf', 'exclusiveMinimum', 'exclusiveMaximum',
            'pattern',
        }
        if any(key not in supported and not key.startswith('x-') for key in node):
            invalid(location, 'unsupported schema keyword in the MVP subset')
        kind = node.get('type')
        if not isinstance(kind, str) or kind not in {'object', 'array', 'string', 'integer', 'number', 'boolean', 'null'}:
            invalid(location, 'schema requires a supported explicit type')
        if kind == 'null' and self.spec['openapi'].startswith('3.0.'):
            invalid(location, 'null schema type requires OpenAPI 3.1+; use nullable in 3.0')
        if 'nullable' in node and not isinstance(node['nullable'], bool):
            invalid(location, 'schema nullable must be a boolean')
        for field in ('title', 'description', 'format', 'pattern'):
            if field in node and not isinstance(node[field], str):
                invalid(location, f'schema {field} must be a string')
        for field in ('readOnly', 'writeOnly', 'deprecated', 'uniqueItems'):
            if field in node and not isinstance(node[field], bool):
                invalid(location, f'schema {field} must be a boolean')
        for field in ('minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties'):
            if field in node and (type(node[field]) is not int or node[field] < 0):
                invalid(location, f'schema {field} must be a nonnegative integer')
        for field in ('minimum', 'maximum', 'multipleOf', 'exclusiveMinimum', 'exclusiveMaximum'):
            if field not in node:
                continue
            value = node[field]
            if field.startswith('exclusive') and self.spec['openapi'].startswith('3.0.'):
                if not isinstance(value, bool):
                    invalid(location, f'schema {field} must be a boolean in OpenAPI 3.0')
            elif type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
                invalid(location, f'schema {field} must be a finite number')
            elif field == 'multipleOf' and value <= 0:
                invalid(location, 'schema multipleOf must be positive')
        if 'properties' in node:
            if kind != 'object':
                invalid(location, 'schema properties require object type')
            for name, child in mapping(node['properties'], location + '.properties').items():
                self.validate(child, 'schemas', location + '.properties.' + name, depth + 1, active)
        if 'required' in node:
            required = node['required']
            if kind != 'object' or not isinstance(required, list) or any(not isinstance(item, str) for item in required) or len(set(required)) != len(required):
                invalid(location, 'schema required must be a unique list of property names for an object')
        if kind == 'array':
            self.validate(node.get('items'), 'schemas', location + '.items', depth + 1, active)
        elif 'items' in node:
            invalid(location, 'schema items require array type')
        if 'additionalProperties' in node:
            if kind != 'object':
                invalid(location, 'schema additionalProperties require object type')
            additional = node['additionalProperties']
            if not isinstance(additional, bool):
                self.validate(additional, 'schemas', location + '.additionalProperties', depth + 1, active)
        if 'enum' in node and (not isinstance(node['enum'], list) or not node['enum']):
            invalid(location, 'schema enum must be a nonempty array')
