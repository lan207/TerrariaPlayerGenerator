from PIL import Image
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
import os
width=40
height=56
def slice4BodyAndArms(path,color=(0,0,0),count=2,isBody=False,isFemale=False):
    img= Image.open(path)

    img_list=[]
    if isBody:
        for i in range(2):
            j=i%(count)
            img_crop=img.crop((j*width,0,(j+1)*width,height))
            img_crop=recolor_image(img_crop,color)
            if isFemale:
                chest= img.crop((j*width,2*height,(j+1)*width,height))
                chest=recolor_image(chest,color)
                img_crop=Image.alpha_composite(img_crop,chest)
            img_list.append(img_crop)
    else:
        for i in range(2):
            x=i%(count)+2
            y=i//(count)*2
            y1=y+1
    return img_list
def recolor_image(image:Image, target_color):
        """
        将图像重新着色为指定颜色（保持原有明暗）
        
        参数:
        image: 原始图像
        target_color: 目标颜色 (R, G, B)
        """
        # 转换为RGBA模式
        img = image.convert('RGBA')
        data = img.getdata()
        
        new_data = []
        for item in data:
            # 保持透明度，但改变颜色
            if item[3] != 0:  # 非透明像素
                # 使用原始像素的亮度信息
                brightness = (item[0] + item[1] + item[2]) // 3
                # 应用目标颜色但保持亮度
                r = int(target_color[0] * brightness / 255)
                g = int(target_color[1] * brightness / 255)
                b = int(target_color[2] * brightness / 255)
                new_data.append((r, g, b, item[3]))
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        return img
img=slice4BodyAndArms(str(ROOT / "Assets/Player/Player_0_3.png"),color=(255,0,0),count=2,isBody=True)
final_image = Image.new('RGBA', (width, height*2), (0, 0, 0, 0))
image=Image.new('RGBA', (width, height), (0, 0, 0, 0))
for i in range(len(img)):
    image=img[i]
    final_image.paste(image, (0, i*height))
output = ROOT / 'test-artifacts/legacy/output2.png'
output.parent.mkdir(parents=True, exist_ok=True)
final_image.save(output)
