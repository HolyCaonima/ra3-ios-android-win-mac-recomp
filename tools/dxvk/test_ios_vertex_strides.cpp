#include "dxvk_format.h"
#include "dxvk_util.h"
#include "dxvk_graphics_state.h"
#include <cassert>
int main() {
  dxvk::DxvkGraphicsPipelineStateInfo a;
  assert(!a.useDynamicVertexStrides());
  a.il=dxvk::DxvkIlInfo(1,1);
  a.ilBindings[0]=dxvk::DxvkIlBinding(0,0,VK_VERTEX_INPUT_RATE_VERTEX,1);
#ifdef DXVK_WSI_IOS
  assert(!a.useDynamicVertexStrides());
#else
  assert(a.useDynamicVertexStrides());
#endif
  for (unsigned stride : {16u,32u,2048u}) {
    auto b=a; b.ilBindings[0].setStride(stride);
    assert(!b.useDynamicVertexStrides());
    assert(b.ilBindings[0].description().stride==stride);
    assert(!a.eq(b)); assert(a.hash()!=b.hash());
    auto c=b; assert(c.eq(b)); assert(c.hash()==b.hash());
  }
  auto b=a; b.il=dxvk::DxvkIlInfo(2,2);
  b.ilBindings[1]=dxvk::DxvkIlBinding(1,32,VK_VERTEX_INPUT_RATE_INSTANCE,2);
  assert(!b.useDynamicVertexStrides());
  assert(b.ilBindings[0].description().stride==0);
  assert(b.ilBindings[1].description().stride==32);
  assert(b.ilBindings[1].divisor()==2);
}
