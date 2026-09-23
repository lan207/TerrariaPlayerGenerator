<<<<<<< HEAD
# Player Studio / 泰拉人物工坊

安卓离线版已提供：将 `dist/PlayerStudio-android.apk` 传到手机安装，即可在本地编辑、预览与导出，无需电脑服务或网络。支持 Android 8.0+ 和较新的 Android System WebView。安装、重新构建与验证说明见 [mobile/README.md](mobile/README.md)。

双击 `StartWeb.bat` 自动启动并打开网页；或运行 `python web_server.py` 后，浏览器打开 **http://127.0.0.1:8765**。
依赖 Python 3.10+ 和 Pillow；缺少依赖时运行 `python -m pip install -r requirements.txt`。
更换端口：`python web_server.py --port 8766`。终端 Ctrl+C 停止服务。

1. 默认展示站立第一帧。左右箭头或在部位选择行左右滑动切换发型、身体/上衣、裤装和鞋子。
2. 左侧在「基础外观 / 装备时装 / 饰品」之间切换。装备分头部、上身、腿部；饰品支持背部、前饰、项链、腰饰、鞋饰、盾牌、前后手、面饰、胡须与气球，共 194 张素材，可按名称或编号搜索。配套披风可自动显示或关闭。右侧色块调整人物基础配色。
3. 点击“确认人物 · 生成动画”，主动作栏提供站立、跑动、跳跃、挥动、展示/举起、射击/瞄准六类常用动作。食用、弹奏等是特定物品的使用姿势，之前生成的旧时间轴仍可读取，但不再把这些采样列为通用动作。
   射击始终只有一帧：在预览框中移动鼠标或触摸拖动，人物面朝目标；也可直接输入任意瞄准角度。移出预览框后保持当前角度，导出单帧 PNG/帧图/GIF。瞄准辅助线不会导出；将射击加入时间轴时会保存该帧自己的瞄准角度。
4. 动画工作台下方的「自定义时间轴」可以加入当前固定帧、整个动作或自定义姿势帧。选择帧后可独立设置身体、头部、腿部状态，前后手是否自定义、四档伸展长度、−180°～180° 角度，以及朝向和饰品动画帧。支持复制、删除、拖动或箭头排序、每帧时长；最多 120 帧。外观与时间轴自动保存在当前浏览器。
5. 选择「自定义」动作，再点击底部导出此帧 PNG、整条时间轴的 PNG 帧图或循环 GIF；GIF 使用每帧独立时长。普通无装备固定帧为 40×56；装备/饰品/复合双臂为 64×80；神灵诅咒为 64×96，以透明留边容纳尾部。自定义时间轴统一对齐人物，不缩放原始像素；2/4/8× 导出使用最近邻缩放。

装备和饰品也支持独立染色：在装备各部位下方，或饰品页当前选择的部位下方，点击色块或输入 `#RRGGBB`。颜色以正片叠底方式叠加于原贴图，保留原有明暗和透明度，白色保留原色。长袍衣摆、外套衣摆和自动配套披风默认随上身颜色；饰品染色可单独覆盖配套披风。点击「重置」恢复原色或自动配套色。颜色按部位保存在浏览器中，切换装备后继续使用，并同步应用到所有动作、自定义时间轴与 PNG/GIF 导出。

选择冬季披风等带前后部件的披风时，会自动补齐同款另一侧；前部按源码拆成两半，分别绘制在前手之前和之后，避免前襟被身体挡住。自动补齐的部件跟随所选披风染色，也可单独指定另一侧的款式或颜色；选择器会标注「自动配套」。

修改外观、装备或饰品会使旧动画失效，需重新确认人物；时间轴编排会保留并重新渲染。修改时间轴后会自动更新预览，更新完成前禁止导出旧的自定义动画。PNG 帧图每格宽度为 `当前画布宽度 × 导出倍率`。相邻完全相同的 GIF 图像可能合并，但总时长保持一致。

素材从 `Assets/Player`、`Assets/Hair`、`Assets/Armor/{Head,Body,Legs}` 与 `Assets/Accessories` 读取。`Assets/Armor/Legs/Extra_73.png` 用于腿部 #140「神灵诅咒」；自定义姿势中可设置 0–7 特效帧，腿部帧 1 使用完整漂浮尾部，其余腿帧使用站立形态。气球使用同一特效帧设置，按 4 帧循环。更换素材后重启服务并刷新网页。

源码依据、支持范围和验证方式见 [docs/equipment.md](docs/equipment.md)。目前不包含手持物品、染料着色器、独立发光层和随机粒子；只提供现有素材对应的饰品，不包含尚未提供的翅膀。此次高级编辑功能用于网页版；已有安卓 APK 的离线引擎仍为基础人物版本。

动作依据 Terraria 1.4.4 的 `Player.PlayerFrame`、`ItemCheck_UseStyle`、`PlayerDrawSet.CreateCompositeData/UpdateCompositeArm` 和 `PlayerDrawLayers`。普通射击的目标角度连续变化，而身体贴图按 `itemRotation × direction` 选择当前姿势（上举/平举/下举），这些是互斥贴图，不是三帧动画。自定义手臂可连续旋转，角度以朝右时为基准、朝左时镜像：0° 向下、−90° 向前、±180° 向上。射击瞄准角采用屏幕坐标：0° 向右、−90° 向上、90° 向下、±180° 向左。

命令行入口仍可使用：

=======
# Player Studio / 泰拉人物工坊

安卓离线版已提供：将 `dist/PlayerStudio-android.apk` 传到手机安装，即可在本地编辑、预览与导出，无需电脑服务或网络。支持 Android 8.0+ 和较新的 Android System WebView。安装、重新构建与验证说明见 [mobile/README.md](mobile/README.md)。

双击 `StartWeb.bat` 自动启动并打开网页；或运行 `python web_server.py` 后，浏览器打开 **http://127.0.0.1:8765**。
依赖 Python 3.10+ 和 Pillow；缺少依赖时运行 `python -m pip install -r requirements.txt`。
更换端口：`python web_server.py --port 8766`。终端 Ctrl+C 停止服务。

1. 默认展示站立第一帧。左右箭头或在部位选择行左右滑动切换发型、身体/上衣、裤装和鞋子。
2. 左侧在「基础外观 / 装备时装 / 饰品」之间切换。装备分头部、上身、腿部；饰品支持背部、前饰、项链、腰饰、鞋饰、盾牌、前后手、面饰、胡须与气球，共 194 张素材，可按名称或编号搜索。配套披风可自动显示或关闭。右侧色块调整人物基础配色。
3. 点击“确认人物 · 生成动画”，主动作栏提供站立、跑动、跳跃、挥动、展示/举起、射击/瞄准六类常用动作。食用、弹奏等是特定物品的使用姿势，之前生成的旧时间轴仍可读取，但不再把这些采样列为通用动作。
   射击始终只有一帧：在预览框中移动鼠标或触摸拖动，人物面朝目标；也可直接输入任意瞄准角度。移出预览框后保持当前角度，导出单帧 PNG/帧图/GIF。瞄准辅助线不会导出；将射击加入时间轴时会保存该帧自己的瞄准角度。
4. 动画工作台下方的「自定义时间轴」可以加入当前固定帧、整个动作或自定义姿势帧。选择帧后可独立设置身体、头部、腿部状态，前后手是否自定义、四档伸展长度、−180°～180° 角度，以及朝向和饰品动画帧。支持复制、删除、拖动或箭头排序、每帧时长；最多 120 帧。外观与时间轴自动保存在当前浏览器。
5. 选择「自定义」动作，再点击底部导出此帧 PNG、整条时间轴的 PNG 帧图或循环 GIF；GIF 使用每帧独立时长。普通无装备固定帧为 40×56；装备/饰品/复合双臂为 64×80；神灵诅咒为 64×96，以透明留边容纳尾部。自定义时间轴统一对齐人物，不缩放原始像素；2/4/8× 导出使用最近邻缩放。

装备和饰品也支持独立染色：在装备各部位下方，或饰品页当前选择的部位下方，点击色块或输入 `#RRGGBB`。颜色以正片叠底方式叠加于原贴图，保留原有明暗和透明度，白色保留原色。长袍衣摆、外套衣摆和自动配套披风默认随上身颜色；饰品染色可单独覆盖配套披风。点击「重置」恢复原色或自动配套色。颜色按部位保存在浏览器中，切换装备后继续使用，并同步应用到所有动作、自定义时间轴与 PNG/GIF 导出。

选择冬季披风等带前后部件的披风时，会自动补齐同款另一侧；前部按源码拆成两半，分别绘制在前手之前和之后，避免前襟被身体挡住。自动补齐的部件跟随所选披风染色，也可单独指定另一侧的款式或颜色；选择器会标注「自动配套」。

修改外观、装备或饰品会使旧动画失效，需重新确认人物；时间轴编排会保留并重新渲染。修改时间轴后会自动更新预览，更新完成前禁止导出旧的自定义动画。PNG 帧图每格宽度为 `当前画布宽度 × 导出倍率`。相邻完全相同的 GIF 图像可能合并，但总时长保持一致。

素材从 `Assets/Player`、`Assets/Hair`、`Assets/Armor/{Head,Body,Legs}` 与 `Assets/Accessories` 读取。`Assets/Armor/Legs/Extra_73.png` 用于腿部 #140「神灵诅咒」；自定义姿势中可设置 0–7 特效帧，腿部帧 1 使用完整漂浮尾部，其余腿帧使用站立形态。气球使用同一特效帧设置，按 4 帧循环。更换素材后重启服务并刷新网页。

源码依据、支持范围和验证方式见 [docs/equipment.md](docs/equipment.md)。目前不包含手持物品、染料着色器、独立发光层和随机粒子；只提供现有素材对应的饰品，不包含尚未提供的翅膀。此次高级编辑功能用于网页版；已有安卓 APK 的离线引擎仍为基础人物版本。

动作依据 Terraria 1.4.4 的 `Player.PlayerFrame`、`ItemCheck_UseStyle`、`PlayerDrawSet.CreateCompositeData/UpdateCompositeArm` 和 `PlayerDrawLayers`。普通射击的目标角度连续变化，而身体贴图按 `itemRotation × direction` 选择当前姿势（上举/平举/下举），这些是互斥贴图，不是三帧动画。自定义手臂可连续旋转，角度以朝右时为基准、朝左时镜像：0° 向下、−90° 向前、±180° 向上。射击瞄准角采用屏幕坐标：0° 向右、−90° 向上、90° 向下、±180° 向左。

命令行入口仍可使用：

>>>>>>> 2eeed83e21770a7bf58dc5020ab92c4d3726ff1e
```powershell
New-Item -ItemType Directory -Force test-artifacts | Out-Null
python Generator.py
python TrueTerrariaGenerator.py --action walk --action-sheet --output test-artifacts/walk.png
python TrueTerrariaGenerator.py --action use --use-style 1 --action-sheet --output test-artifacts/use.png
python TrueTerrariaGenerator.py --armor-head 1 --armor-body 1 --armor-legs 1 --action walk --action-sheet --output test-artifacts/copper_walk.png
python TrueTerrariaGenerator.py --action raise_lamp --output test-artifacts/lamp_pose.png
python TrueTerrariaGenerator.py --action shoot --aim-angle -120 --output test-artifacts/aim.png
<<<<<<< HEAD
```

验证脚本位于 `tests/ui/` 与 `tests/mobile/`，截图和验证产物统一保存到 `test-artifacts/`。运行 `python -m unittest discover -s tests -v`、`python tests/ui/verify_studio_ui.py`、`python tests/ui/verify_dyes_ui.py`、`python tests/ui/verify_aim_ui.py`。

自定义姿势支持头部、身体、腿部和全身分别旋转、X/Y 偏移，并保留双臂设置。装备与饰品随所属部位变换；每个变换提供重置按钮。时间轴帧保存这些参数，预览和导出会按变换后的范围扩展画布。

Windows 双击 `BuildAndroid.bat` 构建安卓安装包，输出为 `dist/PlayerStudio-android.apk`。GitHub Actions 会构建 APK 并提供下载 artifact；推送 `v*` 标签时也会附加到 GitHub Release。详见 [mobile/README.md](mobile/README.md)。
=======
```

验证脚本位于 `tests/ui/` 与 `tests/mobile/`，截图和验证产物统一保存到 `test-artifacts/`。运行 `python -m unittest discover -s tests -v`、`python tests/ui/verify_studio_ui.py`、`python tests/ui/verify_dyes_ui.py`、`python tests/ui/verify_aim_ui.py`。

自定义姿势支持头部、身体、腿部和全身分别旋转、X/Y 偏移，并保留双臂设置。装备与饰品随所属部位变换；每个变换提供重置按钮。时间轴帧保存这些参数，预览和导出会按变换后的范围扩展画布。

Windows 双击 `BuildAndroid.bat` 构建安卓安装包，输出为 `dist/PlayerStudio-android.apk`。GitHub Actions 会构建 APK 并提供下载 artifact；推送 `v*` 标签时也会附加到 GitHub Release。详见 [mobile/README.md](mobile/README.md)。
>>>>>>> 2eeed83e21770a7bf58dc5020ab92c4d3726ff1e
