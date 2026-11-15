# 致谢与来源

本仓库的原创代码与文档使用 MIT；第三方作品保留各自许可。下面明确区分上游代码上下文、外部依赖与方法参考，不将上游作品重新标为项目原创。

| 项目 | 本仓库中的关系 | 许可 / 声明 |
| --- | --- | --- |
| **[elkir0/sc2-android-recomp](https://github.com/elkir0/sc2-android-recomp)** | 原作者 elkir0 的静态重编译项目；README 的组织方式与方法说明参考，没有复制其源码或文档段落 | 链接指向原仓库，而不是维护者的 fork |
| [pcrecomp](https://github.com/sp00nznet/pcrecomp) | `tools/lift` 扩展所针对的外部翻译器接口；未打包上游翻译器或生成物 | [MIT notice](LICENSES/pcrecomp.txt)，Copyright 2026 sp00nz；扩展的完整项目运行时尚未包含 |
| [DXVK](https://github.com/doitsujin/dxvk) | `tools/dxvk/00*.patch` 包含上游上下文和项目修改，基于 v3.1.1 / `b1a1c99ab52b687cf950d62c88bc2fa316b41663` | 上游 **zlib/libpng**，[原始声明](LICENSES/DXVK.txt)；项目新增部分 MIT，合并后的作品仍须遵守上游条款 |
| [MoltenVK](https://github.com/KhronosGroup/MoltenVK) | `tools/moltenvk/0001-*.patch` 基于 v1.4.2 / `db66022459ffb663aa2b50f6b018bc2e124f5edf` | 上游 **Apache-2.0**，[许可](LICENSES/MoltenVK.txt)、[版权与修改声明](LICENSES/MoltenVK-NOTICE.txt)；未重新标成 MIT |
| [ValvePython/steam](https://github.com/ValvePython/steam) | 本地 Steam manifest reader 的 protobuf wire schema 参考；未复制或捆绑其实现 | 文件头注明 schema 来源；只读取调用者提供的本地明文清单 |
| [SDL](https://github.com/libsdl-org/SDL) | macOS DXVK WSI 的外部依赖 | 由使用者单独安装；未捆绑 |
| [Capstone](https://github.com/capstone-engine/capstone) | lifter 扩展的外部依赖 | 未捆绑；随兼容的 pcrecomp 环境安装 |
| [Pillow](https://github.com/python-pillow/Pillow)、[CMake](https://cmake.org/) | 图像工具与配置测试依赖 | 由包管理器安装，未捆绑源码 |

资源解析器、光标解码器、路径组合、LAN 传输和平台发现桥接来自维护者开发项目的手写工具/运行时，不是游戏函数的 lift 输出。BIG / CSF / RefPack 工具只包含格式处理逻辑；实际内容由调用者提供。原始公开版的构建配置、图像统计工具继续保留。

发布适配包括去除本机路径和私有配置，拆分独立入口、保留合成用例、将源码与构建输出放在仓库外。具体来源按文件记录在 [PUBLICATION.json](PUBLICATION.json)。

演示截图来自维护者的 [Bilibili 公开视频](https://space.bilibili.com/3546857907162034)，其中的游戏画面与其他第三方内容不纳入 MIT。[来源与时间点](docs/SCREENSHOTS.md)。
