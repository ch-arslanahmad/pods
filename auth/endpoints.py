from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


async def mcp(request) -> PlainTextResponse:
    return PlainTextResponse("This is an MCP")


async def hello(request):
    return PlainTextResponse("hello World")


routes = [
    Route("/mcp", mcp),
    Route("/", hello),
]

app: Starlette = Starlette(routes=routes)

if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette

    print("Serving OAuth endpoints on http://127.0.0.1:5173 ...")
    uvicorn.run(app, host="127.0.0.1", port=5173)
