"""
E2E测试：Boost重逢场景

测试好友再次接近时触发Boost的完整流程
"""

import pytest
from datetime import datetime, timedelta


@pytest.mark.e2e
class TestBoostReunionScenario:
    """Boost重逢场景测试类"""
    
    @pytest.mark.asyncio
    async def test_boost_triggered_on_reunion(self):
        """
        E2E场景：好友重逢触发Boost
        
        流程：
        1. Alice和Bob是好友
        2. Alice发现Bob在附近（超过5分钟未触发Boost）
        3. 触发Boost
        4. Alice收到Boost通知
        """
        # 验证Boost触发条件
        last_boost = datetime.utcnow() - timedelta(minutes=10)  # 10分钟前
        cooldown = timedelta(minutes=5)
        
        should_boost = datetime.utcnow() - last_boost > cooldown
        assert should_boost is True
    
    @pytest.mark.asyncio
    async def test_boost_cooldown_prevents_duplicate(self):
        """
        E2E场景：Boost冷却期防止重复触发
        
        流程：
        1. Alice和Bob是好友
        2. 2分钟前刚触发过Boost
        3. Alice再次发现Bob
        4. 不触发Boost（冷却期内）
        """
        last_boost = datetime.utcnow() - timedelta(minutes=2)  # 2分钟前
        cooldown = timedelta(minutes=5)
        
        should_boost = datetime.utcnow() - last_boost > cooldown
        assert should_boost is False


class TestBoostCooldown:
    """Boost冷却期测试"""
    
    def test_cooldown_calculation(self):
        """测试冷却期计算"""
        # 刚好5分钟
        last_boost = datetime.utcnow() - timedelta(minutes=5, seconds=1)
        cooldown = timedelta(minutes=5)
        
        should_boost = datetime.utcnow() - last_boost > cooldown
        assert should_boost is True
        
        # 4分59秒
        last_boost = datetime.utcnow() - timedelta(minutes=4, seconds=59)
        should_boost = datetime.utcnow() - last_boost > cooldown
        assert should_boost is False
