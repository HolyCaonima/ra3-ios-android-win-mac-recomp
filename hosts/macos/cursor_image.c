#include "cursor_image.h"
#include <stdlib.h>
#include <string.h>

static uint16_t u16(const uint8_t *p) { return p[0] | (uint16_t)p[1] << 8; }
static uint32_t u32(const uint8_t *p) { return u16(p) | (uint32_t)u16(p+2) << 16; }
static int span(size_t size, size_t offset, size_t count) { return offset <= size && count <= size-offset; }

void ra3_cursor_free(ra3_cursor_image *image) {
    for (unsigned i=0; i<image->frames; i++) free(image->frame[i].rgba);
    memset(image, 0, sizeof(*image));
}

static int decode_cur(const uint8_t *data, size_t size, ra3_cursor_frame *frame, int legacy_ani) {
    if (size<22) return 0;
    /* Beam.ani also has an old cursor-directory tag (00 02 01 00), with
     * hotspot fields rather than icon planes/bpp. Limit this compatibility
     * path to the legacy RIFF-size convention, never standalone CUR input. */
    int legacy=legacy_ani && u16(data)==0x200 && u16(data+2)==1;
    if ((!legacy && u16(data)) || (u16(data+2)!=1 && u16(data+2)!=2) || !u16(data+4)) return 0;
    unsigned count=u16(data+4);
    if (!span(size,6,(size_t)count*16)) return 0;
    /* RA3 supplies one 32x32 image per frame. Prefer its native 32x32 entry
     * when a CUR also contains other display sizes. */
    const uint8_t *entry=data+6;
    for (unsigned i=0;i<count;i++)
        if (data[6+i*16]==32 && data[7+i*16]==32) { entry=data+6+i*16; break; }
    size_t bytes=u32(entry+8), offset=u32(entry+12);
    if (offset < 6+(size_t)count*16 || !span(size,offset,bytes) || bytes<40) return 0;
    const uint8_t *dib=data+offset;
    unsigned header=u32(dib), w=u32(dib+4), doubled=u32(dib+8), bpp=u16(dib+14);
    if (header<40 || header>bytes || !w || w>256 || !doubled || doubled>512 || (doubled&1) ||
        u16(dib+12)!=1 || (bpp!=24 && bpp!=32) || u32(dib+16)!=0) return 0;
    unsigned h=doubled/2, hot_x=(legacy || u16(data+2)==2) ? u16(entry+4) : 0;
    unsigned hot_y=(legacy || u16(data+2)==2) ? u16(entry+6) : 0;
    if (hot_x>=w || hot_y>=h) return 0;
    size_t pitch=((w*bpp+31)/32)*4, mask_pitch=((w+31)/32)*4;
    if (!span(bytes,header,pitch*h+mask_pitch*h)) return 0;
    uint8_t *rgba=malloc((size_t)w*h*4);
    if (!rgba) return 0;
    const uint8_t *pixels=dib+header, *mask=pixels+pitch*h;
    int has_alpha=0;
    if (bpp==32) for (unsigned y=0;y<h;y++) for (unsigned x=0;x<w;x++)
        has_alpha |= pixels[y*pitch+x*4+3];
    for (unsigned y=0;y<h;y++) for (unsigned x=0;x<w;x++) {
        const uint8_t *src=pixels+(h-1-y)*pitch+x*(bpp/8);
        uint8_t *dst=rgba+((size_t)y*w+x)*4;
        dst[0]=src[2]; dst[1]=src[1]; dst[2]=src[0];
        dst[3]=has_alpha ? src[3] : (mask[(h-1-y)*mask_pitch+x/8] & (0x80>>(x%8)) ? 0 : 255);
    }
    *frame=(ra3_cursor_frame){w,h,hot_x,hot_y,rgba};
    return 1;
}

int ra3_cursor_decode(const uint8_t *data, size_t size, ra3_cursor_image *out) {
    memset(out,0,sizeof(*out));
    if (size<12 || memcmp(data,"RIFF",4)) {
        if (!decode_cur(data,size,&out->frame[0],0)) return 0;
        out->frames=out->steps=1; out->rate[0]=out->duration=6;
        return 1;
    }
    size_t end=(size_t)u32(data+4)+8;
    /* The shipped Beam.ani counts the RIFF header in ckSize. Accept that
     * legacy +8 convention, but still require every child chunk in full. */
    int legacy_ani=end==size+8;
    if (legacy_ani) end=size;
    if (end<12 || end>size || memcmp(data+8,"ACON",4)) return 0;
    const uint8_t *header=NULL, *rates=NULL, *sequence=NULL;
    size_t rates_size=0, sequence_size=0;
    for (size_t p=12;p<end;) {
        if (!span(end,p,8)) goto fail;
        const uint8_t *chunk=data+p; size_t n=u32(chunk+4), v=p+8;
        if (!span(end,v,n+(n&1))) goto fail;
        if (!memcmp(chunk,"anih",4)) {
            if (header || n<36 || u32(data+v)<36) goto fail;
            header=data+v;
        } else if (!memcmp(chunk,"rate",4)) { rates=data+v; rates_size=n; }
        else if (!memcmp(chunk,"seq ",4)) { sequence=data+v; sequence_size=n; }
        else if (!memcmp(chunk,"LIST",4) && n>=4 && !memcmp(data+v,"fram",4)) {
            for (size_t f=v+4;f<v+n;) {
                if (!span(v+n,f,8)) goto fail;
                size_t bytes=u32(data+f+4), start=f+8;
                if (!span(v+n,start,bytes+(bytes&1))) goto fail;
                if (!memcmp(data+f,"icon",4)) {
                    if (out->frames==RA3_CURSOR_MAX_FRAMES ||
                        !decode_cur(data+start,bytes,&out->frame[out->frames],legacy_ani)) goto fail;
                    out->frames++;
                }
                f=start+bytes+(bytes&1);
            }
        }
        p=v+n+(n&1);
    }
    if (!header || !(u32(header+32)&1) || !out->frames || u32(header+4)!=out->frames) goto fail;
    out->steps=u32(header+8);
    if (!out->steps || out->steps>RA3_CURSOR_MAX_STEPS ||
        (rates && rates_size<(size_t)out->steps*4) ||
        ((u32(header+32)&2) && (!sequence || sequence_size<(size_t)out->steps*4))) goto fail;
    for (unsigned i=0;i<out->steps;i++) {
        out->sequence[i]=(u32(header+32)&2) ? u32(sequence+i*4) : i;
        out->rate[i]=rates ? u32(rates+i*4) : u32(header+28);
        if (out->sequence[i]>=out->frames || !out->rate[i]) goto fail;
        out->duration+=out->rate[i];
    }
    return 1;
fail:
    ra3_cursor_free(out);
    return 0;
}

unsigned ra3_cursor_frame_at(const ra3_cursor_image *image, uint64_t milliseconds) {
    if (!image->duration) return 0;
    uint64_t tick=((milliseconds/1000)*60+(milliseconds%1000)*60/1000)%image->duration;
    for (unsigned i=0;i<image->steps;i++) {
        if (tick<image->rate[i]) return image->sequence[i];
        tick-=image->rate[i];
    }
    return 0;
}
