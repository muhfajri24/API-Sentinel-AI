"""Validation tests for the supported OpenAPI POST/JSON subset; no network IO."""
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.openapi_parser import parse_openapi, validate_plan_against_spec
from backend.app.generator import fixture_plan


@pytest.fixture
def spec() -> dict[str, Any]:
    return json.loads((Path(__file__).resolve().parents[1] / 'samples' / 'withdraw-openapi.json').read_text(encoding='utf-8'))


def rejected(spec: Any, message: str) -> None:
    with pytest.raises(HTTPException) as error:
        parse_openapi(spec)
    assert error.value.status_code == 422
    assert message.lower() in error.value.detail.lower()


@pytest.mark.parametrize('version', ['3.0.3', '3.1.0'])
def test_valid_document_and_contract(spec: dict[str, Any], version: str) -> None:
    spec['openapi'] = version
    original = deepcopy(spec)
    response = TestClient(app).post('/api/analyze', json={'openapi': spec})
    assert response.status_code == 200
    assert response.json() == {'title': 'Synthetic Wallet API', 'operations': [{'method': 'POST', 'path': '/withdraw'}]}
    assert spec == original


@pytest.mark.parametrize('field', ['openapi', 'info', 'paths'])
def test_missing_document_fields(spec: dict[str, Any], field: str) -> None:
    del spec[field]
    rejected(spec, field)


@pytest.mark.parametrize(('path', 'value', 'message'), [
    (('openapi',), '3.not-valid', 'openapi'),
    (('openapi',), 3, 'openapi'),
    (('info',), [], 'info'),
    (('info', 'title'), '', 'title'),
    (('info', 'title'), 1, 'title'),
    (('info', 'version'), None, 'version'),
    (('paths',), {}, 'paths'),
    (('paths',), [], 'paths'),
    (('paths', '/withdraw'), [], '/withdraw'),
    (('paths', '/withdraw', 'post'), None, 'post'),
    (('paths', '/withdraw', 'post', 'requestBody'), {}, 'content'),
    (('paths', '/withdraw', 'post', 'requestBody', 'required'), 'yes', 'required'),
    (('paths', '/withdraw', 'post', 'requestBody', 'content'), {}, 'application/json'),
    (('paths', '/withdraw', 'post', 'requestBody', 'content'), {'text/plain': {'schema': {'type': 'string'}}}, 'application/json'),
    (('paths', '/withdraw', 'post', 'requestBody', 'content', 'application/json'), {}, 'schema'),
    (('paths', '/withdraw', 'post', 'requestBody', 'content', 'application/json', 'schema'), {'type': 'string'}, 'object'),
    (('paths', '/withdraw', 'post', 'responses'), {}, 'responses'),
    (('paths', '/withdraw', 'post', 'responses'), {'20': {'description': 'bad'}}, 'response'),
    (('paths', '/withdraw', 'post', 'responses'), {'200': {}}, 'description'),
    (('paths', '/withdraw', 'post', 'responses'), {'200': []}, 'response'),
])
def test_invalid_structures(spec: dict[str, Any], path: tuple[str, ...], value: Any, message: str) -> None:
    node = spec
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    rejected(spec, message)


@pytest.mark.parametrize('field', ['title', 'version'])
def test_missing_info_fields(spec: dict[str, Any], field: str) -> None:
    del spec['info'][field]
    rejected(spec, field)


@pytest.mark.parametrize('field', ['requestBody', 'responses'])
def test_missing_operation_fields(spec: dict[str, Any], field: str) -> None:
    del spec['paths']['/withdraw']['post'][field]
    rejected(spec, field)


@pytest.mark.parametrize('path', ['withdraw', '/withdraw?x=1', '/withdraw#fragment', '/a/../b', '//withdraw', '/with space', '/wallet/{id}'])
def test_malformed_or_unsupported_paths(spec: dict[str, Any], path: str) -> None:
    spec['paths'][path] = spec['paths'].pop('/withdraw')
    rejected(spec, 'path')


def test_no_phantom_operations(spec: dict[str, Any]) -> None:
    spec['paths']['/read-only'] = {'get': {'responses': {'200': {'description': 'OK'}}}}
    spec['paths']['/metadata'] = {'summary': 'post is mentioned but not declared'}
    assert [item.path for item in parse_openapi(spec).operations] == ['/withdraw']
    plan = fixture_plan('Reject overdrafts')
    plan.cases[0].path = '/metadata'
    with pytest.raises(HTTPException, match='undeclared operation'):
        validate_plan_against_spec(plan, spec)
    del spec['paths']['/withdraw']
    rejected(spec, 'POST')


def test_resolves_local_request_body_schema_and_response(spec: dict[str, Any]) -> None:
    operation = spec['paths']['/withdraw']['post']
    body = operation['requestBody']
    schema = body['content']['application/json']['schema']
    body['content']['application/json']['schema'] = {'$ref': '#/components/schemas/Wallet'}
    spec['components'] = {'requestBodies': {'Withdraw': body}, 'schemas': {'Wallet': schema}, 'responses': {'Accepted': {'description': 'OK', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Wallet'}}}}}}
    operation['requestBody'] = {'$ref': '#/components/requestBodies/Withdraw'}
    operation['responses']['200'] = {'$ref': '#/components/responses/Accepted'}
    original = deepcopy(spec)
    assert parse_openapi(spec).operations[0].path == '/withdraw'
    assert spec == original


@pytest.mark.parametrize(('reference', 'message'), [
    ('#/components/schemas/Missing', 'broken'),
    ('https://example.com/schema.json', 'local'),
    ('file:///schema.json', 'local'),
    ('other.json#/Wallet', 'local'),
    ('#/paths/~1withdraw', 'unsupported'),
    ('#/components/responses/Accepted', 'unsupported'),
    ('#/components/schemas/Bad~2Name', 'pointer'),
    (123, 'reference'),
])
def test_invalid_schema_references(spec: dict[str, Any], reference: Any, message: str) -> None:
    spec['components'] = {'responses': {'Accepted': {'description': 'OK'}}}
    spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema'] = {'$ref': reference}
    rejected(spec, message)


@pytest.mark.parametrize('indirect', [False, True])
def test_cyclic_schema_references(spec: dict[str, Any], indirect: bool) -> None:
    schemas = {'Loop': {'type': 'object', 'properties': {'child': {'$ref': '#/components/schemas/Other' if indirect else '#/components/schemas/Loop'}}}}
    if indirect:
        schemas['Other'] = {'$ref': '#/components/schemas/Loop'}
    spec['components'] = {'schemas': schemas}
    spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema'] = {'$ref': '#/components/schemas/Loop'}
    rejected(spec, 'cyclic')


def test_bounded_reference_chain(spec: dict[str, Any]) -> None:
    spec['components'] = {'schemas': {f'S{i}': {'$ref': f'#/components/schemas/S{i+1}'} for i in range(40)}}
    spec['components']['schemas']['S40'] = {'type': 'object'}
    spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema'] = {'$ref': '#/components/schemas/S0'}
    rejected(spec, 'limit')


@pytest.mark.parametrize('schema', [[], {'type': 'invalid'}, {'type': 'object', 'properties': []}, {'type': 'object', 'required': 'amount'}, {'type': 'array'}, {'allOf': [{'$ref': '#/components/schemas/Missing'}]}])
def test_invalid_or_unsupported_schema(spec: dict[str, Any], schema: Any) -> None:
    spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema'] = schema
    rejected(spec, 'schema')


def test_http_error_is_useful(spec: dict[str, Any]) -> None:
    del spec['paths']['/withdraw']['post']['requestBody']
    response = TestClient(app).post('/api/analyze', json={'openapi': spec})
    assert response.status_code == 422
    assert 'requestBody' in response.json()['detail']

@pytest.mark.parametrize('kind', ['requestBodies', 'responses'])
def test_cyclic_non_schema_references(spec: dict[str, Any], kind: str) -> None:
    spec['components'] = {kind: {'A': {'$ref': f'#/components/{kind}/B'}, 'B': {'$ref': f'#/components/{kind}/A'}}}
    rejected(spec, 'cyclic')


def test_unused_broken_reference_rejected(spec: dict[str, Any]) -> None:
    spec['components'] = {'schemas': {'Unused': {'$ref': '#/components/schemas/Missing'}}}
    rejected(spec, 'broken')


def test_reference_siblings_rejected(spec: dict[str, Any]) -> None:
    spec['components'] = {'schemas': {'Wallet': {'type': 'object'}}}
    spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema'] = {'$ref': '#/components/schemas/Wallet', 'type': 'string'}
    rejected(spec, 'siblings')


def test_json_pointer_escapes_and_reused_schema(spec: dict[str, Any]) -> None:
    spec['components'] = {'schemas': {'Name/With~Escape': {'type': 'integer'}}}
    schema = spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema']
    schema['properties'] = {name: {'$ref': '#/components/schemas/Name~1With~0Escape'} for name in ['balance', 'amount']}
    assert parse_openapi(spec).operations[0].path == '/withdraw'


def test_deep_inline_schema_is_bounded(spec: dict[str, Any]) -> None:
    schema = {'type': 'object'}
    for _ in range(40):
        schema = {'type': 'object', 'properties': {'child': schema}}
    spec['components'] = {'schemas': {'Deep': schema}}
    rejected(spec, 'limit')


def test_reference_expansion_is_bounded(spec: dict[str, Any]) -> None:
    spec['components'] = {'schemas': {'Value': {'type': 'integer'}, 'Wide': {'type': 'object', 'properties': {f'p{i}': {'$ref': '#/components/schemas/Value'} for i in range(129)}}}}
    rejected(spec, 'limit')


def test_document_node_count_is_bounded(spec: dict[str, Any]) -> None:
    spec['components'] = {'schemas': {'Wide': {'type': 'object', 'properties': {f'p{i}': {'type': 'integer'} for i in range(5100)}}}}
    rejected(spec, 'limit')


@pytest.mark.parametrize(('field', 'value'), [('minimum', 'zero'), ('multipleOf', 0), ('maxLength', True), ('minItems', -1), ('nullable', 'yes'), ('description', 1)])
def test_schema_keyword_types(spec: dict[str, Any], field: str, value: Any) -> None:
    schema = spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['schema']
    schema['properties']['amount'][field] = value
    rejected(spec, 'schema')


@pytest.mark.parametrize('root', [None, [], 'not OpenAPI'])
def test_root_is_an_object(root: Any) -> None:
    rejected(root, 'object')


@pytest.mark.parametrize('field', ['summary', 'parameters'])
def test_malformed_operation_metadata(spec: dict[str, Any], field: str) -> None:
    spec['paths']['/withdraw']['post'][field] = 1
    rejected(spec, field)


def test_example_reference_text_is_not_resolved(spec: dict[str, Any]) -> None:
    spec['paths']['/withdraw']['post']['requestBody']['content']['application/json']['example'] = {'$ref': 'this is literal example data'}
    assert parse_openapi(spec).operations[0].path == '/withdraw'
