#!/usr/bin/env python3
"""
Polymarket BTC/ETH 情绪监控系统主入口

使用方法:
    python -m src.main [--config CONFIG_PATH] [--once] [--interval INTERVAL]

选项:
    --config    配置文件路径 (默认: config/config.yaml)
    --once      只运行一次分析
    --interval  定时任务间隔（秒，默认: 300）
"""
import argparse
import sys
import os
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import load_config, Config
from src.scheduler import SentimentMonitor, create_default_config


def setup_logging(debug: bool = False):
    """设置日志"""
    log_level = "DEBUG" if debug else "INFO"
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>"
    )
    
    # 添加文件处理器
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        str(log_dir / "sentiment_monitor.log"),
        level="INFO",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8"
    )


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Polymarket BTC/ETH Sentiment Monitor"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="配置文件路径 (默认: config/config.yaml)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只运行一次分析，不启动定时调度"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="定时任务间隔（秒，默认: 300）"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    return parser.parse_args()


def main():
    """主入口函数"""
    args = parse_args()
    
    # 设置日志
    setup_logging(debug=args.debug)
    
    logger.info("=" * 50)
    logger.info("Starting Polymarket BTC/ETH Sentiment Monitor")
    logger.info("=" * 50)
    
    # 加载配置
    try:
        config_path = project_root / args.config
        if config_path.exists():
            config = load_config(str(config_path))
            logger.info(f"Config loaded from: {config_path}")
        else:
            logger.warning(f"Config file not found: {config_path}")
            logger.warning("Using default config")
            config = create_default_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # 确保数据目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    # 创建监控器
    try:
        monitor = SentimentMonitor(config)
    except Exception as e:
        logger.error(f"Failed to initialize monitor: {e}")
        sys.exit(1)
    
    # 运行模式
    if args.once:
        logger.info("Running in single-shot mode")
        result = monitor.run_once()
        logger.info(f"Analysis completed: {result}")
    else:
        logger.info(f"Running in scheduler mode (interval: {args.interval}s)")
        try:
            monitor.start_scheduler(analysis_interval=args.interval)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            monitor.stop()
    
    logger.info("Program finished")


if __name__ == "__main__":
    main()
