from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import socket

# For Supabase PostgreSQL, SSL is handled by the connection string or pooler.

def _force_ipv4(database_url: str) -> str:
    """Replace the hostname in the DSN with its IPv4 address.

    Prevents 'OSError: [Errno 101] Network is unreachable' on hosts whose
    Supabase 'db.<ref>.supabase.co' hostname resolves to a non-routable IPv6
    (AAAA) address (common on Render's Docker network). Falls back to the
    original URL if resolution fails.
    """
    if "sqlite" in database_url:
        return database_url
    try:
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(database_url)
        host = parts.hostname
        if not host or not host.endswith("supabase.co"):
            return database_url
        # getaddrinfo returns (family, type, proto, canonname, sockaddr)
        infos = socket.getaddrinfo(host, parts.port or 5432, socket.AF_INET)
        ipv4 = infos[0][4][0]
        netloc = parts.netloc.replace(host, ipv4, 1)
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        return database_url


database_url = _force_ipv4(settings.DATABASE_URL)

connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
