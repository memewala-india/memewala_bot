from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

FONT_PATH = "fonts/NotoSansDevanagari-Bold.ttf"
OUTPUT_DIR = "output"


def _get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(text, width):
    return textwrap.fill(text, width=width)


def generate_meme(template_path, top_text, bottom_text, user_id, watermark=True):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    font_size = max(28, int(width * 0.075))
    font = _get_font(font_size)
    stroke = max(2, font_size // 12)
    
    if top_text:
        wrapped = _wrap_text(top_text.upper(), width=int(width / (font_size * 0.55)))
        draw.text(
            (width / 2, int(height * 0.03)),
            wrapped,
            font=font,
            fill="white",
            anchor="ma",
            stroke_width=stroke,
            stroke_fill="black",
            align="center",
        )
    
    if bottom_text:
        wrapped = _wrap_text(bottom_text.upper(), width=int(width / (font_size * 0.55)))
        draw.text(
            (width / 2, int(height * 0.97)),
            wrapped,
            font=font,
            fill="white",
            anchor="md",
            stroke_width=stroke,
            stroke_fill="black",
            align="center",
        )
    
    if watermark:
        wm_font = _get_font(max(16, font_size // 3))
        wm_text = "@MemeWalaIndiaBot"
        draw.text(
            (width - 12, height - 12),
            wm_text,
            font=wm_font,
            fill=(255, 255, 255),
            anchor="rd",
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )
    
    output_path = f"{OUTPUT_DIR}/meme_{user_id}.jpg"
    img.save(output_path, "JPEG", quality=90)
    return output_path