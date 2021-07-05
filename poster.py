import os
from io import BytesIO

import qrcode
import requests
import requests_cache
from PIL import Image, ImageDraw, ImageFont

import C

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'
}

requests_cache.install_cache(C.STORE_DB + '/cache')


def fetchImg(url=None):
    """加载图片"""
    # print(f"fetch img: {url}")
    if '/storage/upload/' in url:
        # 先判断是否存在本地文件系统
        # http://127.0.0.1:9001/storage/upload/0186e7249df3f1b7.jpg
        url = '/storage/upload/' + url.split('/storage/upload/')[1]

    if not str(url).startswith("http"):
        filepath = C.get_url_local_path(url)
        if os.path.exists(filepath):
            img = Image.open(filepath)
            img = img.convert('RGBA')
            return img
        else:
            # 返回一个默认的图片
            return fetchImg('/img/no-img.jpg')
    try:
        response = requests.get(url, headers=headers)
        img = Image.open(BytesIO(response.content))  # type: Image.Image
        img = img.convert('RGBA')
        return img
    except:
        return fetchImg('/img/no-img.jpg')


def drawImg(draw, item, bg):
    """绘制图片"""
    url = item['v']
    w = item['w']
    h = item['h']
    x = item['x']
    y = item['y']
    try:
        img = fetchImg(url)
        if img == None:
            return
        # 尺寸更改
        img = img.resize((w, h), Image.ANTIALIAS)
        bg.paste(img, (x, y), img)
    except Exception as e:
        print('绘制图片异常: %s' % e)
        pass


def drawBg(item):
    """绘制背景图"""
    url = str(item['bgUrl'])
    w = item['w']
    h = item['h']
    c = item['bgc']
    if c == '': c = '#fff'
    if not url.strip():
        img = Image.new('RGB', (w, h), c)
    else:
        img = fetchImg(url)
    img = img.resize((w, h), Image.ANTIALIAS)
    draw = ImageDraw.Draw(img)  # 绘制对象
    return img, draw


def getFont(item):
    """获取字体"""
    fn = item['fn']
    size = item['s']
    if fn == "":
        # fn = 'Alibaba-Emoji.ttf'
        fn = 'Alibaba-PuHuiTi-Regular.otf'
    font = 'fonts/' + fn
    return ImageFont.truetype(font, size)


def wrap_text(text, font, width):
    """包裹文字"""
    sb = []
    temp = ''
    for s in text:
        t = temp + s
        if font.getsize(t)[0] > width:
            sb.append(temp)
            temp = s
        else:
            temp += s
    if temp != '':
        sb.append(temp)
    return sb


def drawText(draw, item, bg):
    """绘制文本"""
    font = getFont(item)
    v = item['v']
    w = item['w']
    h = item['h']
    x = item['x']
    y = item['y']
    c = item.get('c', '#010203')
    img = Image.new("RGBA", (w, h), '#fff0')
    draw = ImageDraw.Draw(img)  # type:ImageDraw.ImageDraw
    t = wrap_text(v, font, w)
    draw.text((0, 0), '\n'.join(t), fill=c, font=font)
    # 如果是图片绘制，则要添加一下图片
    # img.show()
    if img is not None:
        bg.paste(img, (x, y), img)


def drawQrCode(draw, item, bg):
    """绘制二维码"""
    url = item['v']
    w = item['w']
    h = item['h']
    x = item['x']
    y = item['y']
    c = item.get('c', '#010203').strip()
    c = '#010203' if len(c) == 0 else c
    p = item.get('p', 0)
    # 生成二维码
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=p,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=c, back_color="#ffffff")

    # 尺寸更改
    img = img.resize((w, h), Image.ANTIALIAS)
    bg.paste(img, (x, y), None)


def drawAvatar(draw, item, bg):
    """绘制头像"""
    url = item['v']
    w = item['w']
    h = item['h']
    x = item['x']
    y = item['y']
    c = item.get('c', '#ffffff').strip()
    c = '#ffffff' if len(c) == 0 else c
    im = fetchImg(url)
    if im == None:
        return
    bigsize = (im.size[0] * 3, im.size[1] * 3)  # 放大一些，用来消除锯齿
    mask = Image.new('L', bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(im.size, Image.ANTIALIAS)
    im.putalpha(mask)  # 核心代码
    # 尺寸更改
    im = im.resize((w, h), Image.ANTIALIAS)

    # 在头像上再画一个圆圈
    mask = Image.new('RGBA', bigsize)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, outline=c, width=4 * 3)
    mask = mask.resize(im.size, Image.ANTIALIAS)
    im.paste(mask, (0, 0), mask)

    bg.paste(im, (x, y), im)
    pass


def draw(data):
    """根据json绘制海报"""
    # 绘制底图
    img, draw = drawBg(data)

    # 遍历绘制子元素
    for item in data['items']:
        type = item['t']
        if 'text' == type:
            drawText(draw, item, bg=img)
        if 'image' == type:
            drawImg(draw, item, bg=img)
        if 'avatar' == type:
            drawAvatar(draw, item, bg=img)
        if 'qrcode' == type:
            # 特殊处理(判断是否是小程序码)，兼容之前的程序(一套模板兼容二维码和小程序码)
            url = item.get('v', '')
            if url.startswith('wxacode:'):
                url = url[8:]
                item['v'] = url
                # print("小程序码特殊处理: url=" + url)
                drawImg(draw, item, bg=img)
            else:
                drawQrCode(draw, item, bg=img)

    if data['type'] == "jpeg":
        img = img.convert("RGB")
    return img


def drawio(data):
    # 获取格式
    type = data['type']
    if type == "jpg":
        type = "jpeg"
        data['type'] = type
    mimetype = "image/" + data['type']

    # 绘制海报
    img = draw(data)

    # 设置图片清晰度
    quality = data['quality']
    buf = BytesIO()
    img.save(buf, type, quality=quality, progressive=True)
    # img.save(buf, type, progressive=True)
    # img.save(buf, type)
    buf.seek(0)
    return buf, mimetype


def drawmini(data, scale=0.5):
    """
    生成缩略图
    :param data:
    :param scale:
    :return:
    """
    im = draw(data)
    w = im.size[0]
    h = im.size[1]
    img = im.resize((int(w * scale), int(h * scale)), Image.ANTIALIAS)
    return img
