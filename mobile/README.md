# 安卓离线版

安装包：项目根目录 `dist/PlayerStudio-android.apk`，应用名称为「泰拉人物工坊」。

将 APK 发到安卓手机，打开文件并按系统提示允许该文件管理器安装应用。支持 Android 8.0 及以上；需要较新的 Android System WebView（Chromium 98+）。安装后可完全断网使用，不需要电脑、Python、账户或后台服务。

人物素材、编辑界面、配色与动画生成逻辑都包含在安装包中。支持 165 种发型及 Alt 发型、独立服装配色、站立/跑动/跳跃/使用物品、1/2/4/8 倍 PNG 与 GIF 导出。外观配置自动保存在本机。点击导出后，在系统文件窗口选择保存位置；可以保存到「下载」等本地文件夹。应用不申请网络权限或整个存储空间的访问权限。

## 重新构建

Windows 上需要 Python 3.10+、Pillow、JDK 17+ 和 Android SDK platform 35 / build-tools 35。手机无需安装这些工具。

```powershell
python -m pip install -r requirements.txt
python mobile/setup_android.py
python mobile/build_apk.py --java-home C:/Program Files/Java/jdk-21
```

也可以双击根目录的 `BuildAndroid.bat`。构建脚本检查 Python、JDK 版本和 Android SDK 组件；缺少 SDK 时会下载校验后的官方工具。构建时优先使用 `JAVA_HOME`，未设置时从 `PATH` 中查找 JDK 17+。已有 SDK 可通过 `--sdk 路径` 指定。

`setup_android.py` 从 Google 官方站点下载工具到项目 `.test-tools/android-sdk`，校验官方目录中的 SHA-1 后解压；不修改系统配置。构建使用 aapt2、javac、D8、zipalign 和 apksigner，不依赖 Gradle。工具下载完成后可离线重建。

本地自用签名保存在 `mobile/.signing/local-test.p12`，为本地测试密钥（密码 `android`），不用于商店发布。保留该文件可继续覆盖安装；丢失后生成的新签名无法覆盖旧安装。

## 源码与验证

- `mobile/prepare.py`?提取目录、默认配色和动作数据，并打包共享界面与素材。
- `mobile/offline.js`、`mobile/equipment.js` 和 `mobile/render.js`：本地资源渲染、时间轴合成和 PNG/GIF 导出。
- `src/com/playerstudio/offline/MainActivity.java`：安卓 WebView 容器、本地资源访问和系统文件保存。
- `tests/mobile/verify_offline.py`：独立渲染对比、680 帧旧版回归、设备宽度界面、新装备与变换像素对比、八倍导出。

运行验证需要 Playwright Python 包和 Chrome：

```powershell
python -m pip install playwright
python tests/mobile/verify_offline.py
python tests/mobile/verify_integration.py
```

验证结果与截图保存在 `test-artifacts/mobile/`。680 帧对比已通过，其中 4 帧的半透明像素存在不超过 1/255 的通道舍入差异。PNG 单帧、帧图与 13 帧透明 GIF 的尺寸和内容通过检查；APK 签名已验证。当前未进行安卓真机测试，系统保存窗口和设备 WebView 兼容性需要实机确认。

集成检查另行验证外观持久化、传给安卓保存接口的文件内容、单帧 GIF、移动版没有后端 API 请求，以及原网页版的生成与下载。安卓接口在此项测试中使用模拟实现，不能替代系统文件窗口的真机测试。

网页版继续使用 `StartWeb.bat`，不会加载移动版的本地渲染脚本。


## 当前版本与完整功能

APK 版本为 1.1.0。离线版包含装备、饰品、染色、时间轴和头部/身体/腿部/全身变换编辑。变换会保存在自定义帧中，并用于预览、帧图和 GIF 导出。

每次提交都会在 GitHub Actions 中构建并保存 30 天的 APK artifact；推送 `v*` 标签会额外将安装包加到 GitHub Release。APK 使用本地测试密钥签名，适用于直接安装和内部分发，不用于商店发布。
