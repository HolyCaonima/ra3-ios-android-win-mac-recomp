# MoltenVK residency lifetime patch

Base: [MoltenVK v1.4.2](https://github.com/KhronosGroup/MoltenVK/tree/db66022459ffb663aa2b50f6b018bc2e124f5edf), commit `db66022459ffb663aa2b50f6b018bc2e124f5edf`.
The patch contains Apache-2.0 upstream context; see [license](../../LICENSES/MoltenVK.txt) and [copyright / modification notices](../../LICENSES/MoltenVK-NOTICE.txt). It is a project modification, not an upstream release. The standalone probe and build script are original MIT code.

## Why this patch exists

In an iPad development run, Metal API Validation stopped during buffer destruction: a shared buffer was released while a scheduled command buffer still referenced it. MoltenVK's addressable-buffer enumeration includes buffers the Vulkan application does not directly use in that submission, so the application's own resource retirement did not account for this extra residency reference.

The patch snapshots and retains those Metal buffers under the registry lock, then releases them in the command-buffer completion handler. The change is guarded by `MVK_IOS`. It does not suppress validation, disable allocator cleanup or insert a device-wide idle wait.

One subsequent iPad gameplay retest passed; longer play and the memory/performance cost remain unverified. The separate DXVK static-stride patch addresses a different Metal assertion.

## Build outside this repository

With Xcode and the upstream build dependencies installed:

```sh
MOLTENVK_SOURCE=/path/to/new/moltenvk-source \
MOLTENVK_BUILD=/path/to/moltenvk-build \
bash tools/moltenvk/build.sh iphoneos
```

Use `iphonesimulator` for the simulator. The script clones v1.4.2, verifies the commit, applies the patch, fetches upstream-pinned dependencies and builds a static library. Paths should be absolute. No signing identity or application provisioning is involved.

To fetch and inspect the patch without building:

```sh
python -B tools/upstream.py moltenvk /path/to/new/moltenvk-source
```

## Standalone Metal probe (macOS)

```sh
xcrun clang++ -std=c++17 -fno-objc-arc -fobjc-weak \
  -framework Foundation -framework Metal tools/moltenvk/probe_metal_residency.mm \
  -o /tmp/ra3-metal-residency
MTL_DEBUG_LAYER=1 MTL_DEBUG_LAYER_ERROR_MODE=assert /tmp/ra3-metal-residency
```

The probe uses a tiny synthetic kernel and 128 real GPU submissions to exercise early owner destruction, deferred residency encoding, completion ownership, output correctness and eventual release. Half use placement-heap buffers. This checks the Metal ownership mechanism on the Mac; it is not an iPad or complete MoltenVK test. No game shader is included.
