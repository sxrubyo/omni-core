import asyncio
from nova.kernel import get_kernel
async def run():
    kernel = get_kernel()
    await kernel.initialize()
    ws = await kernel.workspace_manager.ensure_default_workspace()
    agents = await kernel.agent_registry.list(ws.id)
    print(f"Workspace {ws.id} agents: {len(agents)}")
asyncio.run(run())
