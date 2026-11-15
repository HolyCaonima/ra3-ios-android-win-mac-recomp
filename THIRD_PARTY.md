# 致谢与来源

本次公开版本不包含 vendored 第三方源码，也不发布第三方项目的修改补丁。外部项目在这里作为研究背景、依赖说明或阅读参考列出；它们各自的许可证不会被本仓库的 MIT 取代。

| 项目 | 与本版本的关系 |
| --- | --- |
| [sc2-android-recomp](https://github.com/HolyCaonima/sc2-android-recomp) | README 组织及公开边界的参考；没有复制其源码或文档段落 |
| [pcrecomp](https://github.com/sp00nznet/pcrecomp) | 开发路线使用的静态翻译工具背景；本次不分发翻译器、修改版运行时或生成物 |
| [DXVK](https://github.com/doitsujin/dxvk) | Android/Apple 图形路线涉及的外部项目；源码与平台补丁均未收录 |
| [MoltenVK](https://github.com/KhronosGroup/MoltenVK) | Apple 图形路线涉及的外部项目；源码、库与补丁均未收录 |
| [SDL](https://github.com/libsdl-org/SDL) | 桌面窗口、输入和音频背景；不作为公开示例的依赖 |
| [Pillow](https://github.com/python-pillow/Pillow) | 图像差异工具的外部 Python 依赖；通过包管理器安装，未捆绑源码 |
| [CMake](https://cmake.org/) | 构建配置示例的外部工具 |

`cmake/BuildProfile.cmake` 和两个模板从项目的通用配置逻辑整理而来，移除了游戏版本元数据字段与开发上下文描述。`tools/shotdiff.py` 从项目的小型图像统计脚本整理而来，增加独立函数、参数检查和可测试接口。这些文件不读取游戏、私有配置或生成代码。

其余文档、发布检查、示例和测试为此次公开版本新写。逐文件类别见 [PUBLICATION.json](PUBLICATION.json)。本次没有把来源复杂的兼容层、原生替换函数或上游修改版本重新标成 MIT。
