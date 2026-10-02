# monet-palette

Material Design 3 动态取色的设备用的取色工具。
输入一张壁纸，输出一套 M3 配色（浅色 + 深色）。

## 说明

代码在编写过程中使用了 AI 辅助工具，所有代码经过作者审阅、测试和调整。

## 算法流程

```
图片
 └─ 降采样 ────────────── 长边缩到 256px，加速量化
     └─ Wu 量化 ────────── 32³ 5-bit 直方图 + 最优切分 → N 个色簇
         └─ K-Means 精炼 ─ 以 Wu 结果为初值微调簇心（对应 WSMeans）
             └─ 种子色评分 ─ 色相兴奋度 + 色度偏离度，选出种子色
                 └─ CorePalette ── 派生 5 组色调调色板
                     └─ 角色映射 ── 按 M3 规则表生成浅色/深色主题
```

核心色彩空间是 **HCT**（Hue–Chroma–Tone）：

| 分量 | 来源         | 作用                       |
| ---- | ------------ | -------------------------- |
| H    | CAM16 色相   | 保证不同明度下色相观感一致 |
| C    | CAM16 色度   | 控制饱和度                 |
| T    | CIE L\* 明度 | 控制明暗，与对比度直接相关 |

调色板生成时先固定 `(H, C)`，再对 `T = 0, 10, 20, …, 100` 逐档求色；
若某个 `(H, C, T)` 在 sRGB 中不可表示，会自动降低 C 直到落回色域——
这是 Monet 在极端明度下依然能产出合法颜色的关键。

## 安装

```bash
pip install -r requirements.txt
# 或者安装成可编辑包，获得 `monet-palette` 命令
pip install -e .
```

## 三种用法

### ① 直接运行

1. 打开项目根目录
2. 编辑 `main.py` 顶部的 `DEFAULT_IMAGE`，指到你的图片
3. `main.py` → **Run 'main'**

终端会输出带色块的配色，并在项目根目录生成 `theme.css` 和 `preview.png`。

> 传参运行：`Run` → `Edit Configurations…` → `Parameters` 填 `wallpaper.jpg --print`

### ② 终端命令

```bash
# 不安装，直接使用模块
python -m monet_palette wallpaper.jpg --print
python -m monet_palette wallpaper.jpg -o out/          # 一键导出三件套

# 或者安装成全局命令
pip install -e .
monet-palette wallpaper.jpg --css theme.css --preview preview.png

# 顶层脚本
python main.py wallpaper.jpg --print
```

### ③ 函数 API

```python
import monet_palette as mp

result = mp.generate("wallpaper.jpg")

print([mp.to_hex(s.to_rgb()) for s in result.seeds])
print("primary :", mp.to_hex(result.light["primary"]))
print("surface :", mp.to_hex(result.dark["surface"]))

open("theme.css", "w").write(mp.to_css(result))
mp.render_preview(result, "preview.png")
```

## 命令行参数

| 参数               | 说明                                                       |
| ------------------ | ---------------------------------------------------------- |
| `image`          | 输入图片路径                                               |
| `-n, --colors`   | 量化颜色数（默认 128）                                     |
| `-s, --seeds`    | 保留的种子色数量（默认 4）                                 |
| `--content`      | 使用 content 风格，更忠实原图色度                          |
| `--no-refine`    | 跳过 K-Means 精炼                                          |
| `--max-side`     | 分析前的图片最长边（默认 256）                             |
| `-o, --out DIR`  | 一键导出`DIR/theme.css`、`theme.json`、`preview.png` |
| `--json FILE`    | 导出 JSON                                                  |
| `--css FILE`     | 导出 CSS 变量                                              |
| `--preview FILE` | 导出预览图                                                 |
| `--print`        | 在终端打印配色                                             |

## 项目结构

```
monet-palette/
├── main.py                   
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── requirements.txt
│
├── monet_palette/           
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── color.py
│   ├── engine.py
│   ├── export.py
│   ├── quantize.py
│   ├── scheme.py
│   └── score.py
│
├── tests/                     
│   ├── __init__.py
│   ├── conftest.py
│   └── test_smoke.py
│
└── examples/                  
    ├── basic.py
    └── hiro.jpg               
```

## 参考

- [material-foundation/material-color-utilities](https://github.com/material-foundation/material-color-utilities) —— 官方算法库
- Material Design 3 色彩系统文档
- Wu, Xiaolin. "Efficient statistical computation for optimal color quantization."
- Li et al. "Comprehensive color solutions: CAM16, CAT16, and CAM16-UCS."
