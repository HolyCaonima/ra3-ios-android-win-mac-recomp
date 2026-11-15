/* Lexical UTF-16 PathCombineW support. No host filesystem access. */
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

static size_t ra3_wpath_len(const uint16_t *s) {
    size_t n = 0;
    if (s) while (n < 260 && s[n]) n++;
    return n;
}

static size_t ra3_wpath_root(const uint16_t *s, size_t n) {
    if (n >= 2 && s[1] == ':') return n >= 3 && s[2] == '\\' ? 3 : 2;
    if (n >= 2 && s[0] == '\\' && s[1] == '\\') {
        size_t i = 2;
        while (i < n && s[i] != '\\') i++;
        if (i < n) i++;
        while (i < n && s[i] != '\\') i++;
        return i;
    }
    return n && s[0] == '\\' ? 1 : 0;
}

static int ra3_path_combine_w(uint16_t *dest, const uint16_t *dir, const uint16_t *file) {
    uint16_t joined[520], result[520];
    size_t dn = ra3_wpath_len(dir), fn = ra3_wpath_len(file), n = 0;
    if (!dest) return 0;
    if ((!dir && !file) || dn >= 260 || fn > 256) { dest[0] = 0; return 0; }
    if (!fn) {
        if (dn) memcpy(joined, dir, dn * 2);
        n = dn;
    } else if (!dn || (fn >= 2 && file[1] == ':') || (fn >= 2 && file[0] == '\\' && file[1] == '\\')) {
        memcpy(joined, file, fn * 2); n = fn;
    } else {
        n = file[0] == '\\' ? ra3_wpath_root(dir, dn) : dn;
        if (file[0] == '\\' && !n) { dest[0] = 0; return 0; }
        if (n) memcpy(joined, dir, n * 2);
        if (file[0] == '\\') {
            if (n && joined[n - 1] == '\\') n--;
        } else if (n && joined[n - 1] != '\\') joined[n++] = '\\';
        memcpy(joined + n, file, fn * 2); n += fn;
    }
    /* Canonicalization clamps at the drive or leading slashes, unlike the
     * rooted-file combination above, which preserves the UNC share. */
    size_t root = n >= 3 && joined[1] == ':' && joined[2] == '\\' ? 3
                : n && joined[0] == '\\' ? (n >= 2 && joined[1] == '\\' ? 2 : 1) : 0;
    size_t used = root, i = root;
    if (root) memcpy(result, joined, root * 2);
    while (i < n) {
        if (joined[i] == '\\') { result[used++] = joined[i++]; continue; }
        size_t start = i;
        while (i < n && joined[i] != '\\') i++;
        size_t len = i - start;
        if (len == 1 && joined[start] == '.') {
            if (i < n) i++;
            else if (used > root && result[used - 1] == '\\') used--;
        } else if (len == 2 && joined[start] == '.' && joined[start + 1] == '.') {
            int had_component = used > root;
            if (used > root && result[used - 1] == '\\') used--;
            while (used > root && result[used - 1] != '\\') used--;
            if (used == 0 && had_component) result[used++] = '\\';
            if (i < n) i++;
            else if (used > root && used > 1 && result[used - 1] == '\\') used--;
        } else {
            memcpy(result + used, joined + start, len * 2); used += len;
        }
    }
    if (!used || (used == 2 && result[1] == ':')) result[used++] = '\\';
    if (used >= 260) { dest[0] = 0; return 0; }
    result[used] = 0;
    memcpy(dest, result, (used + 1) * 2);
    return 1;
}
