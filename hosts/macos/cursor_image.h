#pragma once
#include <stddef.h>
#include <stdint.h>

/* Decoded Windows CUR / RIFF ACON, independent of SDL and the guest arena. */
#define RA3_CURSOR_MAX_FRAMES 128
#define RA3_CURSOR_MAX_STEPS 512
typedef struct {
    unsigned width, height, hot_x, hot_y;
    uint8_t *rgba;
} ra3_cursor_frame;
typedef struct {
    unsigned frames, steps;
    ra3_cursor_frame frame[RA3_CURSOR_MAX_FRAMES];
    uint32_t sequence[RA3_CURSOR_MAX_STEPS], rate[RA3_CURSOR_MAX_STEPS];
    uint64_t duration; /* jiffies, 1/60 second */
} ra3_cursor_image;
int ra3_cursor_decode(const uint8_t *data, size_t size, ra3_cursor_image *out);
void ra3_cursor_free(ra3_cursor_image *image);
unsigned ra3_cursor_frame_at(const ra3_cursor_image *image, uint64_t milliseconds);
