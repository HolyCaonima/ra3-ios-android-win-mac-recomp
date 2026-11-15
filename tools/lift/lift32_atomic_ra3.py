"""Locked x86 read-modify-writes as real atomics.

pcrecomp's lift32 lifts `lock xadd`, `lock cmpxchg`, `xchg [mem]` and
`lock add/or/inc/...` as plain read-then-write: correct only while one thread
at a time runs lifted code (native32's machine lock). With real threads they
must be atomic on guest memory, or reference counts and spin locks break.

install() wraps Lifter._lift_instruction. For a memory destination:

* xadd / xchg / cmpxchg / cmpxchg8b call recomp_xadd/xchg/cas (runtime/
  recomp32/recomp_types.h), computing the flags lift32 would from the value the
  atomic returned.
* any other `lock` instruction (add sub and or xor adc sbb inc dec neg not
  bts btr btc) whose only register output is the flags: lift32's own lines run
  on a local copy of the operand inside a compare-and-swap loop, retried until
  no other thread wrote the location in between.

xchg with memory is locked on x86 even without the prefix; xadd and cmpxchg
are made atomic with or without it (MSVC never emits them unlocked on shared
data). This does not establish full x86 memory ordering on ARM64.
"""
from __future__ import annotations

from capstone.x86 import X86_OP_MEM, X86_OP_REG

import lift32
from lift32 import Lifter, op_bits

_LOCK = 0xF0
_RMW = {'add', 'sub', 'and', 'or', 'xor', 'adc', 'sbb', 'inc', 'dec', 'neg', 'not',
        'bts', 'btr', 'btc'}
_CTYPE = {8: 'uint8_t', 16: 'uint16_t', 32: 'uint32_t', 64: 'uint64_t'}

stats = {'xadd': 0, 'xchg': 0, 'cmpxchg': 0, 'cmpxchg8b': 0, 'rmw': 0, 'unhandled': 0}


def _has_lock(insn) -> bool:
    for b in bytes(insn.bytes):
        if b == _LOCK:
            return True
        if b not in (0xF2, 0xF3, 0x66, 0x67, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65):
            return False
    return False


def _mnemonic(insn) -> str:
    m = insn.mnemonic
    if m.startswith('lock'):
        m = m[4:].strip() or (insn.op_str.split() or [''])[0]
    return m


def _lift_atomic(self: Lifter, insn):
    self._patched_imm = self._patched_disp = None   # lift32 resets them per instruction
    m = _mnemonic(insn)
    ops = list(insn.operands or [])
    if not ops or ops[0].type != X86_OP_MEM:
        if m == 'xchg' and len(ops) == 2 and ops[1].type == X86_OP_MEM:
            ops = [ops[1], ops[0]]          # xchg reg, [mem]: same thing
        else:
            return None
    locked = _has_lock(insn)
    if m not in ('xadd', 'xchg', 'cmpxchg', 'cmpxchg8b') and not (locked and m in _RMW):
        if locked:
            stats['unhandled'] += 1
            raise NotImplementedError(f"0x{insn.address:08X}: lock {m} not made atomic")
        return None

    comment = f"/* 0x{insn.address:08X}: {insn.mnemonic} {insn.op_str} [atomic] */"
    mem = ops[0]
    bits = op_bits(mem)
    addr = self._fmt_mem_addr(mem.mem)
    lines = []

    if m == 'xadd':
        t = _CTYPE[bits]
        b = self._fmt_read(ops[1])
        lines.append(f"{{ uint32_t _va = {addr}; uint32_t _b = ({t})({b}); "
                     f"uint32_t _old = recomp_xadd{bits}(_va, ({t})_b); {comment}")
        lines.append(self._flag_capture('_old', '_b', bits))
        lines.append("_cf = (uint32_t)((uint32_t)(_flag_a + _flag_b) < (uint32_t)_flag_a);")
        lines.append(f"  {self._fmt_write(ops[1], '_old')}; }}")
        self._flag_state = ('add', "_flag_a, _flag_b")
        stats['xadd'] += 1
        return lines

    if m == 'xchg':
        t = _CTYPE[bits]
        r = self._fmt_read(ops[1])
        lines.append(f"{{ uint32_t _old = recomp_xchg{bits}({addr}, ({t})({r})); "
                     f"{self._fmt_write(ops[1], '_old')}; }} {comment}")
        stats['xchg'] += 1
        return lines

    if m == 'cmpxchg':
        t = _CTYPE[bits]
        acc, acc_w = {32: ('eax', 'eax = _d'), 16: ('LO16(eax)', 'SET_LO16(eax, _d)'),
                      8: ('LO8(eax)', 'SET_LO8(eax, _d)')}[bits]
        src = self._fmt_read(ops[1])
        lines.append(f"{{ uint32_t _e = {acc}, _d = recomp_cas{bits}({addr}, ({t})_e, ({t})({src})); {comment}")
        lines.append(self._flag_capture('_e', '_d', bits))
        lines.append("_cf = (uint32_t)((uint32_t)_flag_a < (uint32_t)_flag_b);")
        lines.append(f"  if (_d != _e) {{ {acc_w}; }} }}")
        self._flag_state = ('cmp', "_flag_a, _flag_b")
        stats['cmpxchg'] += 1
        return lines

    if m == 'cmpxchg8b':
        lines.append(f"{{ uint64_t _e = ((uint64_t)edx << 32) | eax, _q = recomp_cas64({addr}, _e, "
                     f"((uint64_t)ecx << 32) | ebx); uint32_t _zf = _q == _e ? 0x40u : 0; "
                     f"if (!_zf) {{ eax = (uint32_t)_q; edx = (uint32_t)(_q >> 32); }} "
                     f"_flag_a = (recomp_eflags(_flag_k, _flag_a, _flag_b, _cf, _df) & ~0x40u) | _zf; "
                     f"_flag_b = 0; _flag_k = FK_EFLAGS; }} {comment}")
        self._flag_state = None
        stats['cmpxchg8b'] += 1
        return lines

    if m in ('bts', 'btr', 'btc'):
        # A register bit offset addresses a bit string (the dword at
        # ea + 4*(offset >> 5), signed), as in lift32; flags as lift32's bt.
        if ops[1].type == X86_OP_REG:
            off = self._fmt_read(ops[1])
            va = f"(({addr}) + (uint32_t)(((int32_t)({off}) >> 5) * 4))"
            idx = f"(({off}) & 31)"
        else:
            va = addr
            idx = f"(({self._fmt_read(ops[1])}) & 31)"
        op = {'bts': '_o | _bit', 'btr': '_o & ~_bit', 'btc': '_o ^ _bit'}[m]
        lines.append(f"{{ uint32_t _va = {va}, _i = {idx}, _bit = 1u << _i, _o; "
                     f"do {{ _o = MEM32(_va); }} while (recomp_cas32(_va, _o, {op}) != _o); {comment}")
        lines.append("  " + self._flag_capture('_o', '_i') + " }")
        self._flag_state = ('bt', "_flag_a, _flag_b")
        stats['rmw'] += 1
        return lines

    # lock <rmw> [mem], src: lift32's lines on a local copy, in a CAS loop.
    t = _CTYPE[bits]
    read = self._fmt_read(mem)
    inner = _ORIG(self, insn)
    body = []
    for ln in inner:
        if read not in ln and 'MEM' in ln:
            raise NotImplementedError(f"0x{insn.address:08X}: lock {m}: unexpected memory access: {ln}")
        body.append(ln.replace(f"{read} = ({t})(", "_m = (").replace(f"{read} = ", "_m = ").replace(read, "_m"))
    lines.append(f"{{ uint32_t _va = {addr}; for (;;) {{ {t} _o = ({t}){read}, _m = _o; {comment}")
    lines.extend("    " + ln for ln in body)
    lines.append(f"    if (recomp_cas{bits}(_va, _o, ({t})_m) == _o) break; }} }}")
    stats['rmw'] += 1
    return lines


_ORIG = Lifter._lift_instruction


def _lift_instruction(self, insn):
    out = _lift_atomic(self, insn)
    return out if out is not None else _ORIG(self, insn)


def install():
    Lifter._lift_instruction = _lift_instruction
