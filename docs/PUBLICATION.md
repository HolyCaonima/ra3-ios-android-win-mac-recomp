# 公开内容整理与复核

公开仓库在桌面独立目录建立，使用独立 Git 历史，没有迁移开发仓库的 `.git`、LFS 对象或私有制品。维护者确认的范围是：**游戏资源本体和生成的 lift C 不公开，其余原创方法、工具与代码尽量公开。**

## 2026-11-15 扩充

| 类别 | 公开内容与处理 |
| --- | --- |
| 资源工具 | BIG / CSF / RefPack 实现、本地 Steam manifest reader、SkuDef 递归解析；移除固定私有目录、版本清单和自动本机配置 |
| 静态翻译 | 原子与 SSE 扩展、通用非局部跳转转换、PE32 导入查看；没有生成的游戏函数或真实字节测试向量 |
| 宿主组件 | CUR / ANI 解码、UTF-16 路径组合、UDP 发现传输、Apple Bonjour、Android NSD 桥接；列明仍需宿主提供的接口 |
| 图形 | 14 个 DXVK 补丁、1 个 MoltenVK 补丁及构建/验证工具；保留上游许可、版权和修改声明 |
| 配图 | 从维护者公开 Bilibili 视频截取四张静帧；裁去网页、后台终端及个人路径 |
| 既有工具 | Dev / Release 配置、图像差异、公开检查与合成测试继续保留 |
| 持续排除 | 游戏资源、生成 lift C、专有 DLL/程序、游戏 shader / 缓存、游戏包、密钥/签名材料和私有历史 |

完整宿主集成、完整翻译入口、其他尚未完成来源/依赖拆分的运行时模块不在本次文件清单内。代码可以处理调用者本地输入，不会仅因为它与游戏相关就自动排除。具体可独立运行的部分和集成缺项见 [TOOLS.md](TOOLS.md)。

README 改为成果、实机画面、状态、方法和组件目录的顺序；中英文致谢均指向原作者 **[elkir0/sc2-android-recomp](https://github.com/elkir0/sc2-android-recomp)**。

## 本次验证

- 26 项 Python unittest 用例在 macOS 全部通过，包括真实 C 组件的编译与运行。CUR 用例启用 AddressSanitizer / UndefinedBehaviorSanitizer；UDP 用例只使用回环通信。
- Apple DNS-SD provider 在 macOS SDK 下编译通过；Android NSD / JNI 桥接此次没有重新完成应用集成构建。
- 14 个 DXVK 补丁依次应用于干净的 `b1a1c99ab52b687cf950d62c88bc2fa316b41663` 源码通过。
- MoltenVK 补丁应用于干净的 `db66022459ffb663aa2b50f6b018bc2e124f5edf` 源码通过。
- 原生 Metal 探针启用 Metal API Validation，128 次实际 GPU 提交通过，验证输出和完成后的资源释放。
- Python 文件语法、新构建入口参数帮助和 MoltenVK shell 语法检查通过。此次没有重新编译所有平台的完整 DXVK / MoltenVK，也没有把已有开发测试冒充本次公开版本的实机回归。
- 发布前检查当前文件、实际暂存内容及独立公开历史；四张 JPEG 按内容哈希核对。

## 来源与许可

[PUBLICATION.json](../PUBLICATION.json) 列出每个公开文件及来源。项目原创部分使用标准 MIT，不附加非商业限制。DXVK 上游上下文使用 zlib/libpng，MoltenVK 使用 Apache-2.0；原始许可和版权声明在 [LICENSES](../LICENSES/) 中。补丁明确标注项目修改，未将其冒充上游版本。完整关系见 [THIRD_PARTY.md](../THIRD_PARTY.md)。

截图仅用于文档进度展示，其中的游戏画面不属于 MIT。四张 JPEG 小于 256 KiB，无 EXIF；[SCREENSHOTS.md](SCREENSHOTS.md) 记录来源、时间点和裁切。未上传原视频或提取的游戏素材。

## 发布检查

```sh
python -B tools/verify.py
git diff --cached
python -B tools/publication_guard.py --index
```

按清单暂存并审阅，提交后再检查新历史，确认目标仓库再推送。检查包含精确路径、文本/体积、常见秘密和个人路径、生成符号、LFS 指针、暂存内容与所有本地可达历史。图片仅精确路径与 SHA-256 匹配时放行；历史仍必须符合当前清单。更新截图应使用新文件名，并保留历史图片的审查记录。

本地 `.venv` 只从工作目录检查中排除，不能进入 Git。其余临时源码、构建输出和测试数据全部放在公开仓库之外。`.gitattributes` 只对补丁文本关闭 Git 的空白报错，以保留上游原样上下文；这不豁免公开内容扫描。

自动检查不能证明著作权归属、排除所有秘密或保证法律合规；源码、来源和画面仍需人工审查。CI 在上传后运行，不能替代发布前检查。历史扫描不覆盖本地不可见的远端引用或附件。
