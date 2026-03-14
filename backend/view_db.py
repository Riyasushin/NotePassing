#!/usr/bin/env python3
"""友好的数据库查看工具"""

import asyncio
import os
import sys

# 强制加载 .env 文件
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings

settings = get_settings()

# 创建引擎
engine = create_async_engine(settings.database_url)
print(f"🔗 连接到: {settings.database_url.split('@')[1] if '@' in settings.database_url else '数据库'}")


async def list_tables():
    """列出所有表"""
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        
        print("\n📋 数据库表列表:")
        print("-" * 40)
        for i, (table,) in enumerate(tables, 1):
            # 获取行数
            count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.scalar()
            print(f"  {i}. {table:<25} ({count} 行)")
        print("-" * 40)
        return [t[0] for t in tables]


async def view_table(table_name: str, limit: int = 20):
    """查看表数据"""
    async with engine.connect() as conn:
        # 获取列名
        cols_result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table
            ORDER BY ordinal_position
        """), {"table": table_name})
        columns = [c[0] for c in cols_result.fetchall()]
        
        if not columns:
            print(f"❌ 表 {table_name} 不存在")
            return
        
        # 获取数据
        result = await conn.execute(
            text(f"SELECT * FROM {table_name} LIMIT {limit}")
        )
        rows = result.fetchall()
        
        print(f"\n📊 表: {table_name}")
        print(f"   列: {', '.join(columns)}")
        print(f"   显示前 {limit} 行:\n")
        
        # 打印表头
        header = " | ".join(f"{c:<15}" for c in columns)
        print(header)
        print("-" * len(header))
        
        # 打印数据
        for row in rows:
            formatted = []
            for val in row:
                s = str(val) if val is not None else "NULL"
                # 截断长字符串
                if len(s) > 15:
                    s = s[:12] + "..."
                formatted.append(f"{s:<15}")
            print(" | ".join(formatted))
        
        if not rows:
            print("  (空表)")
        print()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="查看数据库数据")
    parser.add_argument("table", nargs="?", help="表名（不提供则列出所有表）")
    parser.add_argument("-n", "--limit", type=int, default=20, help="显示行数（默认20）")
    parser.add_argument("-a", "--all", action="store_true", help="显示所有表的数据")
    
    args = parser.parse_args()
    
    if args.all:
        tables = await list_tables()
        print()
        for table in tables:
            await view_table(table, args.limit)
    elif args.table:
        await view_table(args.table, args.limit)
    else:
        await list_tables()
        print("\n💡 提示: 使用 ./view_db.py <表名> 查看具体表数据")
        print("   例如: ./view_db.py devices")
        print("   例如: ./view_db.py -a 查看所有表")


if __name__ == "__main__":
    asyncio.run(main())
