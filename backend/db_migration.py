#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 为所有表添加用户数据隔离支持
此脚本将执行以下操作：
1. 为需要user_id字段的表添加字段
2. 为现有数据分配默认user_id=1（管理员）
3. 创建必要的外键关系
4. 添加索引以优化查询性能
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer, ForeignKey
from sqlalchemy.exc import SQLAlchemyError
from models import init_db, Base, User, AmazonIntegratedData

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('..', 'data', 'migration.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('db_migration')

# 需要添加user_id的表列表
TABLES_NEED_USER_ID = [
    'amazon_stores',
    'amazon_integrated_data',
    'cost_records', 
    'manual_cost',
    'sync_log',
    'report_share',
    'push_config'
]

def get_db_url():
    """从配置中获取数据库URL"""
    # 默认使用SQLite数据库
    return 'sqlite:///../data/amazon_report.db'

def check_user_table():
    """检查用户表是否存在且有管理员账号"""
    try:
        db_session = init_db()
        
        # 检查表是否存在
        inspector = inspect(db_session.get_bind())
        if 'users' not in inspector.get_table_names():
            logger.error('用户表不存在，请先运行初始化脚本')
            return False
        
        # 检查管理员账号是否存在
        admin_user = db_session.query(User).filter_by(username='admin').first()
        if not admin_user:
            logger.info('创建默认管理员账号...')
            admin_user = User(
                username='admin',
                email='admin@example.com',
                full_name='系统管理员',
                is_admin=True
            )
            admin_user.set_password('admin123')  # 默认密码
            db_session.add(admin_user)
            db_session.commit()
            logger.info('管理员账号创建成功: username=admin, password=admin123')
        else:
            logger.info('管理员账号已存在')
        
        return True
    except Exception as e:
        logger.error(f'检查用户表时出错: {str(e)}')
        return False
    finally:
        if 'db_session' in locals():
            db_session.close()

def add_user_id_columns():
    """为现有表添加user_id列"""
    try:
        db_url = get_db_url()
        engine = create_engine(db_url, echo=True)
        conn = engine.connect()
        inspector = inspect(engine)
        
        # 开始事务
        transaction = conn.begin()
        
        try:
            for table_name in TABLES_NEED_USER_ID:
                # 检查表是否存在
                if table_name not in inspector.get_table_names():
                    logger.warning(f'表 {table_name} 不存在，跳过')
                    continue
                
                # 检查是否已有user_id列
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'user_id' in columns:
                    logger.info(f'表 {table_name} 已经有user_id列，跳过')
                    continue
                
                # 为表添加user_id列（SQLite语法）
                try:
                    logger.info(f'为表 {table_name} 添加user_id列...')
                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN user_id INTEGER'))
                    logger.info(f'表 {table_name} user_id列添加成功')
                except Exception as e:
                    logger.error(f'为表 {table_name} 添加user_id列失败: {str(e)}')
                    # SQLite不支持直接添加外键，我们稍后在支持外键的数据库中处理
            
            # 提交事务
            transaction.commit()
            logger.info('所有表的user_id列添加完成')
            return True
        except Exception as e:
            transaction.rollback()
            logger.error(f'添加user_id列时发生错误: {str(e)}')
            return False
        finally:
            conn.close()
    except Exception as e:
        logger.error(f'连接数据库时出错: {str(e)}')
        return False

def update_existing_data():
    """更新现有数据，设置默认user_id=1"""
    try:
        db_url = get_db_url()
        engine = create_engine(db_url, echo=True)
        conn = engine.connect()
        inspector = inspect(engine)
        
        # 开始事务
        transaction = conn.begin()
        
        try:
            for table_name in TABLES_NEED_USER_ID:
                # 检查表是否存在且有user_id列
                if table_name not in inspector.get_table_names():
                    continue
                
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'user_id' not in columns:
                    continue
                
                # 更新数据，设置默认user_id=1
                logger.info(f'更新表 {table_name} 的现有数据，设置默认user_id=1...')
                result = conn.execute(text(f'UPDATE {table_name} SET user_id = 1 WHERE user_id IS NULL'))
                logger.info(f'表 {table_name} 更新完成，影响行数: {result.rowcount}')
            
            # 提交事务
            transaction.commit()
            logger.info('所有表的现有数据更新完成')
            return True
        except Exception as e:
            transaction.rollback()
            logger.error(f'更新现有数据时发生错误: {str(e)}')
            return False
        finally:
            conn.close()
    except Exception as e:
        logger.error(f'连接数据库时出错: {str(e)}')
        return False

def create_indices():
    """为user_id列创建索引以优化查询性能"""
    try:
        db_url = get_db_url()
        engine = create_engine(db_url, echo=True)
        conn = engine.connect()
        inspector = inspect(engine)
        
        # 开始事务
        transaction = conn.begin()
        
        try:
            for table_name in TABLES_NEED_USER_ID:
                # 检查表是否存在且有user_id列
                if table_name not in inspector.get_table_names():
                    continue
                
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'user_id' not in columns:
                    continue
                
                # 检查是否已有索引
                indices = inspector.get_indexes(table_name)
                user_id_index_exists = any(idx['column_names'] == ['user_id'] for idx in indices)
                
                if not user_id_index_exists:
                    # 创建索引
                    logger.info(f'为表 {table_name} 的user_id列创建索引...')
                    index_name = f'idx_{table_name}_user_id'
                    conn.execute(text(f'CREATE INDEX {index_name} ON {table_name} (user_id)'))
                    logger.info(f'表 {table_name} 的user_id索引创建成功')
                else:
                    logger.info(f'表 {table_name} 的user_id索引已存在')
            
            # 提交事务
            transaction.commit()
            logger.info('所有表的user_id索引创建完成')
            return True
        except Exception as e:
            transaction.rollback()
            logger.error(f'创建索引时发生错误: {str(e)}')
            return False
        finally:
            conn.close()
    except Exception as e:
        logger.error(f'连接数据库时出错: {str(e)}')
        return False

def verify_migration():
    """验证迁移是否成功"""
    try:
        db_session = init_db()
        inspector = inspect(db_session.get_bind())
        
        # 检查表的user_id列是否都已添加
        success = True
        for table_name in TABLES_NEED_USER_ID:
            if table_name not in inspector.get_table_names():
                continue
                
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            if 'user_id' not in columns:
                logger.error(f'表 {table_name} 缺少user_id列')
                success = False
            else:
                # 检查是否有数据没有user_id
                try:
                    result = db_session.execute(text(f'SELECT COUNT(*) FROM {table_name} WHERE user_id IS NULL'))
                    null_count = result.scalar()
                    if null_count > 0:
                        logger.warning(f'表 {table_name} 有 {null_count} 条记录的user_id为NULL')
                except Exception as e:
                    logger.error(f'检查表 {table_name} 的数据时出错: {str(e)}')
        
        # 验证是否可以正常查询用户数据
        try:
            # 测试查询用户的集成数据
            user_data = db_session.query(AmazonIntegratedData).filter_by(user_id=1).limit(5).all()
            logger.info(f'成功查询到 {len(user_data)} 条用户ID为1的集成数据记录')
        except Exception as e:
            logger.error(f'查询用户数据时出错: {str(e)}')
            success = False
        
        return success
    except Exception as e:
        logger.error(f'验证迁移时出错: {str(e)}')
        return False
    finally:
        if 'db_session' in locals():
            db_session.close()

def main():
    """主函数"""
    print("开始数据库迁移...")
    logger.info("=== 数据库迁移开始 ===")
    
    # 步骤1: 检查用户表
    print("1. 检查用户表和管理员账号...")
    if not check_user_table():
        print("错误: 用户表检查失败，请先初始化数据库")
        return False
    
    # 步骤2: 添加user_id列
    print("\n2. 为现有表添加user_id列...")
    if not add_user_id_columns():
        print("警告: 添加user_id列时出现问题，请检查日志")
    
    # 步骤3: 更新现有数据
    print("\n3. 更新现有数据，设置默认user_id=1...")
    if not update_existing_data():
        print("警告: 更新现有数据时出现问题，请检查日志")
    
    # 步骤4: 创建索引
    print("\n4. 为user_id列创建索引...")
    if not create_indices():
        print("警告: 创建索引时出现问题，请检查日志")
    
    # 步骤5: 验证迁移
    print("\n5. 验证迁移结果...")
    if verify_migration():
        print("\n数据库迁移成功完成！")
        logger.info("=== 数据库迁移成功完成 ===")
        return True
    else:
        print("\n警告: 迁移验证有问题，请检查日志")
        logger.warning("=== 数据库迁移验证有问题 ===")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
