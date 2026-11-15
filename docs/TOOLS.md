# 工具与组件指南

本次公开的是开发项目中的实际组件，不只是架构说明。下面区分独立工具、集成组件和依赖上游的扩展。输入与输出均放在公开仓库之外；工具可以读取你有权使用的本地文件，仓库本身不附带这些文件。

## 资源处理

`tools/resources/language_assets.py` 提供：

- `read_big_member(path, name)`：从 BIG4/BIGF 读取单个成员，按需解压 RefPack。
- `unpack_refpack(data)`：解压 RefPack，检查回溯距离和输出大小，限制到 32 MiB。
- `read_csf(data)` / `write_csf(header, entries)`：保留 CSF 标签、字符串记录与语言字段，供本地语言包处理使用。
- `single_member_big(name, data)`：生成单成员 BIGF；内容由调用者提供。

这是小型本地工具库，不是完整的通用归档器。测试使用自行构造的四字节文本、CSF 和 BIG，没有实际游戏字串。配置链查看：

```sh
python -B tools/resources/skudef.py /path/to/local/resources example.skudef
```

它递归展开 `add-config`、检查循环和路径越界、验证 `add-big` 文件存在，忽略 `set-exe`；不复制或修改输入。输出采用原兼容层的 `Z:` 宿主根映射约定，可用于理解资源装载顺序。原私有工具中的固定安装路径、版本清单、可执行文件复制和自动本机配置没有搬入。

`tools/versions/steam_manifest.py` 的 `read_manifest(path)` 解析调用者指定的本地明文 depot manifest，返回文件名、大小、SHA-1。拒绝加密文件名，不接触 Steam 账号、凭据或网络，也不把本地清单当成远程签名认证。

## 静态翻译扩展

| 文件 | 接口与用途 | 集成依赖 |
| --- | --- | --- |
| `tools/lift/lift32_atomic_ra3.py` | `install()` 包装 `Lifter._lift_instruction`，生成原子交换、加法、比较交换和 CAS 循环 | pcrecomp `lift32`；运行时 `recomp_xadd*` / `recomp_xchg*` / `recomp_cas*` |
| `tools/lift/lift32_sse_ra3.py` | `lift_sse_ra3` 扩展整数 lane 运算、饱和、交织与窄化 | pcrecomp `lift32_sse`、Capstone；兼容的 `xmm_t` / 内存访问接口 |
| `tools/lift/nonlocal_jumps.py` | `repair_generated(out, pe)` 补齐 setjmp 续点与 longjmp 宿主落点 | PE adapter 的 `base/data/sections/exports()/iat()/off()`；相应 `RECOMP_EH_*` / `RECOMP_SETJMP_*` / `RECOMP_LONGJMP_RESUME` 宏 |
| `tools/lift/peimports.py` | 独立查看 PE32 DLL 名、函数名和 ordinal | Python；调用者本地 PE32 输入 |

```sh
python -B tools/lift/peimports.py /path/to/local/example.exe
```

前三项是实际生成器扩展，**不是生成出的游戏 C**。它们来自项目所用的 pcrecomp 接口，运行时配套与完整翻译入口尚未一起公开；不能宣称可直接套用任意上游版本。安装时将对应 pcrecomp `tools/lift` 加入 Python 模块路径，先装 SSE handler，再调用 atomic `install()`；不要重复包装。后续集成仍须指令语义差分测试。公开 CI 不证明这些扩展的完整 CPU 等价性，也不证明 ARM64 上普通访存已满足 x86 内存序。

PE 导入查看器是面向可信本地 PE32 的小工具，不是面向不可信上传文件的服务。非局部跳转转换会原地写入指定输出目录，应对本地生成副本使用。

## 宿主组件

- `hosts/macos/cursor_image.{c,h}`：独立 CUR / ANI 解码器，没有 SDL 依赖。输出 RGBA 帧、热点、序列与时序；名称来自原宿主目录，解析器本身可以跨平台使用。`tools/macos/test_cursors.c` 只包含合成像素测试。
- `runtime/hle/path_combine.h`：UTF-16 路径组合与词法规范化，不访问宿主文件系统。公开测试覆盖盘符、根路径、UNC、父目录、Unicode 和长度边界；不宣称覆盖 Windows API 的全部行为。
- `runtime/hle/lan_discovery.{c,h}`：POSIX UDP 传输。调用者在绑定/关闭 socket 后通知组件，通过 `ra3_lan_send/recv` 转发已有数据；DNS-SD 提供地址，报文内容保持不变。原广播和补充单播的跨路径重复副本被配对去重，同路径重传保留。
- `hosts/apple/bonjour.c`：系统 DNS-SD + 串行 dispatch queue，使用 `ra3_apple_bonjour_init()` 初始化一次。
- `hosts/android/bonjour.c` 与 `BonjourDiscovery.java`：JNI / Android NSD 桥接。需要应用提供 `GameActivity.nativeBonjourPeer(String,String,int,boolean)` 与 `bonjourPort(int,boolean,String)`；后者调用 `BonjourDiscovery.port`。完整 Activity、应用生命周期、网络权限和打包工程没有包含。需按目标 Android SDK 的 NSD 权限要求集成。

LAN 组件是 IPv4 局域网发现辅助层，不是公网匹配服务。`wire` 字段用于版本过滤，不是认证；仍需由调用方处理不可信网络输入。移植时必须配套关闭通知，不能将这些组件直接理解成完整网络兼容层。

## 图形与构建

- [DXVK 补丁说明](../tools/dxvk/README.md)：Android / Apple WSI、可选扩展、采样器特化、坐标与顶点 stride。
- [MoltenVK 补丁说明](../tools/moltenvk/README.md)：iOS Metal residency 对象寿命与原生探针。
- `cmake/BuildProfile.cmake`：独立 Dev / Release 配置模块；示例在 `examples/build-profile`。
- `tools/shotdiff.py`：比较两张本地图片的统计差异，不把数值差异等同于图形正确性。

## 验证范围

`python -B tools/verify.py` 运行公开内容检查、合成资源测试、配置测试、图像工具测试、CUR 解码器的 ASan/UBSan 检查、UTF-16 路径测试及真实 loopback UDP 测试。UDP 测试拦截广播，流量仅发向回环地址，需要 8086–8093 中两个空闲端口。macOS 额外编译 Apple DNS-SD provider；Linux 跳过这一项。

平台图形构建需要各自 SDK；完整 renderer 编译和真机测试不在快速 CI 内。补丁应用检查、Metal 探针等发布验证记录见 [PUBLICATION.md](PUBLICATION.md)。
