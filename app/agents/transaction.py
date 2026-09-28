"""SQLite 正式写事务。"""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession


class ImmediateUnitOfWork:
    """在独立连接上执行 BEGIN IMMEDIATE，并独占提交权。"""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._connection: AsyncConnection | None = None
        self.session: AsyncSession | None = None
        self._finished = False

    async def __aenter__(self) -> "ImmediateUnitOfWork":  # noqa: PYI034
        self._connection = await self._engine.connect()
        if self._connection.dialect.name == "sqlite":
            await self._connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            await self._connection.begin()
        self.session = AsyncSession(bind=self._connection, expire_on_commit=False)
        return self

    async def commit(self) -> None:
        if self.session is None or self._connection is None:
            raise RuntimeError("unit of work is not active")
        await self.session.flush()
        await self._connection.commit()
        self._finished = True

    async def rollback(self) -> None:
        if self._connection is not None and not self._finished:
            await self._connection.rollback()
            self._finished = True

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self._finished:
            await self.rollback()
        if self.session is not None:
            await self.session.close()
        if self._connection is not None:
            await self._connection.close()
