# 许可与公开范围 / Publication policy

## 许可适用对象

[MIT](LICENSE) 适用于本仓库实际发布的原创项目代码和文档；第三方补丁中的上游部分保留原许可，见 [THIRD_PARTY.md](THIRD_PARTY.md)。许可证文本采用 [OSI 公布的 MIT 文本](https://opensource.org/license/mit)。它不是游戏许可，也不授予游戏程序、商标、美术、音乐、视频、地图、字体或其他第三方内容的权利。

`docs/images/` 中少量演示截图是文档引用材料，**其中的游戏画面及第三方内容不纳入 MIT 授权**，权利仍归原权利人所有。截图来源、时间点与用途见 [截图说明](docs/SCREENSHOTS.md)。

本文件规定维护者接受哪些内容进入仓库，不改变 MIT 的使用、修改、商业使用或再分发授权。使用者研究第三方软件时，仍需自行确认适用的授权、合同和当地法律；持有正版副本本身不等于获得再分发权。这里不对逆向、互操作或衍生作品作跨司法辖区的合法性保证。

## 本版本接受的内容

- 重新撰写、经过脱敏的工程方法和经验。
- 经逐文件审查的原创工具、资源处理逻辑、lifter 扩展、运行时与平台适配；工具可读取使用者有权使用的本地游戏输入，但不附带输入或生成结果。
- 保留原许可、版权与修改声明的第三方项目补丁。
- 完全合成的测试输入、公开清单和发布检查配置。
- 维护者明确要求引用的少量公开视频静帧，仅用于说明项目运行状态；逐图登记、审查，最多六张。

## 不进入本仓库的内容

- 原游戏及配套专有 DLL、安装包、补丁和压缩档案。
- 反编译或 lift 生成的游戏/DLL 源码、内存镜像、函数表和其他游戏派生表示。
- 提取的资源、界面文案、美术、图标、字体、字幕、光标、地图、音视频和存档。
- 游戏 shader 字节码、转换后的 shader、缓存和包含它们的源码数组。
- 含游戏派生内容的 EXE、APK、IPA、APP、库、符号包和发行制品。
- 序列号、预设授权码、密钥生成实现、凭据、证书、签名材料及设备/账号标识。
- 保护机制的绕过实现或操作说明、在线服务认证或匹配机制替代方案。
- 私有开发历史、LFS 指针、未经审查的第三方代码/补丁和原始诊断记录。

初版未收录截图。2026-11-15 按维护者要求增加四张其 Bilibili 公开进度视频的静帧；这项文档例外不包含视频文件、提取素材、示范存档或真实游戏测试向量。截图仅裁切展示区域，不重绘或合成游戏内容；通用图像工具仍只用合成输入测试。

## 来源与检查

每个公开文件列在 [PUBLICATION.json](PUBLICATION.json)，并记录来源类别。修改清单不等于完成权利审查。第三方来源不清楚、与游戏派生数据难以分离的模块，继续排除。

自动检查可发现一部分文件类型、标识和凭据模式，无法证明著作权归属、识别所有秘密或判断所有派生内容。人工内容审查仍是发布前的必要步骤。检查和审查结果见 [发布说明](docs/PUBLICATION.md)。

如果发现误收内容，应停止后续发布并处理已经公开的历史；仅删除最新文件或 revert 不能消除历史中的内容。凭据泄漏还需立即撤销/轮换。可通过仓库 Issue 提供文件路径和问题描述，请勿上传争议原件、密钥或个人信息。

## 名称与关系

Command & Conquer、Red Alert 3、Electronic Arts 及相关名称归其各自权利人所有。此项目独立维护，不隶属、代表或获得上述权利人背书。

**English summary:** MIT covers original project code and written documentation; upstream portions of third-party patches retain their respective licenses. A small, individually reviewed set of stills from the maintainer's public progress videos is included solely as documentary illustration; game imagery and other third-party material in those stills are excluded from MIT. Game code, extracted assets, packages, credentials and protection-bypass material remain excluded. This policy governs repository inclusion, not additional restrictions on MIT recipients. Automated checks do not establish ownership or legal clearance. This project is independent and unaffiliated.
