import time
import random
import logging
import functools
from typing import Callable, Any, List, Optional, Type

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('retry_utils')

class RetryError(Exception):
    """重试失败异常"""
    pass

def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    exceptions: List[Type[Exception]] = None,
    log_level: int = logging.WARNING
) -> Callable:
    """
    API调用重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避乘数，每次重试延迟增加的倍数
        jitter: 抖动因子，随机调整延迟时间，避免雪崩效应
        exceptions: 需要捕获并重试的异常类型列表，默认为Exception
        log_level: 重试日志级别
    
    Returns:
        装饰后的函数
    """
    if exceptions is None:
        exceptions = [Exception]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):  # +1 因为第一次不算重试
                try:
                    # 尝试执行原函数
                    return func(*args, **kwargs)
                    
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    # 如果是最后一次尝试，则抛出异常
                    if attempt >= max_retries:
                        error_message = f"函数 {func.__name__} 达到最大重试次数 {max_retries} 次后失败: {str(e)}"
                        logger.error(error_message)
                        raise RetryError(error_message) from e
                    
                    # 计算抖动延迟
                    jitter_delay = current_delay * (1 + random.uniform(-jitter, jitter))
                    
                    # 记录重试信息
                    logger.log(
                        log_level,
                        f"函数 {func.__name__} 第 {attempt + 1}/{max_retries} 次重试失败: {str(e)}. "
                        f"将在 {jitter_delay:.2f} 秒后重试..."
                    )
                    
                    # 等待后重试
                    time.sleep(jitter_delay)
                    
                    # 更新下一次的延迟时间
                    current_delay *= backoff
            
            # 这行代码理论上不会执行到，因为最后一次失败会在循环中抛出异常
            raise RetryError(f"函数 {func.__name__} 重试失败") from last_exception
        
        return wrapper
    
    return decorator

class RetryManager:
    """
    API调用重试管理器
    提供更灵活的重试策略配置
    """
    
    # 预定义的重试策略
    DEFAULT_STRATEGIES = {
        'default': {
            'max_retries': 3,
            'delay': 1.0,
            'backoff': 2.0,
            'jitter': 0.1
        },
        'network': {
            'max_retries': 5,
            'delay': 2.0,
            'backoff': 1.5,
            'jitter': 0.2
        },
        'api_heavy': {
            'max_retries': 4,
            'delay': 3.0,
            'backoff': 1.2,
            'jitter': 0.15
        }
    }
    
    def __init__(self, strategy_name: str = 'default'):
        """
        初始化重试管理器
        
        Args:
            strategy_name: 预定义策略名称
        """
        if strategy_name not in self.DEFAULT_STRATEGIES:
            logger.warning(f"未知的重试策略 '{strategy_name}'，使用默认策略")
            strategy_name = 'default'
        
        self.strategy = self.DEFAULT_STRATEGIES[strategy_name].copy()
        logger.info(f"初始化重试管理器，使用策略: {strategy_name}")
    
    def set_strategy(self, **kwargs) -> 'RetryManager':
        """
        设置自定义重试策略
        
        Args:
            **kwargs: 重试策略参数 (max_retries, delay, backoff, jitter)
        
        Returns:
            重试管理器实例（支持链式调用）
        """
        for key, value in kwargs.items():
            if key in self.strategy:
                self.strategy[key] = value
        
        logger.info(f"更新重试策略: {self.strategy}")
        return self
    
    def retry_on(self, exceptions: List[Type[Exception]] = None) -> Callable:
        """
        创建重试装饰器
        
        Args:
            exceptions: 需要捕获并重试的异常类型列表
        
        Returns:
            装饰器函数
        """
        return retry(
            max_retries=self.strategy['max_retries'],
            delay=self.strategy['delay'],
            backoff=self.strategy['backoff'],
            jitter=self.strategy['jitter'],
            exceptions=exceptions
        )

# 创建预定义的重试管理器实例
default_retry_manager = RetryManager('default')
network_retry_manager = RetryManager('network')
api_heavy_retry_manager = RetryManager('api_heavy')

# 提供便捷的装饰器函数
def api_retry(func: Callable) -> Callable:
    """API调用默认重试装饰器"""
    return default_retry_manager.retry_on()(func)

def network_retry(func: Callable) -> Callable:
    """网络请求重试装饰器（更适合网络不稳定情况）"""
    return network_retry_manager.retry_on()(func)

def api_heavy_retry(func: Callable) -> Callable:
    """针对API限流敏感的重试装饰器"""
    return api_heavy_retry_manager.retry_on()(func)

# 使用示例
if __name__ == '__main__':
    # 示例1：使用装饰器
    @api_retry
    def example_api_call(param):
        print(f"执行API调用，参数: {param}")
        # 模拟随机失败
        if random.random() < 0.7:
            raise ConnectionError("模拟网络连接失败")
        return f"成功，返回: {param}"
    
    # 示例2：使用自定义重试管理器
    custom_retry = RetryManager()
    custom_retry.set_strategy(max_retries=5, delay=0.5)
    
    @custom_retry.retry_on([ValueError, TypeError])
    def example_with_custom_retry(value):
        print(f"执行带自定义重试的函数，值: {value}")
        # 模拟特定异常
        if isinstance(value, int) and value < 0:
            raise ValueError("值不能为负数")
        return f"成功处理: {value}"
    
    # 测试示例
    print("测试默认API重试:")
    try:
        result = example_api_call("test-data")
        print(f"最终结果: {result}")
    except RetryError as e:
        print(f"重试失败: {e}")
    
    print("\n测试自定义重试:")
    try:
        result = example_with_custom_retry(42)
        print(f"正常值结果: {result}")
        
        result = example_with_custom_retry(-10)
        print(f"负值结果: {result}")
    except RetryError as e:
        print(f"重试失败: {e}")
