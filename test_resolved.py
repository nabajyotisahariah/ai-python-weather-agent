import asyncio
from app.cache.context_memory import ContextMemory
async def test():
    mem = ContextMemory()
    city = await mem.get_resolved_city('abcd1242', 'default_user')
    print('resolved:', city)
asyncio.run(test())