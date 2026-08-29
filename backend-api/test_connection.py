import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv('.env')

db_url = os.getenv('DATABASE_URL')
print(f'Database URL: {db_url[:40]}...')

async def test_connection():
    import asyncpg
    try:
        # Convert asyncpg URL to regular postgres URL for direct connection
        sync_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        conn = await asyncpg.connect(sync_url)
        version = await conn.fetchval('SELECT version()')
        print(f'Connected! PostgreSQL version: {version}')
        
        # Check if tables exist
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        table_names = [t['table_name'] for t in tables]
        print(f'Tables found: {table_names}')
        print(f'Total tables: {len(table_names)}')
        
        await conn.close()
        print('Connection test PASSED!')
    except Exception as e:
        print(f'Connection test FAILED: {e}')

asyncio.run(test_connection())
