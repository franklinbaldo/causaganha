import inspect

import pydantic_ai
from pydantic_ai import Agent


print(f"pydantic-ai version: {pydantic_ai.__version__}")
print(f"Agent signature: {inspect.signature(Agent)}")
