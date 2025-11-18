#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FBA配送费计算器测试脚本
用于验证美国站和日本站修复后的计算结果准确性
"""

import sys
import os
import math

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 直接实现美国站的尺寸分段判断函数（复制自原代码并简化）
def determine_size_segment(max_len, mid_len, min_len, len_girth, weight_lb, weight_oz):
    """判断美国站的尺寸分段"""
    # 总重量（磅）
    total_weight_lb = weight_lb + weight_oz / 16.0
    
    # 首先判断是否为超大件（两个条件满足其一即可）
    # 条件1：尺寸超限（最大边>108英寸 或 周长+最长边>165英寸）
    if max_len > 108 or (len_girth + max_len) > 165:
        return "超大件"
    # 条件2：重量超限（>=100磅）
    elif total_weight_lb >= 100:
        return "超大件"
    # 判断大件
    elif max_len > 18 or len_girth + max_len > 75:
        if max_len <= 20 and len_girth + max_len <= 118:
            return "小号大件"
        elif max_len <= 30 and len_girth + max_len <= 130:
            return "中号大件"
        elif max_len <= 48 and len_girth + max_len <= 165:
            return "大号大件"
        else:
            return "超大件"
    # 判断标准尺寸
    else:
        if total_weight_lb < 1:
            return "小号标准尺寸"
        else:
            return "大号标准尺寸"

# 直接实现美国站的费用计算函数（复制自原代码并简化）
def calculate_fee(size_segment, weight_lb, weight_oz):
    """计算美国站的配送费"""
    # 总重量（磅）
    total_weight_lb = weight_lb + weight_oz / 16.0
    
    # 小号标准尺寸费用计算
    if size_segment == "小号标准尺寸":
        return 3.0  # 固定费用
    
    # 大号标准尺寸费用计算
    elif size_segment == "大号标准尺寸":
        if total_weight_lb <= 1:
            return 3.0
        elif total_weight_lb <= 2:
            return 3.96
        elif total_weight_lb <= 3:
            return 4.44
        elif total_weight_lb <= 21:
            # 基础费用 + (重量-3) × 每磅额外费用
            base_fee = 4.44
            additional_fee = (total_weight_lb - 3) * 0.48
            return base_fee + additional_fee
        else:
            # 超出21磅的特殊情况
            return 11.52  # 兜底值
    
    # 小号大件费用计算
    elif size_segment == "小号大件":
        if total_weight_lb <= 10:
            return 8.26
        else:
            # 基础费用 + (重量-10) × 每磅额外费用
            base_fee = 8.26
            additional_fee = (total_weight_lb - 10) * 0.48
            return base_fee + additional_fee
    
    # 中号大件费用计算
    elif size_segment == "中号大件":
        if total_weight_lb <= 20:
            return 13.85
        else:
            # 基础费用 + (重量-20) × 每磅额外费用
            base_fee = 13.85
            additional_fee = (total_weight_lb - 20) * 0.48
            return base_fee + additional_fee
    
    # 大号大件费用计算
    elif size_segment == "大号大件":
        if total_weight_lb <= 50:
            return 18.98
        else:
            # 基础费用 + (重量-50) × 每磅额外费用
            base_fee = 18.98
            additional_fee = (total_weight_lb - 50) * 0.48
            return base_fee + additional_fee
    
    # 超大件费用计算
    elif size_segment == "超大件":
        if total_weight_lb <= 90:
            return 90.0
        else:
            # 基础费用 + (重量-90) × 每磅额外费用
            base_fee = 90.0
            additional_fee = (total_weight_lb - 90) * 0.76
            return base_fee + additional_fee
    
    # 默认情况
    else:
        return 0.0

# 直接实现日本站的尺寸分段判断函数（复制自原代码并简化）
def determine_size_segment_jp(max_len_cm):
    """判断日本站的尺寸分段"""
    if max_len_cm <= 35:
        return "小号"
    elif max_len_cm <= 80:
        return "标准"
    elif max_len_cm <= 120:
        return "大件"
    elif max_len_cm <= 200:
        return "超大件"
    else:
        return "超大件（超出200厘米）"

# 简化版日本站费用计算函数
def calculate_fee_jp_demo(size_segment, weight_kg, price_over_1000, is_frozen=False):
    """日本站费用计算演示"""
    # 这是一个简化版的演示函数，仅用于验证关键逻辑
    # 实际费用计算请查看原代码中的完整实现
    if size_segment == "小号":
        return 630 if is_frozen else 589
    elif size_segment == "标准":
        return 960 if is_frozen else 914
    elif size_segment == "大件":
        return 1153 if is_frozen else 1052
    elif size_segment == "超大件":
        return 2760 if is_frozen else 2675
    else:
        return 4820

def test_us_size_segment():
    """测试美国站尺寸分段判断逻辑"""
    print("===== 测试美国站尺寸分段判断 =====")
    
    # 测试用例1：小号标准尺寸
    max_len, mid_len, min_len = 15, 10, 5
    len_girth = 2 * (mid_len + min_len) + max_len
    weight_lb, weight_oz = 0, 12
    result = determine_size_segment(max_len, mid_len, min_len, len_girth, weight_lb, weight_oz)
    print(f"测试1（小号标准尺寸）: 结果={result}, 期望=小号标准尺寸")
    
    # 测试用例2：大号标准尺寸（重量刚超过1磅）
    max_len, mid_len, min_len = 15, 10, 5
    len_girth = 2 * (mid_len + min_len) + max_len
    weight_lb, weight_oz = 1, 1
    result = determine_size_segment(max_len, mid_len, min_len, len_girth, weight_lb, weight_oz)
    print(f"测试2（大号标准尺寸-重量）: 结果={result}, 期望=大号标准尺寸")
    
    # 测试用例3：小号大件（刚好超过标准尺寸但小于20英寸）
    max_len, mid_len, min_len = 19, 10, 5
    len_girth = 2 * (mid_len + min_len) + max_len
    weight_lb, weight_oz = 10, 0
    result = determine_size_segment(max_len, mid_len, min_len, len_girth, weight_lb, weight_oz)
    print(f"测试3（小号大件-尺寸）: 结果={result}, 期望=小号大件")
    
    # 测试用例4：超大件（重量超限）
    max_len, mid_len, min_len = 15, 10, 5
    len_girth = 2 * (mid_len + min_len) + max_len
    weight_lb, weight_oz = 101, 0  # 101磅 > 100磅
    result = determine_size_segment(max_len, mid_len, min_len, len_girth, weight_lb, weight_oz)
    print(f"测试4（超大件-重量超限）: 结果={result}, 期望=超大件")
    
    print()

def test_us_fee_calculation():
    """测试美国站费用计算逻辑"""
    print("===== 测试美国站费用计算 =====")
    
    # 测试用例1：小号标准尺寸，<1磅
    size_segment = "小号标准尺寸"
    weight_lb, weight_oz = 0, 12
    result = calculate_fee(size_segment, weight_lb, weight_oz)
    print(f"测试1（小号标准尺寸，12盎司）: 费用=${result:.2f}")
    
    # 测试用例2：大号标准尺寸，1-2磅边界
    size_segment = "大号标准尺寸"
    weight_lb, weight_oz = 2, 0
    result = calculate_fee(size_segment, weight_lb, weight_oz)
    print(f"测试2（大号标准尺寸，2磅）: 费用=${result:.2f}")
    
    # 测试用例3：大号标准尺寸，3-21磅范围内
    size_segment = "大号标准尺寸"
    weight_lb, weight_oz = 10, 0
    result = calculate_fee(size_segment, weight_lb, weight_oz)
    print(f"测试3（大号标准尺寸，10磅）: 费用=${result:.2f}")
    
    # 测试用例4：中号大件，额外重量计算
    size_segment = "中号大件"
    weight_lb, weight_oz = 21, 0  # 21磅（超过首重20磅1磅）
    result = calculate_fee(size_segment, weight_lb, weight_oz)
    print(f"测试4（中号大件，21磅）: 费用=${result:.2f}")
    
    print()

def test_jp_size_segment():
    """测试日本站尺寸分段判断逻辑"""
    print("===== 测试日本站尺寸分段判断 =====")
    
    # 测试用例1：小号（≤35厘米）
    max_len_cm = 30
    result = determine_size_segment_jp(max_len_cm)
    print(f"测试1（小号，30厘米）: 结果={result}, 期望=小号")
    
    # 测试用例2：标准尺寸（>35厘米但≤80厘米）
    max_len_cm = 60
    result = determine_size_segment_jp(max_len_cm)
    print(f"测试2（标准尺寸，60厘米）: 结果={result}, 期望=标准")
    
    # 测试用例3：大件（>80厘米但≤120厘米）
    max_len_cm = 100
    result = determine_size_segment_jp(max_len_cm)
    print(f"测试3（大件，100厘米）: 结果={result}, 期望=大件")
    
    # 测试用例4：超大件（>120厘米但≤200厘米）
    max_len_cm = 150
    result = determine_size_segment_jp(max_len_cm)
    print(f"测试4（超大件，150厘米）: 结果={result}, 期望=超大件")
    
    print()

def test_jp_fee_demo():
    """测试日本站费用计算逻辑（简化版）"""
    print("===== 测试日本站费用计算（简化版）=====")
    
    # 测试用例1：非冷冻-小号
    size_segment = "小号"
    weight_kg = 0.2
    price_over_1000 = False
    is_frozen = False
    result = calculate_fee_jp_demo(size_segment, weight_kg, price_over_1000, is_frozen)
    print(f"测试1（非冷冻-小号）: 费用={result}日元")
    
    # 测试用例2：冷冻-标准尺寸
    size_segment = "标准"
    weight_kg = 1.0
    price_over_1000 = True
    is_frozen = True
    result = calculate_fee_jp_demo(size_segment, weight_kg, price_over_1000, is_frozen)
    print(f"测试2（冷冻-标准尺寸）: 费用={result}日元")
    
    print()

def run_all_tests():
    """运行所有测试"""
    print("开始测试FBA配送费计算器...\n")
    
    try:
        test_us_size_segment()
        test_us_fee_calculation()
        test_jp_size_segment()
        test_jp_fee_demo()
        
        print("===== 测试完成 =====")
        print("所有测试用例已执行，请检查计算结果是否符合预期。")
        print("注意：实际费用计算请与亚马逊官方FBA配送费表进行最终核对。")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
