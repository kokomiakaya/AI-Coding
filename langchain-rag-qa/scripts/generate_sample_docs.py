"""生成演示文档（虚构电商商品数据，覆盖 3 种文件类型，便于答辩演示）。

产物输出到 scripts/sample_docs/：
- 商品FAQ.md        —— 常见问答（Markdown）
- 商品信息表.xlsx    —— 商品规格表格（Excel，电商商品信息主场景）
- 商品说明书.pdf     —— 星耀X1手机说明书（PDF，含分页）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from openpyxl import Workbook  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "sample_docs"

FAQ_CONTENT = """# 星耀数码旗舰店 - 商品常见问题（FAQ）

## 星耀X1 手机

### 星耀X1 的电池容量是多少？
星耀X1 手机内置 4500mAh 大容量电池，支持 66W 有线快充，充电 10 分钟可充入 40% 电量，30 分钟可充满 80%。日常使用续航约 1.5 天，重度使用约 1 天。

### 星耀X1 的屏幕参数是什么？
星耀X1 采用 6.7 英寸 AMOLED 曲面屏，分辨率 2772×1280，支持 120Hz 自适应刷新率，峰值亮度 1500 尼特，阳光下依然清晰可见，并通过莱茵低蓝光认证。

### 星耀X1 的价格是多少？
星耀X1 提供三个版本：8GB+256GB 售价 2999 元，12GB+256GB 售价 3299 元，12GB+512GB 售价 3599 元。首发期间赠送原装保护壳与一年碎屏险。

### 星耀X1 支持防水吗？
星耀X1 支持 IP68 级防尘防水，可在 1.5 米深清水中静置 30 分钟，日常雨淋、洗手溅水完全不用担心。

### 星耀X1 的保修政策是什么？
整机保修一年，主要部件（屏幕、主板、电池）保修两年。保修期内非人为损坏免费维修，人为损坏可享受 8 折维修优惠。支持 7 天无理由退货、15 天内质量问题换货。

## 云听P2 无线耳机

### 云听P2 的续航表现如何？
云听P2 单次充电可连续听歌 8 小时，配合充电盒总续航达 36 小时。支持快充：充电 10 分钟可听歌 2 小时。充电盒采用 Type-C 接口，也支持无线充电。

### 云听P2 的降噪效果怎么样？
云听P2 搭载主动降噪技术，降噪深度达 45dB，可有效过滤地铁、公交等环境噪音；同时支持通透模式，不摘耳机也能清晰听到外界声音。

### 云听P2 的价格？
云听P2 标准版售价 499 元，降噪加强版售价 599 元。支持以旧换新，旧耳机最高可抵 200 元。

## 星辰S3 智能手表

### 星辰S3 有哪些健康监测功能？
星辰S3 支持心率监测、血氧监测、睡眠监测、压力监测四大健康功能。心率异常时会主动提醒，所有健康数据可在手机 App 中查看历史趋势。

### 星辰S3 的运动模式有多少种？
星辰S3 内置 120 种运动模式，包括跑步、游泳、骑行、登山、瑜伽等，支持 5ATM 防水，游泳时可以佩戴。

### 星辰S3 的价格与续航？
星辰S3 售价 899 元。典型使用场景下续航 14 天，重度使用约 7 天，磁吸快充 15 分钟可用一整天。

## 物流与售后

### 什么时间发货？
每天 16:00 前下单当日发货，16:00 后下单次日发货。默认顺丰包邮，全国大部分地区 2-3 天送达，偏远地区 3-5 天。

### 可以开发票吗？
支持开具增值税普通发票和增值税专用发票，下单时勾选"需要发票"并填写抬头即可，电子发票在确认收货后 3 个工作日内发送至邮箱。
"""

XLSX_HEADERS = ["商品编号", "商品名称", "类别", "价格(元)", "库存", "保修期", "主要卖点"]
XLSX_ROWS = [
    ["SP-X1-8256", "星耀X1 8+256G", "手机", 2999, 520, "整机1年/主要部件2年", "4500mAh电池、66W快充、IP68防水"],
    ["SP-X1-12256", "星耀X1 12+256G", "手机", 3299, 310, "整机1年/主要部件2年", "4500mAh电池、66W快充、IP68防水"],
    ["SP-X1-12512", "星耀X1 12+512G", "手机", 3599, 180, "整机1年/主要部件2年", "4500mAh电池、66W快充、IP68防水"],
    ["SP-P2-STD", "云听P2 标准版", "耳机", 499, 1200, "1年", "45dB主动降噪、36小时总续航"],
    ["SP-P2-PRO", "云听P2 降噪加强版", "耳机", 599, 860, "1年", "45dB主动降噪、36小时总续航"],
    ["SP-S3-STD", "星辰S3 智能手表", "手表", 899, 450, "1年", "120种运动模式、14天续航、5ATM防水"],
    ["SP-X1-CASE", "星耀X1 原装保护壳", "配件", 69, 3000, "无保修", "TPU软边+PC硬背板"],
]

PDF_PAGES = [
    (
        "星耀X1 手机使用说明书\n\n"
        "【产品概述】\n"
        "感谢您选择星耀X1 手机。本机搭载旗舰级处理器，配备 6.7 英寸 AMOLED 曲面屏，"
        "内置 4500mAh 大容量电池并支持 66W 有线快充，具备 IP68 级防尘防水能力，"
        "为您带来流畅、持久、安心的使用体验。\n\n"
        "【包装清单】\n"
        "手机 ×1、充电器 ×1、数据线 ×1、保护壳 ×1、取卡针 ×1、快速入门指南 ×1、三包凭证 ×1。"
    ),
    (
        "星耀X1 手机使用说明书\n\n"
        "【技术规格】\n"
        "屏幕：6.7 英寸 AMOLED，分辨率 2772×1280，120Hz 自适应刷新率\n"
        "电池：4500mAh，66W 有线快充（30 分钟充至 80%）\n"
        "防水：IP68（1.5 米清水 30 分钟）\n"
        "存储：8GB+256GB / 12GB+256GB / 12GB+512GB\n"
        "颜色：星空黑、晨曦银、流光蓝\n\n"
        "【充电说明】\n"
        "首次使用建议将手机充满电。请使用包装内原装充电器，充电时保持环境通风，"
        "避免边充电边进行大型游戏等高负载操作。"
    ),
    (
        "星耀X1 手机使用说明书\n\n"
        "【使用与保养】\n"
        "1. 请勿在高温、潮湿环境下长时间使用手机。\n"
        "2. 屏幕建议贴膜使用，避免与钥匙等硬物共同存放。\n"
        "3. 手机进水后请立即关机并送修，切勿自行拆机。\n"
        "4. 建议每月重启一次手机以保持系统流畅。\n\n"
        "【安全须知】\n"
        "请勿自行拆卸电池，请勿将手机投入火中。电池出现鼓包、变形请立即停止使用并联系售后。\n\n"
        "【售后服务】\n"
        "整机保修一年，主要部件保修两年。凭购机发票与三包凭证享受全国联保。"
        "客服热线：400-888-6666，服务时间 9:00-21:00。"
    ),
]


def gen_markdown() -> Path:
    path = OUT_DIR / "商品FAQ.md"
    path.write_text(FAQ_CONTENT, encoding="utf-8")
    return path


def gen_xlsx() -> Path:
    path = OUT_DIR / "商品信息表.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "商品清单"
    ws.append(XLSX_HEADERS)
    for row in XLSX_ROWS:
        ws.append(row)
    wb.save(path)
    return path


def gen_pdf() -> Path:
    """用 reportlab 生成（内嵌中文字体 TTF，保证 pypdf 能正确提取文本与页码）。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    path = OUT_DIR / "商品说明书.pdf"
    font_path = Path("C:/Windows/Fonts/simhei.ttf")
    if not font_path.exists():
        print("警告：未找到中文字体 simhei.ttf，PDF 演示文档跳过生成（不影响其他功能）")
        return path
    pdfmetrics.registerFont(TTFont("SimHei", str(font_path)))
    style = ParagraphStyle(
        name="body", fontName="SimHei", fontSize=12, leading=20, wordWrap="CJK"
    )
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=50, bottomMargin=50)
    story = []
    for page_text in PDF_PAGES:
        from reportlab.platypus import PageBreak

        for i, line in enumerate(page_text.split("\n")):
            if i > 0:
                story.append(Spacer(1, 4))
            story.append(Paragraph(line.replace("&", "&amp;"), style))
        story.append(PageBreak())
    story.pop()  # 去掉最后多余的分页符
    doc.build(story)
    return path


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for gen in (gen_markdown, gen_xlsx, gen_pdf):
        p = gen()
        if p.exists():
            print(f"已生成：{p.name}")
    print(f"演示文档目录：{OUT_DIR}")
