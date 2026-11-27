"""
Gerador automático de Card Visual de Ofertas (1080x1080 PNG) para WhatsApp/Telegram.
Combina foto limpa do produto + selo de desconto + preço riscado + preço atual + economia em reais.
"""

import hashlib
import io
import logging
import os
import tempfile
import textwrap
from pathlib import Path
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def _format_brl(value):
    num = float(value)
    return f'R$ {num:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _load_font(size, bold=False):
    from PIL import ImageFont

    candidates = (
        ['segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf']
        if bold
        else ['segoeui.ttf', 'arial.ttf', 'DejaVuSans.ttf']
    )
    win_fonts = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
    for name in candidates:
        for base in (win_fonts, Path('/usr/share/fonts/truetype/dejavu')):
            candidate_path = base / name
            if candidate_path.exists():
                try:
                    return ImageFont.truetype(str(candidate_path), size=size)
                except Exception:
                    continue
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _download_image_bytes(url, timeout=10):
    if not url or not str(url).startswith(('http://', 'https://')):
        return None
    req = Request(
        str(url),
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
            )
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data if data and len(data) > 512 else None


def generate_offer_card_image(
    title,
    price,
    original_price=None,
    discount_pct=0,
    store_label='',
    thumbnail_url='',
    coupon='',
    brand_name='GARIMPO DE OFERTAS',
):
    """
    Gera um card visual 1080x1080 PNG em pasta temporária e retorna o caminho absoluto.
    Retorna None caso a imagem do produto não possa ser baixada ou processada.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning('Pillow não instalado; pulando geração de card visual.')
        return None

    try:
        raw_bytes = _download_image_bytes(thumbnail_url)
        if not raw_bytes:
            return None
        prod_img = Image.open(io.BytesIO(raw_bytes)).convert('RGBA')
    except Exception:
        logger.warning('Não foi possível baixar thumbnail para o card visual: %s', thumbnail_url)
        return None

    try:
        W, H = 1080, 1080
        TOP_H = 690
        canvas = Image.new('RGB', (W, H), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # Área superior branca com foto do produto centralizada
        max_w, max_h = 840, 520
        prod_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        bg_paste = Image.new('RGB', prod_img.size, (255, 255, 255))
        bg_paste.paste(prod_img, mask=prod_img.split()[3] if prod_img.mode == 'RGBA' else None)
        px = (W - prod_img.width) // 2
        py = 115 + (max_h - prod_img.height) // 2
        canvas.paste(bg_paste, (px, py))

        # Selo de desconto (topo esquerdo)
        price_val = float(price)
        orig_val = float(original_price) if original_price else None
        calc_discount = int(discount_pct or 0)
        if not calc_discount and orig_val and orig_val > price_val > 0:
            calc_discount = round(((orig_val - price_val) / orig_val) * 100)

        font_badge = _load_font(34, bold=True)
        font_store = _load_font(28, bold=True)
        font_title = _load_font(38, bold=True)
        font_old = _load_font(32, bold=False)
        font_now = _load_font(74, bold=True)
        font_save = _load_font(28, bold=True)
        font_brand = _load_font(24, bold=True)

        if calc_discount > 0:
            badge_text = f'-{calc_discount}% OFF'
            bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
            bw = (bbox[2] - bbox[0]) + 46
            bh = (bbox[3] - bbox[1]) + 26
            draw.rounded_rectangle([38, 36, 38 + bw, 36 + bh], radius=14, fill=(220, 38, 38))
            draw.text((38 + 23, 36 + 11), badge_text, font=font_badge, fill=(255, 255, 255))

        if store_label:
            st_text = str(store_label).strip()
            bbox = draw.textbbox((0, 0), st_text, font=font_store)
            sw = (bbox[2] - bbox[0]) + 42
            sh = (bbox[3] - bbox[1]) + 24
            sx = W - 38 - sw
            draw.rounded_rectangle([sx, 38, sx + sw, 38 + sh], radius=12, fill=(15, 23, 42))
            draw.text((sx + 21, 38 + 10), st_text, font=font_store, fill=(255, 255, 255))

        # Faixa inferior escura limpa (alto contraste e legibilidade no celular)
        draw.rectangle([0, TOP_H, W, H], fill=(15, 23, 42))
        draw.rectangle([0, TOP_H, W, TOP_H + 6], fill=(16, 185, 129))

        # Título limpo em até 2 linhas
        clean_title = ' '.join(str(title or '').split())
        wrapped = textwrap.wrap(clean_title, width=42)[:2]
        if len(wrapped) == 2 and len(clean_title) > 84:
            wrapped[1] = wrapped[1].rstrip(' .,;:-') + '...'

        ty = TOP_H + 34
        for line in wrapped:
            draw.text((48, ty), line, font=font_title, fill=(248, 250, 252))
            ty += 48

        # Preço antigo riscado + preço atual em verde esmeralda
        price_y = TOP_H + 150
        if orig_val and orig_val > price_val:
            old_text = f'De {_format_brl(orig_val)}'
            draw.text((48, price_y), old_text, font=font_old, fill=(148, 163, 184))
            ob = draw.textbbox((48, price_y), old_text, font=font_old)
            mid_y = (ob[1] + ob[3]) // 2 + 2
            draw.line([(ob[0], mid_y), (ob[2], mid_y)], fill=(148, 163, 184), width=3)
            price_y += 42

        now_text = _format_brl(price_val)
        draw.text((48, price_y), now_text, font=font_now, fill=(52, 211, 153))

        # Pill de economia em reais (e/ou cupom) à direita
        savings = (orig_val - price_val) if (orig_val and orig_val > price_val) else 0
        pill_x = 48
        pill_y = H - 72
        if savings >= 5:
            save_text = f'Economize {_format_brl(savings)}'
            sb = draw.textbbox((0, 0), save_text, font=font_save)
            sw = (sb[2] - sb[0]) + 34
            sh = (sb[3] - sb[1]) + 18
            draw.rounded_rectangle([pill_x, pill_y, pill_x + sw, pill_y + sh], radius=10, fill=(6, 95, 70))
            draw.text((pill_x + 17, pill_y + 7), save_text, font=font_save, fill=(209, 250, 229))
            pill_x += sw + 16

        if coupon:
            cp_text = f'CUPOM: {str(coupon).strip()[:18]}'
            cb = draw.textbbox((0, 0), cp_text, font=font_save)
            cw = (cb[2] - cb[0]) + 34
            ch = (cb[3] - cb[1]) + 18
            draw.rounded_rectangle([pill_x, pill_y, pill_x + cw, pill_y + ch], radius=10, fill=(234, 88, 12))
            draw.text((pill_x + 17, pill_y + 7), cp_text, font=font_save, fill=(255, 255, 255))

        # Assinatura discreta da marca no canto inferior direito
        brand_str = str(brand_name or 'GARIMPO DE OFERTAS').upper()
        bb = draw.textbbox((0, 0), brand_str, font=font_brand)
        bw = bb[2] - bb[0]
        draw.text((W - 48 - bw, H - 62), brand_str, font=font_brand, fill=(148, 163, 184))

        digest = hashlib.md5(f'{clean_title}|{price_val}|{thumbnail_url}'.encode('utf-8')).hexdigest()[:12]
        out_path = Path(tempfile.gettempdir()) / f'garimpo_card_{digest}.png'
        canvas.save(str(out_path), format='PNG', optimize=True)
        return str(out_path)
    except Exception:
        logger.warning('Falha ao renderizar card visual da oferta.', exc_info=True)
        return None
