"""CLI entry point for running server with uvicorn."""

import uvicorn
from server import config

if __name__ == "__main__":
    uvicorn.run("server.main:app", host=config.HOST, port=config.PORT, reload=True)
