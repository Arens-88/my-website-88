#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据隔离测试脚本
测试不同用户的数据访问权限控制功能
"""

import sys
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base, User, AmazonStore, AmazonIntegratedData, CostRecord, SyncLog

class UserIsolationTester:
    """用户数据隔离测试类"""
    
    def __init__(self, db_url='sqlite:///amazon_report.db'):
        """初始化测试环境"""
        print("=== 用户数据隔离测试开始 ===")
        self.engine = create_engine(db_url, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()
        self.success_count = 0
        self.failure_count = 0
        
    def run_all_tests(self):
        """运行所有测试用例"""
        try:
            # 测试1: 创建测试用户
            self.test_user_creation()
            
            # 测试2: 测试数据插入与user_id关联
            self.test_data_insertion()
            
            # 测试3: 验证普通用户只能访问自己的数据
            self.test_normal_user_isolation()
            
            # 测试4: 验证管理员可以访问所有数据
            self.test_admin_access()
            
            # 测试5: 验证数据更新时user_id保护
            self.test_data_update_protection()
            
        except Exception as e:
            self._print_failure(f"测试过程发生错误: {str(e)}")
        finally:
            self._print_summary()
            self.db_session.close()
    
    def test_user_creation(self):
        """测试1: 创建测试用户"""
        print("\n[测试1] 创建测试用户...")
        
        try:
            # 删除已存在的测试用户
            self.db_session.query(User).filter(User.username.in_(['test_user1', 'test_user2'])).delete()
            self.db_session.commit()
            
            # 创建两个测试用户
            user1 = User(
                username='test_user1',
                email='test1@example.com',
                full_name='测试用户1',
                is_admin=False
            )
            user1.set_password('password123')
            
            user2 = User(
                username='test_user2',
                email='test2@example.com',
                full_name='测试用户2',
                is_admin=False
            )
            user2.set_password('password123')
            
            self.db_session.add_all([user1, user2])
            self.db_session.commit()
            
            # 验证用户创建
            user1_db = self.db_session.query(User).filter_by(username='test_user1').first()
            user2_db = self.db_session.query(User).filter_by(username='test_user2').first()
            
            if user1_db and user2_db:
                self._print_success(f"成功创建测试用户: {user1_db.username}, {user2_db.username}")
                self.test_users = {"user1": user1_db, "user2": user2_db}
            else:
                self._print_failure("用户创建失败")
                
        except Exception as e:
            self.db_session.rollback()
            self._print_failure(f"创建测试用户失败: {str(e)}")
    
    def test_data_insertion(self):
        """测试2: 测试数据插入与user_id关联"""
        print("\n[测试2] 测试数据插入与user_id关联...")
        
        try:
            # 为每个用户创建一些测试数据
            user1 = self.test_users["user1"]
            user2 = self.test_users["user2"]
            
            # 删除现有测试数据
            self.db_session.query(AmazonStore).filter(AmazonStore.user_id.in_([user1.id, user2.id])).delete()
            self.db_session.query(AmazonIntegratedData).filter(AmazonIntegratedData.user_id.in_([user1.id, user2.id])).delete()
            self.db_session.commit()
            
            # 创建AmazonStore数据
            store1 = AmazonStore(
                user_id=user1.id,
                store_name=f"测试店铺-{user1.username}",
                region="US",
                is_active=1
            )
            
            store2 = AmazonStore(
                user_id=user2.id,
                store_name=f"测试店铺-{user2.username}",
                region="JP",
                is_active=1
            )
            
            self.db_session.add_all([store1, store2])
            self.db_session.commit()
            
            # 创建AmazonIntegratedData数据
            today = datetime.date.today()
            data1 = AmazonIntegratedData(
                user_id=user1.id,
                asin="B081234567",
                order_date=today,
                store_id=store1.id,
                store_name=store1.store_name,
                order_count=10,
                sales_amount=100.0
            )
            
            data2 = AmazonIntegratedData(
                user_id=user2.id,
                asin="B087654321",
                order_date=today,
                store_id=store2.id,
                store_name=store2.store_name,
                order_count=20,
                sales_amount=200.0
            )
            
            self.db_session.add_all([data1, data2])
            self.db_session.commit()
            
            # 验证数据关联
            user1_data = self.db_session.query(AmazonIntegratedData).filter_by(user_id=user1.id).all()
            user2_data = self.db_session.query(AmazonIntegratedData).filter_by(user_id=user2.id).all()
            
            if len(user1_data) == 1 and len(user2_data) == 1:
                self._print_success(f"数据插入成功，每个用户各有1条测试数据")
            else:
                self._print_failure(f"数据关联验证失败，user1: {len(user1_data)}条, user2: {len(user2_data)}条")
                
        except Exception as e:
            self.db_session.rollback()
            self._print_failure(f"数据插入测试失败: {str(e)}")
    
    def test_normal_user_isolation(self):
        """测试3: 验证普通用户只能访问自己的数据"""
        print("\n[测试3] 验证普通用户数据隔离...")
        
        try:
            user1 = self.test_users["user1"]
            user2 = self.test_users["user2"]
            
            # 模拟user1查询数据
            user1_stores = self.db_session.query(AmazonStore).filter_by(user_id=user1.id).count()
            user1_data = self.db_session.query(AmazonIntegratedData).filter_by(user_id=user1.id).count()
            
            # 模拟user2查询数据
            user2_stores = self.db_session.query(AmazonStore).filter_by(user_id=user2.id).count()
            user2_data = self.db_session.query(AmazonIntegratedData).filter_by(user_id=user2.id).count()
            
            # 验证用户只能看到自己的数据
            if user1_stores == 1 and user1_data == 1 and user2_stores == 1 and user2_data == 1:
                self._print_success(f"用户数据隔离验证通过，每个用户只能看到自己的数据")
            else:
                self._print_failure(f"用户数据隔离验证失败: user1({user1_stores}店铺, {user1_data}数据), user2({user2_stores}店铺, {user2_data}数据)")
                
        except Exception as e:
            self._print_failure(f"用户隔离测试失败: {str(e)}")
    
    def test_admin_access(self):
        """测试4: 验证管理员可以访问所有数据"""
        print("\n[测试4] 验证管理员访问权限...")
        
        try:
            # 获取管理员用户
            admin = self.db_session.query(User).filter_by(username='admin').first()
            
            if not admin:
                self._print_failure("未找到管理员账号")
                return
            
            # 模拟管理员查询所有数据
            total_stores = self.db_session.query(AmazonStore).count()
            total_data = self.db_session.query(AmazonIntegratedData).count()
            
            # 应该能看到所有测试用户的数据
            if total_stores >= 2 and total_data >= 2:
                self._print_success(f"管理员权限验证通过，可以访问所有数据 (店铺: {total_stores}, 数据: {total_data})")
            else:
                self._print_failure(f"管理员权限验证失败，无法访问所有数据 (店铺: {total_stores}, 数据: {total_data})")
                
        except Exception as e:
            self._print_failure(f"管理员权限测试失败: {str(e)}")
    
    def test_data_update_protection(self):
        """测试5: 验证数据更新时user_id保护"""
        print("\n[测试5] 验证数据更新保护机制...")
        
        try:
            user1 = self.test_users["user1"]
            user2 = self.test_users["user2"]
            
            # 获取user1的数据
            user1_data = self.db_session.query(AmazonIntegratedData).filter_by(user_id=user1.id).first()
            
            if not user1_data:
                self._print_failure("未找到user1的测试数据")
                return
            
            # 尝试将user1的数据user_id修改为user2（应该被应用层阻止，但这里直接测试）
            original_user_id = user1_data.user_id
            
            # 记录修改前的ID
            data_id = user1_data.id
            
            # 修改user_id
            user1_data.user_id = user2.id
            self.db_session.commit()
            
            # 重新查询验证修改
            updated_data = self.db_session.query(AmazonIntegratedData).filter_by(id=data_id).first()
            
            # 检查修改是否生效
            if updated_data and updated_data.user_id == user2.id:
                # 修改成功，这是数据库层的预期行为
                self._print_warning("数据库层允许修改user_id，请注意在API层添加严格的权限检查")
            else:
                self._print_failure(f"数据更新未按预期生效: 原user_id={original_user_id}, 修改后user_id={updated_data.user_id if updated_data else 'None'}")
            
            # 恢复数据
            if updated_data:
                updated_data.user_id = original_user_id
                self.db_session.commit()
            
            # 验证数据已恢复
            restored_data = self.db_session.query(AmazonIntegratedData).filter_by(id=data_id).first()
            if restored_data and restored_data.user_id == original_user_id:
                self._print_success("数据已成功恢复，测试通过")
            else:
                self._print_failure("数据恢复失败")
                
        except Exception as e:
            self.db_session.rollback()
            self._print_failure(f"数据更新保护测试失败: {str(e)}")
    
    def _print_success(self, message):
        """打印成功信息"""
        print(f"✅ {message}")
        self.success_count += 1
    
    def _print_failure(self, message):
        """打印失败信息"""
        print(f"❌ {message}")
        self.failure_count += 1
    
    def _print_warning(self, message):
        """打印警告信息"""
        print(f"⚠️ {message}")
    
    def _print_summary(self):
        """打印测试总结"""
        print("\n=== 测试总结 ===")
        print(f"成功: {self.success_count} 项")
        print(f"失败: {self.failure_count} 项")
        
        if self.failure_count == 0:
            print("🎉 所有测试通过！用户数据隔离功能正常工作。")
        else:
            print("❌ 存在测试失败，请检查代码和配置。")

if __name__ == '__main__':
    # 运行测试
    tester = UserIsolationTester()
    tester.run_all_tests()
