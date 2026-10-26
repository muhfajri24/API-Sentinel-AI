# OpenAPI parser MVP subset (TASK 02)

`POST /api/analyze` keeps its existing request and response shapes. Validation
failures return HTTP 422 with a location and reason. Validation performs no
network or filesystem resolution and does not mutate the supplied document.

- Documents require an OpenAPI `3.<minor>.<patch>` release string, nonempty
  `info.title` and `info.version`, and at least one supported operation in `paths`.
- Only declared lowercase `post` operations are listed. GET and other methods
  never create POST endpoints. Invalid path items are rejected instead of skipped.
- Paths use static alphanumeric, underscore and hyphen segments, with an optional
  trailing slash. Templates, query strings, fragments, parameters and other path
  forms are unsupported by the current test-case contract.
- Each POST declares an `application/json` request body with an object schema and
  at least one response. Response keys are HTTP status strings, ranges such as
  `2XX`, or `default`; each response requires a string description.
- The schema subset supports explicit object, array and scalar types; object
  properties, required names, additional properties, array items and common scalar
  constraints. Schema structure is validated here; this is not a request-value
  validator or a complete OpenAPI/JSON Schema conformance implementation.
- References must point to a single component under `#/components/schemas/`,
  `#/components/requestBodies/`, or `#/components/responses/`, in the matching
  context. JSON pointer escapes `~0` and `~1` are supported. References resolve
  read-only before the body/schema structure is accepted.
- Broken and cyclic references, remote/file references, nested pointer targets,
  reference siblings, schema composition, dynamic references and other unsupported
  schema keywords are rejected. Unused definitions in these three component
  collections are validated too. Literal example/default/enum data is not resolved.
- Limits per validation: 32 nesting levels, 10,000 visited nodes and 128 reference
  expansions. These limits intentionally reject unusually large specifications.

No test-plan generation, Meta integration, HTTP execution or port configuration
is added or changed by TASK 02.
