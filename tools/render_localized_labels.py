#!/usr/bin/env python3
"""Replace explicitly authored texture-label rectangles, retaining other pixels.

Rules contain individually reviewed text, bounds and background sample columns.
This tool requires an explicit source digest and refuses existing outputs.
It does not infer translations, change palettes or launch the game.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from freetype import Face


def mixed_text_layer(text, fonts, faces, fill, stroke, stroke_width):
    """Render explicit fallback runs on a common baseline, with no tofu glyphs."""
    assert '\n' not in text, 'Mixed-font labels currently require a single line'
    runs = []
    for character in text:
        index = next((i for i, face in enumerate(faces)
                      if face.get_char_index(ord(character))), None)
        assert index is not None, ('Missing font glyph', character)
        if runs and runs[-1][0] == index:
            runs[-1][1] += character
        else:
            runs.append([index, character])
    lengths = [font.getlength(run) for i, run in runs for font in [fonts[i]]]
    ascent = max(font.getmetrics()[0] for font in fonts)
    descent = max(font.getmetrics()[1] for font in fonts)
    padding = stroke_width + 2
    layer = Image.new('RGBA', (math.ceil(sum(lengths))+2*padding,
                             ascent+descent+2*padding))
    draw = ImageDraw.Draw(layer)
    x = padding
    for (index, run), length in zip(runs, lengths):
        draw.text((x, padding+ascent), run, font=fonts[index], anchor='ls',
                  fill=fill, stroke_width=stroke_width, stroke_fill=stroke)
        x += length
    bounds = layer.getchannel('A').getbbox()
    assert bounds, 'Label has no visible glyphs'
    return layer.crop(bounds)


def heal_lettering(source, box, minimum=195):
    """Fill a reviewed lettering mask from adjacent unmasked background pixels."""
    crop = source.crop(box)
    ink = Image.new('L',crop.size)
    for y in range(crop.height):
        for x in range(crop.width):
            color = crop.getpixel((x,y))
            if min(color[:3]) >= minimum:
                ink.putpixel((x,y),255)
    ink = ink.filter(ImageFilter.MaxFilter(5))
    pending = {(x,y) for y in range(crop.height) for x in range(crop.width) if ink.getpixel((x,y))}
    known = {(x,y):crop.getpixel((x,y)) for y in range(crop.height) for x in range(crop.width) if (x,y) not in pending}
    if not known:
        raise ValueError('Lettering mask covers entire rectangle; review its bounds')
    while pending:
        wave = {}
        for x,y in pending:
            neighbors = [known[(x+dx,y+dy)] for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)) if (x+dx,y+dy) in known]
            if neighbors:
                wave[(x,y)] = tuple(round(sum(c[k] for c in neighbors)/len(neighbors)) for k in range(4))
        assert wave, 'No background reaches lettering mask'
        known.update(wave)
        pending.difference_update(wave)
    for xy,color in known.items():
        crop.putpixel(xy,color)
    return crop


def region_mask(source,box,lettering=False,minimum=195,polygon=None):
    import cv2
    import numpy as np
    rgba=np.array(source)
    ink=np.zeros(rgba.shape[:2],dtype=np.uint8)
    x0,y0,x1,y1=box
    if polygon:
        cv2.fillPoly(ink,[np.array(polygon,dtype=np.int32)],255)
        scope=np.zeros_like(ink)
        scope[y0:y1,x0:x1]=255
        ink=cv2.bitwise_and(ink,scope)
    elif lettering:
        local=(rgba[y0:y1,x0:x1,:3].min(axis=2)>=minimum).astype(np.uint8)*255
        local=cv2.dilate(local,np.ones((5,5),np.uint8))
        ink[y0:y1,x0:x1]=local
    else:
        ink[y0:y1,x0:x1]=255
    return ink


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('rules', type=Path)
    p.add_argument('font', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--expected-source-sha256', required=True)
    p.add_argument('--expected-font-sha256', required=True)
    p.add_argument('--fallback-font', action='append', type=Path, default=[])
    p.add_argument('--expected-fallback-font-sha256', action='append', default=[])
    p.add_argument('--light-text', action='store_true')
    a = p.parse_args()
    assert hashlib.sha256(a.source.read_bytes()).hexdigest() == a.expected_source_sha256
    assert hashlib.sha256(a.font.read_bytes()).hexdigest() == a.expected_font_sha256
    assert len(a.fallback_font) == len(a.expected_fallback_font_sha256)
    for path, digest in zip(a.fallback_font, a.expected_fallback_font_sha256):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    if a.output.exists():
        p.error('Use a fresh output filename')
    rules = json.loads(a.rules.read_bytes())
    faces = [Face(str(path)) for path in [a.font, *a.fallback_font]]
    face = faces[0]
    missing = sorted({c for r in rules['labels'] for c in r['text']
                      if c not in '\n\r\t' and not any(f.get_char_index(ord(c)) for f in faces)})
    assert not missing, ('Missing font glyphs', missing)
    original = Image.open(a.source).convert('RGBA')
    assert list(original.size) == rules['dimensions']
    edited = original.copy()
    mask = Image.new('1', original.size)
    md = ImageDraw.Draw(mask)
    placed = []
    cv_mask=None
    for r in rules.get('background_groups',rules['labels']):
        x0,y0,x1,y1 = r['box']
        assert 0 <= x0 < x1 <= original.width and 0 <= y0 < y1 <= original.height
        assert 0 <= r['sample_x'] < original.width
        assert r.get('reviewed_background_sample_inside_box') is True or not x0 <= r['sample_x'] < x1
        mode = r.get('background_mode','row_sample')
        if mode in {'region_inpaint','letter_inpaint'}:
            ink=region_mask(original,r['box'],mode=='letter_inpaint',r.get('ink_minimum',195),r.get('polygon'))
            cv_mask=ink if cv_mask is None else cv_mask|ink
        elif mode == 'inpaint':
            edited.paste(heal_lettering(original,r['box'],r.get('ink_minimum',195)),(x0,y0))
        elif mode == 'vertical_interpolation':
            upper,lower = r['sample_y']
            assert 0 <= upper < y0 < y1 <= lower < original.height
            for x in range(x0,x1):
                c0,c1 = original.getpixel((x,upper)),original.getpixel((x,lower))
                for y in range(y0,y1):
                    t = (y-upper)/(lower-upper)
                    edited.putpixel((x,y),tuple(round(v0*(1-t)+v1*t) for v0,v1 in zip(c0,c1)))
        else:
            for y in range(y0,y1):
                sample_x = r.get('lower_sample_x',r['sample_x']) if y >= r.get('lower_sample_y',y1) else r['sample_x']
                color = original.getpixel((sample_x,y))
                for x in range(x0,x1):
                    edited.putpixel((x,y),color)
        md.rectangle((x0,y0,x1-1,y1-1),fill=1)
    if cv_mask is not None:
        import cv2
        import numpy as np
        rgba=np.array(edited)
        rgb=cv2.inpaint(rgba[:,:,:3],cv_mask,3,cv2.INPAINT_NS)
        rgba[cv_mask!=0,:3]=rgb[cv_mask!=0]
        edited=Image.fromarray(rgba)
    for r in rules['labels']:
        x0,y0,x1,y1=r['box']
        font = ImageFont.truetype(str(a.font),r['size'])
        stroke_width = r.get('stroke_width',1)
        draw=ImageDraw.Draw(edited)
        bbox = draw.multiline_textbbox((0,0),r['text'],font=font,spacing=r.get('line_spacing',1),stroke_width=stroke_width)
        w,h = bbox[2]-bbox[0],bbox[3]-bbox[1]
        fill = tuple(r.get('fill',[15,15,15,255]))
        stroke = tuple(r.get('stroke',[255,255,255,255]))
        if a.light_text and r['id'] not in {'heading','footnote'}:
            fill,stroke = stroke,fill
        uses_fallback = any(not face.get_char_index(ord(c)) for c in r['text']
                            if c not in '\n\r\t')
        if uses_fallback:
            fonts = [font, *[ImageFont.truetype(str(path), r['size']) for path in a.fallback_font]]
            layer = mixed_text_layer(r['text'], fonts, faces, fill, stroke, stroke_width)
            if r.get('angle'):
                layer = layer.rotate(r['angle'], expand=True, resample=Image.Resampling.BICUBIC)
            w, h = layer.size
            assert w <= x1-x0 and h <= y1-y0, (r['id'], (w,h), r['box'])
            alignment = r.get('align', 'center')
            assert alignment in {'left', 'center', 'right'}
            x = x0 if alignment == 'left' else (x1-w if alignment == 'right' else x0+(x1-x0-w)//2)
            edited.alpha_composite(layer, (x, y0+(y1-y0-h)//2))
        elif r.get('angle'):
            layer=Image.new('RGBA',(w,h),(0,0,0,0))
            ImageDraw.Draw(layer).multiline_text((-bbox[0],-bbox[1]),r['text'],font=font,fill=fill,stroke_width=stroke_width,stroke_fill=stroke,spacing=r.get('line_spacing',1),align='center')
            layer=layer.rotate(r['angle'],expand=True,resample=Image.Resampling.BICUBIC)
            w,h=layer.size
            assert w <= x1-x0 and h <= y1-y0, (r['id'],(w,h),r['box'])
            edited.alpha_composite(layer,(x0+(x1-x0-w)//2,y0+(y1-y0-h)//2))
        else:
            assert w <= x1-x0 and h <= y1-y0, (r['id'],(w,h),r['box'])
            alignment = r.get('align', 'center')
            assert alignment in {'left', 'center', 'right'}
            x = x0 if alignment == 'left' else (x1-w if alignment == 'right' else x0+(x1-x0-w)//2)
            xy = (x-bbox[0],y0+(y1-y0-h)//2-bbox[1])
            draw.multiline_text(xy,r['text'],font=font,fill=fill,stroke_width=stroke_width,stroke_fill=stroke,spacing=r.get('line_spacing',1),align='center')
        md.rectangle((x0,y0,x1-1,y1-1),fill=1)
        placed.append({'id':r['id'],'box':r['box'],'text':r['text'],'font_size':r['size'],'ink_size':[w,h],
                       'fallback_font_used':uses_fallback})
    diffs = protected = 0
    for x in range(original.width):
        for y in range(original.height):
            if original.getpixel((x,y)) != edited.getpixel((x,y)):
                diffs += 1
                if not mask.getpixel((x,y)):
                    protected += 1
    assert protected == 0
    a.output.parent.mkdir(parents=True,exist_ok=True)
    edited.save(a.output)
    mask.convert('L').save(a.output.with_suffix('.mask.png'))
    report = {'asset':rules['asset'],'source_sha256':a.expected_source_sha256,'font_sha256':a.expected_font_sha256,
        'fallback_font_sha256':a.expected_fallback_font_sha256,
        'output_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'dimensions':list(edited.size),
        'labels':placed,'changed_pixels':diffs,'changed_pixels_outside_authored_boxes':protected,
        'runtime_verdict':'NOT_TESTED','palette_conversion_required':True}
    a.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'labels':len(placed),'changed_pixels':diffs,'protected_changed_pixels':protected}))


if __name__ == '__main__':
    main()
