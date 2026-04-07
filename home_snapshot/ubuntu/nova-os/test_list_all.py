import asyncio
from nova.kernel import get_kernel
async def run():
    kernel = get_kernel()
    await kernel.initialize()
    workspaces = await kernel.workspace_manager.list_workspaces()
    for ws in workspaces:
        agents = await kernel.agent_registry.list(ws.id)
        print(f"Workspace {ws.name} ({ws.id}) has {len(agents)} agents")
asyncio.run(run())
