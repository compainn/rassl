from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, select, delete, Boolean
from sqlalchemy.exc import NoResultFound
from datetime import datetime, timedelta
import json

DATABASE_URL = "sqlite+aiosqlite:///./bot.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    phone = Column(String(20))
    session_string = Column(Text)
    usernames = Column(Text, default='[]')
    message = Column(Text)
    is_active = Column(Integer, default=0)
    subscription_end = Column(DateTime)
    subscription_type = Column(String(20))
    mailing_hours = Column(Float, default=5.0)
    delay_minutes = Column(Float, default=3.5)

    def get_usernames(self):
        return json.loads(self.usernames) if self.usernames else []

    def set_usernames(self, usernames_list):
        self.usernames = json.dumps(usernames_list)

    def check_subscription(self):
        if not self.is_active:
            return False

        if self.subscription_type == 'forever':
            return True

        if self.subscription_end and self.subscription_end > datetime.now():
            return True

        if self.subscription_end and self.subscription_end <= datetime.now():
            self.is_active = 0
            return False

        return False

    def get_mailing_seconds(self):
        return self.mailing_hours * 3600

    def get_delay_seconds(self):
        return self.delay_minutes * 60

class Admin(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    is_ga = Column(Boolean, default=False)

class Config(Base):
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(500))

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        from config import ADMIN_PASSWORD, GA_PASSWORD

        configs = {
            'ADMIN_PASSWORD': ADMIN_PASSWORD if ADMIN_PASSWORD else 'admin123',
            'GA_PASSWORD': GA_PASSWORD if GA_PASSWORD else 'ga123',
            'ADMIN_IDS': '[]'
        }

        for key, value in configs.items():
            result = await session.execute(
                select(Config).where(Config.key == key)
            )
            config = result.scalar_one_or_none()

            if not config:
                config = Config(key=key, value=value)
                session.add(config)

        await session.commit()

async def get_user(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one()
            return user
        except NoResultFound:
            return None

async def create_user(telegram_id: int, **kwargs) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            if 'usernames' in kwargs and isinstance(kwargs['usernames'], list):
                kwargs['usernames'] = json.dumps(kwargs['usernames'])

            user = User(telegram_id=telegram_id, **kwargs)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

async def save_user(telegram_id: int, **kwargs) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            for key, value in kwargs.items():
                if key == 'usernames' and isinstance(value, list):
                    user.set_usernames(value)
                elif hasattr(user, key):
                    setattr(user, key, value)
        else:
            if 'usernames' in kwargs and isinstance(kwargs['usernames'], list):
                kwargs['usernames'] = json.dumps(kwargs['usernames'])

            user = User(telegram_id=telegram_id, **kwargs)
            session.add(user)

        await session.commit()
        await session.refresh(user)
        return user


async def delete_user(telegram_id: int) -> bool:
    """Удаляет только данные для рассылки, но оставляет подписку"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Очищаем только данные для рассылки, но оставляем подписку
            user.session_string = None
            user.phone = None
            user.usernames = '[]'  # Пустой список
            user.message = None

            await session.commit()
            return True
        return False

async def update_user_session(telegram_id: int, session_string: str = None) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.session_string = session_string
            await session.commit()
            return True
        return False

async def update_user_message(telegram_id: int, message: str = None) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.message = message
            await session.commit()
            return True
        return False

async def update_user_usernames(telegram_id: int, usernames: list = None) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.set_usernames(usernames or [])
            await session.commit()
            return True
        return False

async def update_subscription(telegram_id: int, days: int = 0, sub_type: str = 'day') -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.is_active = 1
            user.subscription_type = sub_type

            if sub_type == 'forever':
                user.subscription_end = None
            else:
                user.subscription_end = datetime.now() + timedelta(days=days)

            await session.commit()
            return True
        return False

async def update_mailing_settings(telegram_id: int, mailing_hours: float = None, delay_minutes: float = None) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            if mailing_hours is not None:
                user.mailing_hours = mailing_hours
            if delay_minutes is not None:
                user.delay_minutes = delay_minutes

            await session.commit()
            return True
        return False

async def get_admin(telegram_id: int) -> Admin | None:
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Admin).where(Admin.telegram_id == telegram_id)
            )
            admin = result.scalar_one()
            return admin
        except NoResultFound:
            return None

async def add_admin(telegram_id: int, username: str = None, is_ga: bool = False) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            admin = Admin(telegram_id=telegram_id, username=username, is_ga=is_ga)
            session.add(admin)
            await session.commit()

            if not is_ga:
                result = await session.execute(
                    select(Config).where(Config.key == 'ADMIN_IDS')
                )
                config = result.scalar_one()
                admin_ids = json.loads(config.value)
                if telegram_id not in admin_ids:
                    admin_ids.append(telegram_id)
                    config.value = json.dumps(admin_ids)
                    await session.commit()

            return True
        return False

async def get_all_users() -> list[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return users

async def get_all_admins() -> list[Admin]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin))
        admins = result.scalars().all()
        return admins

async def remove_admin(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        admin = result.scalar_one_or_none()

        if admin and not admin.is_ga:
            await session.delete(admin)

            result = await session.execute(
                select(Config).where(Config.key == 'ADMIN_IDS')
            )
            config = result.scalar_one()
            admin_ids = json.loads(config.value)
            if telegram_id in admin_ids:
                admin_ids.remove(telegram_id)
                config.value = json.dumps(admin_ids)

            await session.commit()
            return True
        return False

async def get_config(key: str) -> str | None:
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Config).where(Config.key == key)
            )
            config = result.scalar_one()
            return config.value
        except NoResultFound:
            return None

async def set_config(key: str, value: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Config).where(Config.key == key)
        )
        config = result.scalar_one_or_none()

        if config:
            config.value = value
        else:
            config = Config(key=key, value=value)
            session.add(config)

        await session.commit()
        return True

async def is_ga(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь главным админом"""
    admin = await get_admin(telegram_id)
    if admin and hasattr(admin, 'is_ga'):
        return admin.is_ga
    return False

async def get_all_admins_without_ga() -> list[Admin]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.is_ga == False)
        )
        admins = result.scalars().all()
        return admins

async def get_admin_ids() -> list[int]:
    admins = await get_all_admins()
    return [admin.telegram_id for admin in admins]
