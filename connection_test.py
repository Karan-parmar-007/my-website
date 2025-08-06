import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        user='karan',
        password='2004',
        database='my_website',
        host='localhost'  # Your host IP
    )
    print("Connected!")
    await conn.close()

asyncio.run(test())