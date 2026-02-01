# File: backend/tests/test_machine_id.py
# Purpose: 测试机器ID生成功能
"""
机器ID生成功能测试

测试内容：
1. 机器ID生成的一致性
2. 缓存机制的有效性
3. 多次调用返回相同ID
4. 缓存清除功能
"""

import pytest
from pathlib import Path
from app.core.machine_id import (
    get_machine_id,
    clear_machine_id_cache,
    MachineIDGenerator
)


class TestMachineID:
    """机器ID生成测试套件"""
    
    def test_machine_id_generation(self):
        """测试机器ID生成"""
        machine_id = get_machine_id()
        
        # 验证ID格式（64位十六进制字符串）
        assert isinstance(machine_id, str)
        assert len(machine_id) == 64
        assert all(c in "0123456789abcdef" for c in machine_id)
        
        print(f"✓ 机器ID生成成功: {machine_id[:16]}...")
    
    def test_machine_id_consistency(self):
        """测试机器ID的一致性（多次调用返回相同ID）"""
        id1 = get_machine_id()
        id2 = get_machine_id()
        id3 = get_machine_id()
        
        assert id1 == id2 == id3
        print(f"✓ 机器ID一致性验证通过: {id1[:16]}...")
    
    def test_cache_mechanism(self):
        """测试缓存机制"""
        # 清除缓存
        clear_machine_id_cache()
        
        # 第一次生成（应该从硬件特征生成）
        id1 = get_machine_id()
        
        # 验证缓存文件存在
        cache_file = MachineIDGenerator.CACHE_FILE
        assert cache_file.exists()
        
        # 第二次获取（应该从缓存读取）
        id2 = get_machine_id()
        
        assert id1 == id2
        print(f"✓ 缓存机制验证通过: {id1[:16]}...")
    
    def test_cache_clear(self):
        """测试缓存清除功能"""
        # 生成ID（创建缓存）
        id1 = get_machine_id()
        
        # 清除缓存
        success = clear_machine_id_cache()
        assert success
        
        # 验证缓存文件已删除
        cache_file = MachineIDGenerator.CACHE_FILE
        assert not cache_file.exists()
        
        # 重新生成ID（应该与之前相同，因为基于硬件特征）
        id2 = get_machine_id()
        assert id1 == id2
        
        print(f"✓ 缓存清除功能验证通过")
    
    def test_cache_directory_creation(self):
        """测试缓存目录自动创建"""
        # 确保缓存目录存在
        cache_dir = MachineIDGenerator.CACHE_DIR
        
        # 即使目录不存在，get_machine_id也应该能创建它
        machine_id = get_machine_id()
        
        assert cache_dir.exists()
        assert cache_dir.is_dir()
        
        print(f"✓ 缓存目录自动创建验证通过: {cache_dir}")
    
    def test_cache_file_permissions(self):
        """测试缓存文件权限（应该是600，仅用户可读写）"""
        # 生成ID
        machine_id = get_machine_id()
        
        # 检查文件权限
        cache_file = MachineIDGenerator.CACHE_FILE
        if cache_file.exists():
            # 在Unix系统上验证权限
            import stat
            file_stat = cache_file.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)
            
            # 0o600 = 用户读写，组和其他无权限
            assert file_mode == 0o600
            
            print(f"✓ 缓存文件权限验证通过: {oct(file_mode)}")


def test_machine_id_display():
    """显示当前机器的ID（用于调试）"""
    machine_id = get_machine_id()
    print(f"\n{'='*60}")
    print(f"当前机器ID: {machine_id}")
    print(f"ID前缀: {machine_id[:16]}")
    print(f"缓存位置: {MachineIDGenerator.CACHE_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
