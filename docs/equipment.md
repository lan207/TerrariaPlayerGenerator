# 换装实现与源码依据

源码来自用户提供的 `PATH_TO_TERRARIA_SOURCE`（1.4.4，包含 tModLoader 的拆分定义）。运行编辑器只依赖项目内的 `equipment_rules.json` 和素材，不需要这个外部目录。

## 绘制规则

| 源码 | 对应实现 |
| --- | --- |
| `ID/ArmorIDs.cs`、`ID/ArmorIDs.TML.cs` | 装备编号、完整/帽下发型、隐藏头部/皮肤/手部、跳跃肩甲、前后头饰映射 |
| `Player.cs: GetHairSettings / GetHelmetDrawOffset` | 自动选择头发类型及特殊头盔位置 |
| `Player.cs: SetMatch` | 男女贴图切换、长袍和裙装自动替换腿部；卸装后恢复用户选择 |
| `DataStructures/PlayerDrawSet.cs: CreateCompositeData` | 胸甲 9 列 × 4 行图集；男女躯干、前后手臂、跳跃隐藏肩甲、肩甲偏移 |
| `DataStructures/PlayerDrawLayers.cs: DrawPlayer_01_3_BackHead` | 狗耳等头饰的后方部件 |
| `DrawPlayer_12_SkinComposite_BackArmShirt / DrawPlayer_17_TorsoComposite / DrawPlayer_28_ArmOverItemComposite` | 胸甲取代基础衣服，按顺序绘制后臂、躯干、前臂、肩甲；露出的手部保留肤色 |
| `DrawPlayer_13_Leggings / DrawPlayer_16_ArmorLongCoat` | 护腿替换裤子与鞋子，外套衣摆单独叠加 |
| `DrawPlayer_21_Head` | 高帽裁切、正常/帽下发型遮挡、兔帽与獾帽的特殊拼接 |
| `Player.ItemCheck_UseStyle` | 食用、饮用、割草、弹奏、后手举灯的双臂伸展与角度采样 |
| `PlayerDrawSet.UpdateCompositeArm` | 自定义前臂使用图集第 7 列、后臂第 8 列；Full/ThreeQuarters/Quarter/None 对应第 0/1/2/3 行 |
| `GetCompositeOffset_FrontArm / GetCompositeOffset_BackArm` | 前臂支点 `(15,28)`、后臂支点 `(26,30)`，均相对于 40×56 帧左上角；复合前臂另加 `(1,1)` 平移 |
| `DrawPlayer_08_Backpacks / 08_1_Tails / 10_BackAcc / 11_Balloons / 12_1_BalloonFronts` | 背饰、披风、尾部及气球的分层与离散动画帧 |
| `DrawPlayer_14_Shoes / 19_WaistAcc / 20_NeckAcc / 22_FaceAcc / 25_Shield / 32_FrontAcc` | 鞋饰遮挡、腰部取帧、面饰遮发与头盔替换、盾牌宽度、前部饰品 |
| `ArmorIDs.Body.Sets.IncludedCape* / IncludeCapeFrontAndBack` | 装备自动配套披风；手动选择优先，可关闭自动配套 |

705 张盔甲素材中，6 张后方头饰由前方头饰自动引用，1 张头部 #23 为未使用条目，目录显示 698 个可选部件。新增 `Extra_73.png` 后，腿部 #140「神灵诅咒」已启用：16×24 源矩形、26 像素行步长、8 个动画帧；腿部状态 1 取 x=0 列，其余取 x=18 列。按源码隐藏普通腿部和鞋饰，防止下方露出脚。

`Assets/Accessories` 的 194 张素材覆盖 11 类饰品。每个部位独立选择一个，手饰随复合手臂旋转与伸展，气球按 `Main.OffsetsPlayerOffhand` 定位；面饰、胡须和鞋饰使用原版可见性规则。自动配套披风采用已有贴图，显式选择的饰品优先。没有匹配中文名称的条目仍可用英文名或贴图编号搜索。

## 披风部件与图层

`Item.cs:26132` 对 2284–2287 号披风同时设置 `backSlot = 3 + type - 2284` 和 `frontSlot = 1 + type - 2284`。因此冬季披风（2287）需要 `Acc_Back_6.png` 与 `Acc_Front_4.png` 两张贴图，单独把背部图层提前不能补齐前襟。`accessories.py` 根据 `ArmorIDs.Back/Front` 的同名条目配对；手动指定的另一侧优先，装备自动配套披风随后补充空位。

绘制顺序来自 `Graphics/Renderers/LegacyPlayerRenderer.cs:229` 之后的调用序列、`DataStructures/PlayerDrawLayers.cs:2847` 的 `DrawPlayer_32_FrontAcc_FrontPart/BackPart`，以及 `PlayerDrawSet.cs:1431`：

- 背部披风绘制在身体之前。
- 朝右源矩形 x=20…39 的前部半片，在身体/面饰之后、盾牌与前手之前绘制。
- 朝右源矩形 x=0…19 的前部半片，在前手及手饰之后绘制；最后统一镜像到朝左。
- 跳跃身体帧 5 且 `ArmorIDs.Front.Sets.DrawsInNeckLayer` 为真（前饰 #6）时，前部半片提前到面饰之后、前手之前。

自动补齐的披风部件默认继承手动所选部件的染色；装备自带部件继承上身染色。任一部件的显式染色设置优先。前后部分分别裁切后只合成一次，保留原 alpha，不会通过重复叠加改变半透明像素。

装备名称从 `ArmorIDs` 提取，中文显示名来自本机的 Terraria `Localization/Items.json`。没有中文映射的条目显示源码英文名或对应衣摆名，均可按名称、英文名、贴图编号搜索。需要刷新规则时运行：

```powershell
python tests/extract_equipment_rules.py --source "PATH_TO_TERRARIA_SOURCE" --names "PATH_TO_ITEMS_JSON"
```

## 画布与范围

普通无装备固定姿势为 40×56。穿戴装备、饰品或使用自定义/复合双臂时为 64×80，神灵诅咒为 64×96。原人物画布向右移 12 像素、向下移 24 像素，仅增加透明留边，不缩放人物。自定义序列把普通固定帧补齐到相同坐标和尺寸，避免不同类型的帧在播放时跳位。导出 2/4/8 倍仍使用最近邻缩放；任意角度旋转也使用最近邻采样。

支持现有头部、胸甲、腿部与饰品贴图的外观，不包含染料着色器、发光叠加、随机粒子、未提供素材的翅膀或手持物品。兔帽与獾帽显示单顶、静止的独立帽子动画状态，不模拟堆叠或随机晃动。主动作栏保留六类常用动作；过去额外添加的食用、弹奏等是物品专用姿势的离散采样，并非通用人物动画，现仅保留旧时间轴与接口兼容。

## 射击单帧与鼠标瞄准

本地源码 `Player.cs:39189` 的普通射击分支使用 `atan2(dy × direction, dx × direction)` 求 `itemRotation`，目标可以位于任意角度。`Player.cs:29802–29820` 则用 `itemRotation × direction` 选择当前 `bodyFrame`：小于 −0.75 弧度取 2，大于 0.6 弧度取 4，其余取 3。三个身体贴图是随角度切换的备选状态，不能串成三帧射击动画。

`poses.shooting_pose` 实现普通 `useStyle=5`、正常重力、不带特殊物品覆盖的这个分支。`aim_angle` 为屏幕方向的角度，范围 −180～180，0 向右、90 向下；左右朝向由目标水平分量决定。普通射击的该分支并未启用连续旋转复合双臂，故身体图像仍按上述阈值选择；需要连续手臂旋转时使用显式自定义双臂功能。

网页只更新当前射击的一帧，单帧状态禁用播放与逐帧操作。鼠标移出预览框后冻结瞄准；数值输入可精确指定角度，瞄准辅助线只显示在界面。导出等待当前瞄准请求完成，并使用已确认的角度，防止旧响应和新目标混用。

## 自定义时间轴

`poses.py` 定义固定动作、姿势校验和序列渲染；`web/sequence.js` 实现编辑器。序列帧为 `fixed`（动作名、动作帧、时长，射击另存 `aim_angle`）或 `custom`（身体/头部/腿部帧、朝向、双臂长度和角度、饰品动画帧、时长）。射击帧索引固定为 0，每个射击帧独立保存角度；改变实时瞄准不改变已加入时间轴的帧。网页读取旧的三帧射击条目时，将旧帧号 0/1/2 转换为 −60°/0°/60° 的独立单帧，并保留旧物品采样条目及其时长。

`POST /api/sequence` 接收 `{config, sequence}`，返回有序 PNG 预览。`POST /api/export` 使用 `action: "custom"` 与相同 `sequence` 导出。后端校验最大 120 帧、帧索引、四档伸展、有限角度值、每帧 20–2000 ms（10ms 倍数）；过大导出要求降低倍率或减少帧数。PNG 帧图严格保留全部帧；GIF 可能合并相邻相同图像，但保持总时长。

浏览器自动保存外观和序列描述；不持久化生成的图片。编辑过程中取消旧预览请求，并用外观版本与序列版本阻止旧响应覆盖新结果。自定义序列未生成成功前禁止导出旧帧。

## 装备与饰品染色

配置新增 `armor_dyes`（head/body/legs）与 `accessory_dyes`（11 个饰品槽位）两个字典，值为 `#RRGGBB`。字段缺省时为空字典，可直接读取旧配置；后端拒绝未知槽位和非法颜色。颜色采用 RGB 逐通道乘法，保留原 alpha；`#ffffff` 完全保持原图。此功能是自定义颜色叠加，不是游戏内复杂染料着色器的复刻。

染色在分层裁切后、旋转与最终合成前应用，覆盖头饰前后部件、胸甲肩部和双臂、腿装、气球及 Extra_73。基础肤色与发色仍由原有配色控制；需要肤色或发色的特殊装备/胡须先完成原有着色，再叠加对应染色。

长袍配套腿部和外套衣摆取上身染色，装备自带披风默认取上身染色；手动所选披风自动补齐的另一侧继承所选部位染色。显式饰品染色优先，可用白色覆盖为原色，删除该槽位染色设置则恢复自动继承。所有预览、固定动作、自定义序列和导出共用同一绘制路径，颜色修改会使旧动画失效。

本次功能接入网页版与 Python 命令行。安卓离线版的渲染器独立，本次没有更新 APK；共享界面在没有装备目录的旧移动端会保留基础外观编辑模式。

## 验证

```powershell
python -m unittest discover -s tests -v
python tests/ui/verify_equipment_ui.py
python tests/ui/verify_studio_ui.py
python tests/ui/verify_dyes_ui.py
python tests/ui/verify_aim_ui.py
python tests/ui/verify_capes_ui.py
python tests/mobile/verify_integration.py
```

测试覆盖全部 698 个装备部件、男女体型、四种动作状态，共 5584 个绘制组合；全部 194 张饰品以及手饰伸展共 1476 个绘制组合。另检查多种角度/四档伸展/左右镜像、Extra_73 八帧、配套披风、无效输入、混合时间轴尺寸、顺序和 GIF 时长。浏览器测试覆盖搜索、增删/复制、按钮/拖动排序、编辑双臂、三个导出格式、外观修改失效、刷新恢复和手机宽度布局。

染色测试检查白色与缺省设置的逐像素一致性、各槽位着色和 alpha 保留、衣摆/披风继承及独立覆盖、Extra_73/气球/旋转手饰、无效输入，以及浏览器取色、HEX 校验、重置、刷新恢复和染色后实际导出。

瞄准测试检查源码角度阈值、左右朝向、任意角度始终单帧、时间轴角度独立保存、单帧 GIF 和 PNG 帧图、鼠标瞄准、旧时间轴迁移及手机布局。

披风测试用独立颜色标记验证身体、披风两半与前手的遮挡次序，并逐像素验证冬季披风前襟在男女体型、左右朝向和自定义双臂下的可见性；浏览器验证自动配套、染色继承/覆盖/重置、卸下、手机布局及预览与 PNG 导出一致性。
