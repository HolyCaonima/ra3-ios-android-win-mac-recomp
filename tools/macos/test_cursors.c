/* Synthetic inputs only; compile with ASan/UBSan when available. */
#include "../../hosts/macos/cursor_image.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void pixel_cases(void) {
    /* A bottom-up 2x2 CUR: two padded 24-bit rows and AND mask rows. */
    uint8_t cur[86]={0};
    cur[2]=2; cur[4]=1; cur[6]=cur[7]=2; cur[10]=1;
    cur[14]=64; cur[18]=22; cur[22]=40; cur[26]=2; cur[30]=4;
    cur[34]=1; cur[36]=24;
    cur[62]=255;             /* bottom-left blue */
    cur[65]=255; cur[66]=255; /* bottom-right cyan */
    cur[72]=255;             /* top-left red */
    cur[74]=255;             /* top-right green */
    cur[82]=0x40;            /* top-right transparent */
    ra3_cursor_image image;
    assert(ra3_cursor_decode(cur,sizeof(cur),&image));
    const uint8_t expected[]={255,0,0,255, 0,255,0,0, 0,0,255,255, 0,255,255,255};
    assert(image.frame[0].hot_x==1 && image.frame[0].hot_y==0);
    assert(!memcmp(image.frame[0].rgba,expected,sizeof(expected)));
    ra3_cursor_free(&image);
    /* A 32-bit DIB uses its alpha when at least one pixel is nonzero. */
    cur[36]=32;
    memset(cur+62,0,24); cur[72]=255; cur[73]=128;
    assert(ra3_cursor_decode(cur,sizeof(cur),&image));
    assert(image.frame[0].rgba[0]==255 && image.frame[0].rgba[3]==128);
    assert(image.frame[0].rgba[7]==0);
    ra3_cursor_free(&image);
    cur[10]=2; assert(!ra3_cursor_decode(cur,sizeof(cur),&image)); /* invalid hotspot */
    cur[10]=1; cur[18]=255; assert(!ra3_cursor_decode(cur,sizeof(cur),&image));
    image=(ra3_cursor_image){.frames=2,.steps=3,.sequence={1,0,1},.rate={3,6,3},.duration=12};
    assert(ra3_cursor_frame_at(&image,0)==1);
    assert(ra3_cursor_frame_at(&image,49)==1);
    assert(ra3_cursor_frame_at(&image,50)==0);
    assert(ra3_cursor_frame_at(&image,149)==0);
    assert(ra3_cursor_frame_at(&image,150)==1);
    assert(ra3_cursor_frame_at(&image,200)==1);
}

int main(void) {
    pixel_cases();
    puts("PASS: synthetic CUR pixels, alpha, masks, hotspots and ANI timing");
    return 0;
}
