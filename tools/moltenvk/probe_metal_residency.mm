#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <cassert>
#include <cstdio>

// Native Metal probe: an otherwise unused buffer is declared resident, just as
// MoltenVK's GPU-addressable-buffer enumeration does. Its app owner disappears
// before deferred encoding; a completion-owned snapshot must bridge that gap.
int main() {
  @autoreleasepool {
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    assert(device);
    id<MTLCommandQueue> queue = [device newCommandQueue];
    NSError* error = nil;
    id<MTLLibrary> lib = [device newLibraryWithSource:@"#include <metal_stdlib>\nusing namespace metal; kernel void touch(device uint* out [[buffer(0)]], uint i [[thread_position_in_grid]]) { out[i] = i + 7; }" options:nil error:&error];
    assert(lib && !error);
    id<MTLFunction> fn = [lib newFunctionWithName:@"touch"];
    id<MTLComputePipelineState> pipeline = [device newComputePipelineStateWithFunction:fn error:&error];
    assert(pipeline && !error);
    for (unsigned iteration = 0; iteration < 128; ++iteration) {
      __weak id<MTLBuffer> weakResource = nil;
      @autoreleasepool {
        id<MTLHeap> heap = nil;
        id<MTLBuffer> extra = nil;
        if (iteration % 2) {
          MTLHeapDescriptor* heapDesc = [MTLHeapDescriptor new];
          heapDesc.type = MTLHeapTypePlacement;
          heapDesc.storageMode = MTLStorageModeShared;
          heapDesc.hazardTrackingMode = MTLHazardTrackingModeTracked;
          heapDesc.size = 2 * 1024 * 1024;
          heap = [device newHeapWithDescriptor:heapDesc];
          [heapDesc release];
          extra = [heap newBufferWithLength:1024 * 1024 options:MTLResourceStorageModeShared offset:0];
        } else {
          extra = [device newBufferWithLength:1024 * 1024 options:MTLResourceStorageModeShared];
        }
        assert(extra);
        weakResource = extra;
        id<MTLBuffer> output = [device newBufferWithLength:256 * sizeof(unsigned) options:MTLResourceStorageModeShared];
        MTLCommandBufferDescriptor* desc = [MTLCommandBufferDescriptor new];
        desc.retainedReferences = NO;
        id<MTLCommandBuffer> command = [queue commandBufferWithDescriptor:desc];
        [desc release];
        NSMutableArray<id<MTLBuffer>>* snapshot = [[NSMutableArray alloc] initWithObjects:extra, nil];
        [command addCompletedHandler:^(id<MTLCommandBuffer>) { [snapshot removeAllObjects]; }];
        [snapshot release];
        [extra release];
        [heap release];
        assert(weakResource != nil);
        id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
        [encoder setComputePipelineState:pipeline];
        [encoder setBuffer:output offset:0 atIndex:0];
        [encoder useResource:extra usage:MTLResourceUsageRead | MTLResourceUsageWrite];
        [encoder dispatchThreads:MTLSizeMake(256, 1, 1) threadsPerThreadgroup:MTLSizeMake(32, 1, 1)];
        [encoder endEncoding];
        [command commit];
        [command waitUntilCompleted];
        assert(command.status == MTLCommandBufferStatusCompleted);
        for (unsigned i = 0; i < 256; ++i) assert(((unsigned*)output.contents)[i] == i + 7);
        [output release];
      }
      // This also catches retaining snapshots indefinitely after completion.
      assert(weakResource == nil);
    }
    [pipeline release]; [fn release]; [lib release]; [queue release]; [device release];
  }
  puts("PASS: 128 real Metal submissions; early owner release, correct output, resources reclaimed after completion");
}
