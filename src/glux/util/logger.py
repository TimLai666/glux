"""
日誌記錄器模組
提供格式化的日誌記錄功能
"""

import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime


class Logger:
    """
    日誌記錄器類
    提供統一的日誌記錄介面
    """
    
    def __init__(self, name: str, level: int = logging.INFO, console: bool = True, file: Optional[str] = None):
        """
        初始化日誌記錄器
        
        Args:
            name: 日誌記錄器名稱
            level: 日誌級別
            console: 是否輸出到控制台
            file: 日誌文件路徑（可選）
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []  # 清除可能存在的處理器
        
        # 日誌格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 控制台輸出
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 文件輸出
        if file:
            file_handler = logging.FileHandler(file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str) -> None:
        """輸出調試信息"""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """輸出一般信息"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """輸出警告信息"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """輸出錯誤信息"""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """輸出嚴重錯誤信息"""
        self.logger.critical(message)
    
    def log(self, level: int, message: str) -> None:
        """按指定級別輸出日誌"""
        self.logger.log(level, message)
    
    @staticmethod
    def get_datetime() -> str:
        """獲取當前日期時間字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def setup_global_logging(level: int = logging.INFO) -> None:
        """設置全局日誌配置"""
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ) 