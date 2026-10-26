"""OpenAPI analysis for bounded static POST operations with JSON object bodies."""
import re
from typing import Any

from .models import AnalyzeResponse, Operation, TestPlan
from .openapi_validation import DocumentValidator, invalid, mapping

HTTP_METHODS = {'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'}
PATH_FIELDS = HTTP_METHODS | {'summary', 'description', 'servers', 'parameters'}


def parse_openapi(spec: dict[str, Any]) -> AnalyzeResponse:
    spec = mapping(spec, 'document')
    version = spec.get('openapi')
    if not isinstance(version, str) or not re.fullmatch(r'3\.\d+\.\d+', version):
        invalid('openapi', 'MVP requires an OpenAPI 3.x release version (for example 3.1.0)')
    info = mapping(spec.get('info'), 'info')
    for field in ('title', 'version'):
        if not isinstance(info.get(field), str) or not info[field].strip():
            invalid('info.' + field, 'must be a nonempty string')
    paths = mapping(spec.get('paths'), 'paths')
    if not paths:
        invalid('paths', 'must contain at least one POST operation')
    validator = DocumentValidator(spec)
    validator.check_tree(spec)
    components = mapping(spec.get('components', {}), 'components')
    # Validate unused definitions too, so dangling/cyclic references cannot hide there.
    for kind in ('schemas', 'requestBodies', 'responses'):
        for name, definition in mapping(components.get(kind, {}), 'components.' + kind).items():
            validator.validate(definition, kind, 'components.' + kind + '.' + name)
    operations: list[Operation] = []
    for path, path_item in paths.items():
        if path.startswith('x-'):
            continue
        # Match the existing TestCase path contract; templates/queries are unsupported.
        if not re.fullmatch(r'/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?', path):
            invalid('paths', 'malformed or unsupported static path')
        location = 'paths.' + path
        path_item = mapping(path_item, location)
        for field, value in path_item.items():
            if field not in PATH_FIELDS and not field.startswith('x-'):
                invalid(location, 'unsupported path item field (references are not supported here)')
            if field in HTTP_METHODS:
                mapping(value, location + '.' + field)
            elif field in {'summary', 'description'} and not isinstance(value, str):
                invalid(location + '.' + field, 'must be a string')
        if 'parameters' in path_item and path_item['parameters'] != []:
            invalid(location + '.parameters', 'parameters are unsupported for static MVP operations')
        if 'post' not in path_item:
            continue
        operation = path_item['post']
        for field in ('summary', 'description', 'operationId'):
            if field in operation and not isinstance(operation[field], str):
                invalid(location + '.post.' + field, 'must be a string')
        if 'parameters' in operation and operation['parameters'] != []:
            invalid(location + '.post.parameters', 'parameters are unsupported for static MVP operations')
        # RequestBody must be declared by this operation; metadata never creates an endpoint.
        validator.validate(operation.get('requestBody'), 'requestBodies', location + '.post.requestBody')
        responses = mapping(operation.get('responses'), location + '.post.responses')
        if not responses or not any(not code.startswith('x-') for code in responses):
            invalid(location + '.post.responses', 'at least one response declaration is required')
        for code, response in responses.items():
            if code.startswith('x-'):
                continue
            if code != 'default' and not re.fullmatch(r'[1-5](?:\d{2}|XX)', code):
                invalid(location + '.post.responses', 'invalid response status key')
            validator.validate(response, 'responses', location + '.post.responses.' + code)
        operations.append(Operation(method='POST', path=path))
    if not operations:
        invalid('paths', 'MVP requires at least one supported POST operation')
    return AnalyzeResponse(title=info['title'], operations=operations)


def validate_plan_against_spec(plan: TestPlan, spec: dict[str, Any]) -> None:
    operations = parse_openapi(spec).operations
    permitted = {(op.method, op.path) for op in operations}
    if any((case.method, case.path) not in permitted for case in plan.cases):
        invalid('plan', 'Generated plan includes an undeclared operation')
