"""Preserve host control flow for lifted CRT setjmp/longjmp.

Keep the CRT's guest register saving, value normalization and SEH handling.
Only give setjmp a real continuation address and bridge longjmp's final
indirect jump to the existing host landing-pad machinery. No DLL addresses
are hardcoded: exports and FF25 import thunks identify the relevant functions.
"""
import re
import struct
from pathlib import Path

SETJMP = {'_setjmp', '_setjmp3', 'setjmp'}
LONGJMP = {'longjmp', '_longjmpex'}
MARKER = '/* RA3 nonlocal control flow */'


def repair_generated(out, pe):
    exports = pe.exports()
    setters = {pe.base + r for n, r in exports.items() if n in SETJMP}
    jumpers = {pe.base + r for n, r in exports.items() if n in LONGJMP}
    slots = {a for a, (_, n) in pe.iat().items() if n in SETJMP}
    # Linker import thunks: jmp dword ptr [IAT slot].
    for _, rva, vs, rawsize, raw, chars in pe.sections:
        if not chars & 0x20000000:
            continue
        data = pe.data[raw:raw + rawsize]
        for m in re.finditer(b'\xff\x25', data):
            if m.start() + 6 <= len(data) and struct.unpack_from('<I', data, m.start() + 2)[0] in slots:
                setters.add(pe.base + rva + m.start())
    changed = []
    for path in sorted(Path(out).glob('recomp_*.c')):
        old = path.read_text(encoding='utf-8')
        parts = re.split(r'(?=^void sub_[0-9A-F]{8}\(void\) \{)', old, flags=re.M)
        for k, body in enumerate(parts):
            head = re.match(r'void sub_([0-9A-F]{8})', body)
            if not head or MARKER in body:
                continue
            addr = int(head[1], 16)
            resumes = []
            def call(m):
                macro, arg, pc = m[1], m[2], int(m[3], 16)
                direct = re.fullmatch(r'sub_([0-9A-F]{8})', arg)
                indirect = re.fullmatch(r'MEM32\(0x([0-9A-Fa-f]+)\)', arg)
                if not ((direct and int(direct[1], 16) in setters) or
                        (indirect and int(indirect[1], 16) in slots)):
                    return m[0]
                off = pe.off(pc - pe.base)
                opcode = pe.data[off:off + 2]
                size = 5 if opcode[0] == 0xe8 else 6 if opcode == b'\xff\x15' else 0
                if not size:
                    raise ValueError(f'unsupported setjmp call at {pc:08X}')
                resume = pc + size
                resumes.append(resume)
                kind = 'CALL' if macro == 'CALL' else 'ICALL'
                return f'RECOMP_SETJMP_{kind}({arg}, 0x{resume:08X}u); /* 0x{pc:08X}:'
            body = re.sub(r'RECOMP_(CALL|ICALL)\((.*?)\); /\* 0x([0-9A-F]{8}):', call, body)
            if resumes:
                # Every exit must unlink the stack-owned host frame.
                body = body.replace('RECOMP_REGS_OUT();', 'RECOMP_EH_LEAVE(); RECOMP_REGS_OUT();')
                entry = f'RECOMP_ENTER(0x{addr:08X}u);'
                body = body.replace(entry, entry + '\n    RECOMP_EH_ENTER();', 1)
                for resume in resumes:
                    label = f'L_{resume:08X}:'
                    if label not in body:
                        pattern = rf'(RECOMP_SETJMP_.*?0x{resume:08X}u\);[^\n]*\n    RECOMP_FLAGS_IN\(\);)'
                        body, count = re.subn(pattern, r'\1\n' + label, body, count=1)
                        if count != 1:
                            raise ValueError(f'missing continuation {resume:08X}')
                cases = ''.join(f'      case 0x{r:08X}u: goto L_{r:08X};\n' for r in resumes)
                if '  _ljump:' in body:
                    body = body.replace('switch (_itail_tgt) {', 'switch (_itail_tgt) {\n' + cases, 1)
                else:
                    pos = body.rfind('}')
                    body = (body[:pos] + '    return;\n  _ljump:\n    switch (_itail_tgt) {\n' + cases +
                            '      default: abort();\n    }\n' + body[pos:])
            if addr in jumpers:
                needle = 'default: RECOMP_ITAIL(_itail_tgt);'
                if needle not in body:
                    tails = re.findall(r'RECOMP_ITAIL\(0x([0-9A-F]{8})u\)', body)
                    if len(tails) == 1 and int(tails[0], 16) in jumpers:
                        continue  # _longjmpex can be an alias of longjmp.
                    raise ValueError(f'longjmp {addr:08X} has no indirect exit')
                body = body.replace(needle, 'default: RECOMP_LONGJMP_RESUME(_itail_tgt);')
            if resumes or addr in jumpers:
                body = body.replace('{\n', '{\n    ' + MARKER + '\n', 1)
                parts[k] = body
                changed.append(f'{addr:08X}')
        new = ''.join(parts)
        if new != old:
            # Use the runtime include path, also when lift_module uses --out.
            new = new.replace('#include "recomp_types.h"', '#include "recomp_types.h"\n#include "nonlocal_jumps.h"', 1)
            path.write_text(new, encoding='utf-8', newline='\n')
    return changed
