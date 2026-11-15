"""The packed-integer SSE2 forms pcrecomp's lift32_sse leaves UNIMPLEMENTED.

This extension adds lane arithmetic, unpacks and saturating packs, then
hands other instructions to lift32_sse.lift_sse. Install lift_sse_ra3 in
place of lift32.lift_sse before translating locally supplied inputs.

Every form reads both operands into temporaries before writing: the source
may be the destination register (`paddw xmm1, xmm1`). Semantics follow the
Intel SDM; signed lanes are read through casts since xmm_t has no i8 view.
"""
from __future__ import annotations

from capstone.x86 import X86_OP_IMM

import lift32_sse
from lift32_sse import _xi

_lift_sse = lift32_sse.lift_sse

# name -> (lanes, C type of a lane read, expression of a and b, store type)
# Plain lane arithmetic, wrapping.
_WRAP = {
    "paddb": (16, "u8", "uint8_t", "{a} + {b}"),
    "paddw": (8, "u16", "uint16_t", "{a} + {b}"),
    "psubb": (16, "u8", "uint8_t", "{a} - {b}"),
    "psubw": (8, "u16", "uint16_t", "{a} - {b}"),
    "pmullw": (8, "i16", "uint16_t", "(int32_t){a} * (int32_t){b}"),
    "pmulhw": (8, "i16", "uint16_t", "((int32_t){a} * (int32_t){b}) >> 16"),
    "pmulhuw": (8, "u16", "uint16_t", "((uint32_t){a} * (uint32_t){b}) >> 16"),
    "pavgb": (16, "u8", "uint8_t", "((uint32_t){a} + (uint32_t){b} + 1) >> 1"),
    "pavgw": (8, "u16", "uint16_t", "((uint32_t){a} + (uint32_t){b} + 1) >> 1"),
    "pmaxub": (16, "u8", "uint8_t", "{a} > {b} ? {a} : {b}"),
    "pminub": (16, "u8", "uint8_t", "{a} < {b} ? {a} : {b}"),
}
# Saturating lane arithmetic: (lanes, view, signed?, bits, op).
_SAT = {
    "paddsb": (16, "u8", 1, 8, "+"), "paddsw": (8, "i16", 1, 16, "+"),
    "psubsb": (16, "u8", 1, 8, "-"), "psubsw": (8, "i16", 1, 16, "-"),
    "paddusb": (16, "u8", 0, 8, "+"), "paddusw": (8, "u16", 0, 16, "+"),
    "psubusb": (16, "u8", 0, 8, "-"), "psubusw": (8, "u16", 0, 16, "-"),
}
# Interleaves: (view, lanes per half, high half?).
_UNPACK = {
    "punpcklbw": ("u8", 8, 0), "punpckhbw": ("u8", 8, 1),
    "punpcklwd": ("u16", 4, 0), "punpckhwd": ("u16", 4, 1),
    "punpckldq": ("u32", 2, 0), "punpckhdq": ("u32", 2, 1),
}
# Narrowing packs: (source view, lanes per operand, dest view, lo, hi).
_PACK = {
    "packsswb": ("i16", 8, "u8", -128, 127),
    "packuswb": ("i16", 8, "u8", 0, 255),
    "packssdw": ("i32", 4, "u16", -32768, 32767),
}


def _lane(view: str, src: str) -> str:
    """A signed byte lane has no xmm_t view: read it through a cast."""
    return f"(int8_t){src}.u8[_k]" if view == "i8" else f"{src}.{view}[_k]"


def lift_sse_ra3(L, m, ops, comment):
    # A spin-wait hint. The loop around it already gives the machine lock
    # away now and then (RECOMP_BACKEDGE), which is what lets the thread it
    # waits on run; the hint itself does nothing.
    if m == "pause":
        return [f"/* pause */ {comment}"]
    if len(ops) < 2 or _xi(ops[0]) is None:
        return _lift_sse(L, m, ops, comment)
    di, s = _xi(ops[0]), ops[1]
    si = _xi(s)
    src = f"_xmm[{si}]" if si is not None else f"xmm_ld({L._fmt_mem_addr(s.mem)})"
    head = f"{{ xmm_t _s = {src}, _d = _xmm[{di}];"

    def one(body):
        return [f"{head} {body} }} {comment}"]

    if m in _WRAP:
        n, view, store, expr = _WRAP[m]
        a, b = f"_d.{view}[_k]", f"_s.{view}[_k]"
        target = "u8" if view == "u8" else "u16"
        return one(f"for (int _k = 0; _k < {n}; _k++) _xmm[{di}].{target}[_k] = ({store})({expr.format(a=a, b=b)});")
    if m in _SAT:
        n, view, signed, bits, op = _SAT[m]
        lo, hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)
        rd = (lambda x: f"(int32_t)(int8_t){x}.u8[_k]") if (signed and bits == 8) else (lambda x: f"(int32_t){x}.{view}[_k]")
        target = "u8" if bits == 8 else "u16"
        return one(f"for (int _k = 0; _k < {n}; _k++) {{ int32_t _v = {rd('_d')} {op} {rd('_s')}; "
                   f"_xmm[{di}].{target}[_k] = (uint{bits}_t)(_v < {lo} ? {lo} : _v > {hi} ? {hi} : _v); }}")
    if m in _UNPACK:
        view, n, high = _UNPACK[m]
        off = n if high else 0
        return one(f"for (int _k = 0; _k < {n}; _k++) {{ _xmm[{di}].{view}[2 * _k] = _d.{view}[_k + {off}]; "
                   f"_xmm[{di}].{view}[2 * _k + 1] = _s.{view}[_k + {off}]; }}")
    if m in _PACK:
        view, n, dview, lo, hi = _PACK[m]
        dt = "uint8_t" if dview == "u8" else "uint16_t"
        sat = f"(_v < {lo} ? {lo} : _v > {hi} ? {hi} : _v)"
        return one(f"for (int _k = 0; _k < {n}; _k++) {{ int32_t _v = _d.{view}[_k]; _xmm[{di}].{dview}[_k] = ({dt}){sat}; "
                   f"_v = _s.{view}[_k]; _xmm[{di}].{dview}[_k + {n}] = ({dt}){sat}; }}")
    if m == "pmaddwd":
        return one("for (int _k = 0; _k < 4; _k++) _xmm[%d].i32[_k] = (int32_t)((int32_t)_d.i16[2 * _k] * _s.i16[2 * _k] "
                   "+ (int32_t)_d.i16[2 * _k + 1] * _s.i16[2 * _k + 1]);" % di)
    if m == "pmuludq":
        return one("_xmm[%d].u64[0] = (uint64_t)_d.u32[0] * _s.u32[0]; "
                   "_xmm[%d].u64[1] = (uint64_t)_d.u32[2] * _s.u32[2];" % (di, di))
    if m == "psadbw":
        return one("for (int _h = 0; _h < 2; _h++) { uint32_t _t = 0; for (int _k = 0; _k < 8; _k++) { "
                   "int _x = (int)_d.u8[8 * _h + _k] - (int)_s.u8[8 * _h + _k]; _t += _x < 0 ? -_x : _x; } "
                   "_xmm[%d].u64[_h] = _t; }" % di)
    if m in ("pshuflw", "pshufhw") and len(ops) == 3 and ops[2].type == X86_OP_IMM:
        imm, base = ops[2].imm, 0 if m == "pshuflw" else 4
        sel = "; ".join(f"_xmm[{di}].u16[{base + k}] = _s.u16[{base + ((imm >> (2 * k)) & 3)}]" for k in range(4))
        keep = 4 - base
        return one(f"{sel}; _xmm[{di}].u64[{keep // 4}] = _s.u64[{keep // 4}];")
    return _lift_sse(L, m, ops, comment)
