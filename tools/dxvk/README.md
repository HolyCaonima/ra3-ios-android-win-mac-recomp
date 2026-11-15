# DXVK platform patches

Base: [DXVK v3.1.1](https://github.com/doitsujin/dxvk/tree/b1a1c99ab52b687cf950d62c88bc2fa316b41663), commit `b1a1c99ab52b687cf950d62c88bc2fa316b41663`.
These are project modifications, **not an upstream DXVK release**. Upstream portions retain the zlib/libpng license and copyright notices in [LICENSES/DXVK.txt](../../LICENSES/DXVK.txt). Original additions are MIT; upstream terms still apply to the patched source.

## Apply and build

Python, Git, Meson, Ninja and glslang are required. macOS additionally needs SDL2 and the Apple toolchain; Android needs an NDK; iOS needs Xcode and an iOS SDK; Windows cross compilation needs i686 MinGW tools on PATH. Fetch/build outputs must be outside this public checkout.

```sh
python -B tools/upstream.py dxvk /path/to/new/dxvk-source
python -B tools/dxvk/build.py macos --source /path/to/new/dxvk-source --build /path/to/new/dxvk-build
```

Replace `macos` with `iphoneos`, `iphonesimulator`, `win32`, or `android --ndk /path/to/ndk --abi arm64-v8a`. Use a fresh build directory for each platform/configuration. For a subsequent build, run `ninja -C /path/to/dxvk-build`.

The fetch script checks the exact upstream commit, applies all 14 patches in order and initializes upstream-pinned submodules. It refuses an existing destination. This builds the D3D9 renderer, not a game executable or signed app. The host must supply its surface/lifecycle callbacks. Apple integration also needs MoltenVK; iOS links the static renderer and MoltenVK into its host application.

## Patch map

| Patch | Purpose |
| --- | --- |
| 0001 | Android native WSI, optional maintenance5/6 and robustness2, stand-ins for null resources |
| 0002 | Opt-in pipeline input diagnostics; generated shader dumps remain local |
| 0003 | Fold unused sampler paths before mobile driver compilation |
| 0004 | Optional single-queue policy for Android |
| 0005 | Select a supported composite alpha mode |
| 0006 | Convert unsupported scaled vertex formats using shader IR |
| 0007 | Fit presentation to the surface and map cursor/input regions |
| 0008 | Darwin / MoltenVK compatibility and valid fallback buffer bindings |
| 0009 | Report software vertex processing support consistently with geometry capability |
| 0010 | Apply sampler specialization on Apple |
| 0011 | Create SDL Cocoa surfaces on the main thread |
| 0012 | iOS CAMetalLayer WSI and static Vulkan dispatch |
| 0013 | Report missing required iOS capabilities without enabling unsupported features |
| 0014 | Keep iOS vertex strides static and part of the pipeline key |

The series applies cleanly to the pinned base. This publication pass does not rebuild the entire renderer for all four SDKs. Device progress and outstanding issues are recorded in [STATUS](../../docs/STATUS.md).

The stride regression test compiles the real DXVK state structures twice, with and without the iOS policy, from an existing configured iOS build:

```sh
python -B tools/dxvk/test_ios_vertex_strides.py /path/to/dxvk-ios-build/compile_commands.json
```

It checks zero and nonzero strides, instance bindings, and distinct pipeline keys. It does not replace Metal validation on an iPad.
