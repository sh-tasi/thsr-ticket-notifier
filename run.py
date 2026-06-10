"""本機 / CI 入口：python run.py

把 src 加進匯入路徑後執行主流程，免去設定 PYTHONPATH。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from thsr_notifier.main import main

if __name__ == "__main__":
    raise SystemExit(main())
