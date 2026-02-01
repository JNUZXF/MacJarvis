# File: backend/app/core/machine_id.py
# Purpose: 生成基于机器硬件的唯一标识符，用于绑定用户数据到特定设备
"""
机器ID生成模块

该模块提供基于机器硬件特征生成唯一标识符的功能，确保：
1. 同一台机器始终生成相同的ID
2. 不同机器生成不同的ID
3. 重装系统后ID保持不变（基于硬件特征）
4. 支持跨平台（macOS、Linux、Windows）

生产级特性：
- 多重硬件特征组合（MAC地址、机器序列号、主板UUID等）
- 本地缓存机制（避免重复计算）
- 降级策略（某些特征获取失败时使用备选方案）
- 安全的ID生成（使用SHA256哈希）
"""

import hashlib
import platform
import subprocess
import uuid
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class MachineIDGenerator:
    """
    机器唯一标识符生成器
    
    使用多种硬件特征组合生成稳定的机器ID：
    1. MAC地址（网络接口）
    2. 机器序列号（macOS: IOPlatformSerialNumber）
    3. 主板UUID（Linux: /sys/class/dmi/id/product_uuid）
    4. 硬件UUID（通用备选方案）
    """
    
    # 缓存文件路径（存储在用户主目录）
    CACHE_DIR = Path.home() / ".mac_agent"
    CACHE_FILE = CACHE_DIR / "machine_id"
    
    @classmethod
    def get_machine_id(cls) -> str:
        """
        获取机器唯一ID
        
        优先从缓存读取，缓存不存在时生成新ID并缓存
        
        Returns:
            32位十六进制字符串（SHA256哈希）
        """
        # 尝试从缓存读取
        cached_id = cls._read_from_cache()
        if cached_id:
            logger.debug("machine_id_from_cache", machine_id=cached_id[:8] + "...")
            return cached_id
        
        # 生成新ID
        machine_id = cls._generate_machine_id()
        
        # 保存到缓存
        cls._save_to_cache(machine_id)
        
        logger.info(
            "machine_id_generated",
            machine_id_prefix=machine_id[:8],
            platform=platform.system()
        )
        
        return machine_id
    
    @classmethod
    def _generate_machine_id(cls) -> str:
        """
        生成机器ID
        
        组合多种硬件特征并生成SHA256哈希
        """
        features = []
        
        # 1. 获取MAC地址
        mac_address = cls._get_mac_address()
        if mac_address:
            features.append(f"mac:{mac_address}")
        
        # 2. 获取机器序列号（macOS特有）
        if platform.system() == "Darwin":
            serial = cls._get_macos_serial()
            if serial:
                features.append(f"serial:{serial}")
        
        # 3. 获取主板UUID（Linux特有）
        elif platform.system() == "Linux":
            board_uuid = cls._get_linux_board_uuid()
            if board_uuid:
                features.append(f"board:{board_uuid}")
        
        # 4. 获取机器UUID（通用备选）
        machine_uuid = cls._get_machine_uuid()
        if machine_uuid:
            features.append(f"uuid:{machine_uuid}")
        
        # 5. 添加主机名作为额外特征
        hostname = platform.node()
        if hostname:
            features.append(f"host:{hostname}")
        
        # 如果所有特征都获取失败，使用随机UUID（不推荐，但保证可用）
        if not features:
            logger.warning("machine_id_fallback_to_random")
            features.append(f"random:{uuid.uuid4().hex}")
        
        # 组合所有特征并生成哈希
        combined = "|".join(features)
        machine_id = hashlib.sha256(combined.encode()).hexdigest()
        
        logger.debug(
            "machine_id_features",
            feature_count=len(features),
            features=[f.split(":")[0] for f in features]
        )
        
        return machine_id
    
    @classmethod
    def _get_mac_address(cls) -> Optional[str]:
        """
        获取主网络接口的MAC地址
        
        Returns:
            MAC地址字符串（格式：xx:xx:xx:xx:xx:xx）或None
        """
        try:
            # 使用uuid.getnode()获取MAC地址（48位整数）
            mac_int = uuid.getnode()
            
            # 转换为标准MAC地址格式
            mac_hex = f"{mac_int:012x}"
            mac_address = ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
            
            # 验证MAC地址有效性（不是全0或全F）
            if mac_address not in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
                return mac_address
            
        except Exception as e:
            logger.warning("failed_to_get_mac_address", error=str(e))
        
        return None
    
    @classmethod
    def _get_macos_serial(cls) -> Optional[str]:
        """
        获取macOS设备序列号
        
        使用ioreg命令获取IOPlatformSerialNumber
        
        Returns:
            序列号字符串或None
        """
        try:
            result = subprocess.run(
                ["ioreg", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 搜索IOPlatformSerialNumber
                for line in result.stdout.split("\n"):
                    if "IOPlatformSerialNumber" in line:
                        # 格式："IOPlatformSerialNumber" = "C02XY1234567"
                        parts = line.split("=")
                        if len(parts) == 2:
                            serial = parts[1].strip().strip('"')
                            if serial and serial != "System Serial Number":
                                return serial
        
        except Exception as e:
            logger.warning("failed_to_get_macos_serial", error=str(e))
        
        return None
    
    @classmethod
    def _get_linux_board_uuid(cls) -> Optional[str]:
        """
        获取Linux主板UUID
        
        从/sys/class/dmi/id/product_uuid读取
        
        Returns:
            UUID字符串或None
        """
        try:
            uuid_file = Path("/sys/class/dmi/id/product_uuid")
            if uuid_file.exists():
                board_uuid = uuid_file.read_text().strip()
                if board_uuid:
                    return board_uuid
        
        except Exception as e:
            logger.warning("failed_to_get_linux_board_uuid", error=str(e))
        
        return None
    
    @classmethod
    def _get_machine_uuid(cls) -> Optional[str]:
        """
        获取机器UUID（通用方法）
        
        尝试多种方式获取系统UUID
        
        Returns:
            UUID字符串或None
        """
        try:
            system = platform.system()
            
            if system == "Darwin":
                # macOS: 使用IOPlatformUUID
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "IOPlatformUUID" in line:
                            parts = line.split("=")
                            if len(parts) == 2:
                                machine_uuid = parts[1].strip().strip('"')
                                if machine_uuid:
                                    return machine_uuid
            
            elif system == "Linux":
                # Linux: 尝试读取machine-id
                machine_id_file = Path("/etc/machine-id")
                if machine_id_file.exists():
                    return machine_id_file.read_text().strip()
                
                # 备选：/var/lib/dbus/machine-id
                dbus_id_file = Path("/var/lib/dbus/machine-id")
                if dbus_id_file.exists():
                    return dbus_id_file.read_text().strip()
            
            elif system == "Windows":
                # Windows: 使用wmic获取UUID
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if len(lines) >= 2:
                        machine_uuid = lines[1].strip()
                        if machine_uuid:
                            return machine_uuid
        
        except Exception as e:
            logger.warning("failed_to_get_machine_uuid", error=str(e))
        
        return None
    
    @classmethod
    def _read_from_cache(cls) -> Optional[str]:
        """
        从缓存文件读取机器ID
        
        Returns:
            缓存的机器ID或None
        """
        try:
            if cls.CACHE_FILE.exists():
                machine_id = cls.CACHE_FILE.read_text().strip()
                
                # 验证格式（64位十六进制）
                if len(machine_id) == 64 and all(c in "0123456789abcdef" for c in machine_id):
                    return machine_id
                else:
                    logger.warning(
                        "invalid_cached_machine_id",
                        length=len(machine_id)
                    )
        
        except Exception as e:
            logger.warning("failed_to_read_machine_id_cache", error=str(e))
        
        return None
    
    @classmethod
    def _save_to_cache(cls, machine_id: str) -> None:
        """
        保存机器ID到缓存文件
        
        Args:
            machine_id: 要保存的机器ID
        """
        try:
            # 确保缓存目录存在
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            # 写入缓存文件
            cls.CACHE_FILE.write_text(machine_id)
            
            # 设置文件权限（仅用户可读写）
            cls.CACHE_FILE.chmod(0o600)
            
            logger.debug("machine_id_cached", cache_file=str(cls.CACHE_FILE))
        
        except Exception as e:
            logger.warning(
                "failed_to_save_machine_id_cache",
                error=str(e),
                cache_file=str(cls.CACHE_FILE)
            )
    
    @classmethod
    def clear_cache(cls) -> bool:
        """
        清除缓存的机器ID
        
        用于测试或重置场景
        
        Returns:
            True if cache was cleared, False otherwise
        """
        try:
            if cls.CACHE_FILE.exists():
                cls.CACHE_FILE.unlink()
                logger.info("machine_id_cache_cleared")
                return True
        
        except Exception as e:
            logger.error("failed_to_clear_machine_id_cache", error=str(e))
        
        return False


# 便捷函数
def get_machine_id() -> str:
    """
    获取当前机器的唯一标识符
    
    这是模块的主要入口函数，推荐使用此函数而非直接调用类方法
    
    Returns:
        64位十六进制字符串（SHA256哈希）
        
    Example:
        >>> machine_id = get_machine_id()
        >>> print(f"Machine ID: {machine_id[:16]}...")
        Machine ID: a1b2c3d4e5f6g7h8...
    """
    return MachineIDGenerator.get_machine_id()


def clear_machine_id_cache() -> bool:
    """
    清除缓存的机器ID
    
    Returns:
        True if cache was cleared, False otherwise
    """
    return MachineIDGenerator.clear_cache()
