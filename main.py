#!/usr/bin/env python3
"""# monet-palette 入口。

三种用法：
    1. 直接Run —— 无参数时走 DEFAULT_IMAGE
    2. 终端传参  python main.py wallpaper.jpg --css theme.css
    3. 命令行解析全部委托给 monet_palette.cli

把想默认处理的图片路径填到下面的 DEFAULT_IMAGE 里,之后RUN就能直接看到结果。
"""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# 让 `python main.py` 在任意工作目录下都能找到 monet_palette 包
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from monet_palette.cli import main as cli_main  # noqa: E402

# ---------------------------------------------------------------------------
# ★ PyCharm 直接运行时使用的默认参数 ★
# ---------------------------------------------------------------------------
DEFAULT_IMAGE = "./examples/hiro.jpg"   # ← 换成你自己的图片路径
DEFAULT_ARGS = [
    "--print",                    # 终端里打印带色块的配色
    "--css", "theme.css",         # 顺手导出 CSS
    "--preview", "preview.png",   # 顺手导出预览图
]

def _resolve_default_image() -> str | None:
    """默认图片不存在时，自动找同目录下任意一张常见格式的图片。"""
    if os.path.exists(DEFAULT_IMAGE):
        return DEFAULT_IMAGE
    for name in sorted(os.listdir(_HERE)):
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
            print(f"[main] 未找到 {DEFAULT_IMAGE}，改用 {name}", file=sys.stderr)
            return name
    return None

def run() -> int:
    argv = sys.argv[1:]

    # 没有任何参数 → 走 PyCharm 默认流程
    if not argv:
        image = _resolve_default_image()
        if image is None:
            print(
                "用法: python main.py <图片路径> [选项]\n"
                "或在 main.py 里修改 DEFAULT_IMAGE。",
                file=sys.stderr,
            )
            return 1
        argv = [image, *DEFAULT_ARGS]

    return cli_main(argv)

if __name__ == "__main__":
    raise SystemExit(run())