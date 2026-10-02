"""让 `python -m monet_palette` 等价于命令行工具。"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())