import asyncio,sys,tempfile,shutil
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def check_server(folder):
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(folder/'server.py')])
    async with stdio_client(params) as (r,w):
        async with ClientSession(r,w) as client:
            await client.initialize();listing=await client.list_tools()
            assert len(listing.tools)==7
            result=await client.call_tool('get_sync_status',{})
            assert not result.isError
            print('MCP stdio handshake: PASS; read-only tools:',len(listing.tools))
            for tool in listing.tools:print(tool.name)
async def main():
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='synthetic-mcp-',dir=root) as temp:
        folder=Path(temp)
        for name in ['assistant.py','server.py']:shutil.copyfile(root/name,folder/name)
        await check_server(folder)
asyncio.run(asyncio.wait_for(main(), timeout=30))
