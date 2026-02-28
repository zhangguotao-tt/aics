#!/usr/bin/env python3
"""
数据库初始化脚本
用法: python scripts/init_db.py
"""
import asyncio
import sys
import os

# 将 backend 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db.database import init_db, engine, AsyncSessionLocal
from models.user import User, UserRole, UserStatus
from passlib.context import CryptContext
from sqlalchemy import select

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_default_admin():
    """创建默认管理员账号"""
    async with AsyncSessionLocal() as session:
        # 检查是否已存在管理员
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        if result.scalar_one_or_none():
            print("✅ 管理员账号已存在，跳过创建")
            return

        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=pwd_context.hash("Admin@123456"),
            full_name="系统管理员",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.commit()
        print("✅ 默认管理员账号创建成功")
        print("   用户名: admin")
        print("   密 码: Admin@123456  ← 请登录后立即修改！")


async def main():
    print("🚀 开始初始化数据库...")
    await init_db()
    print("✅ 数据库表创建完成")
    await create_default_admin()
    await engine.dispose()
    print("🎉 数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
