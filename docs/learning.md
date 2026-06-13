# Learnings

## Pydantic

Pydantic auto-validates tool inputs before they reach your DB, and returns **LLM-readable error messages** in *JSON-RPC* format, a native LLM format.

Ultimately, allows the model to see exactly what it did wrong and self-correct.

### Field validators

Full reference: [Pydantic Fields](https://docs.pydantic.dev/latest/concepts/fields/), however its quite indepth, advanced.

The most common validators used:

| Param        | Meaning                  | Example                       |
| ------------ | ------------------------ | ----------------------------- |
| `gt`         | greater than (exclusive) | `gt=0` rejects 0, -5          |
| `ge`         | greater than or equal    | `ge=1` accepts 1, 2...        |
| `le`         | less than or equal       | `le=100` accepts 100, 99...   |
| `min_length` | minimum string length    | `min_length=1` rejects `""`   |
| `max_length` | maximum string length    | `max_length=200` caps at 200  |
| `pattern`    | regex pattern            | `pattern=r"^[a-z]+$"`         |
| None type    | marks field as optional  | `project: str \| None = None` |
| `default`    | fallback if not provided | `default=50`                  |

### Using a Pydantic model class

```python
class Pod(BaseModel):
    pod_id: int | None = Field(None, gt=0)
    pod_name: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1)
    category: str | None = Field(None, min_length=1, max_length=100)
    project: str | None = None
    query: str | None = Field(None, min_length=1)
    limit: int = Field(default=50, ge=1)
    offset: int = Field(default=0, ge=0)
```

All fields are optional (`None` default) so one class works across all tools. FastMCP unwraps it, each field becomes a separate MCP tool parameter.

```python
@mcp.tool()
def pods_add(pod: Pod) -> int:
    return db.create_pod(pod.pod_name, pod.content, pod.project, pod.category)
```

However, error arises if value is `None` and hence the model `pods_add()` would give error hence we need a conditional, `if (pod.pod_name is None)`.

### What errors look like

Pydantic catches **invalid values** (based on a condition, i.e., wrong data-type, out of range value):

```
Empty pod_name:
-> "String should have at least 1 character"

pod_id=-5:
-> "Input should be greater than 0"

limit=0:
-> "Input should be greater than or equal to 1"
```

Pydantic also catches **missing values** if the field has no `None` default, however when using a class every tool exposes all attributes.

```python
# Required — no default, Pydantic rejects if missing
pod_name: str = Field(min_length=1) # Field() if no class

# Optional — has = None or default, Pydantic fills default if missing
project: str | None = None
limit: int = Field(default=50, ge=1)
```

Pydantic catches bad values on both, but only catches missing values on required fields (no default).

```
Missing pod_name (not passed at all):
-> "Field required"
```

FastMCP sends these back as tool errors in JSON-RPC format. The LLM reads them and retries with corrected input.


### Using `Field()` instead of a Pydantic model class

As stated, you can use `Field()` directly on function params (no class)

You don't need a separate model class. FastMCP reads `Field()` directly from function signatures. This is the approach we use:

```python
@mcp.tool()
def pods_add(
    pod_name: str = Field(min_length=1, max_length=200),
    content: str = Field(min_length=1),
    category: str = Field(min_length=1, max_length=100),
    project: str | None = None,
) -> int:
    return db.create_pod(pod_name, content, project, category)
```

Each tool shows only its params, required fields enforced.
However you repeat validations across tools.