"""Utility helpers shared across the Differ 2 plugin modules.

This module exists so that `differ_native.py` and `differ_python.py` can
import common helpers at the top of the file (no lazy imports, no
circular-dependency workarounds). `__init__.py` imports these too via
`from .utils import split_lines_safe, ScrollSplittedTab`.
"""

import json
import os
import re
import typing as tp

import cudatext as ct


# Pattern that matches a single line terminator (CRLF, lone CR, or lone LF).
# CRLF is listed FIRST so regex alternation tries the two-byte sequence
# before the lone \r — otherwise \r\n would be split as two boundaries
# (a spurious empty string between \r and \n). See split_lines_safe's
# docstring for the full rationale.
_LINE_SPLIT_RE = re.compile(r'\r\n|\r|\n')

# The exotic line boundaries str.splitlines() ALSO splits on, but
# CudaText (and this plugin) must NOT: VT, FF, FS, GS, RS, NEL, LS, PS.
# Their absence is the guard for split_lines_safe's splitlines() fast
# path — with none of them present, splitlines(True) splits on exactly
# \n / \r\n / \r and nothing else, which is precisely this module's
# contract. Kept as a tuple of 1-char strings so the `c in text` guard
# runs as 8 memchr-class scans with early break.
_EXOTIC_BOUNDARY_CHARS = (
    '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85',
    '\u2028', '\u2029',
)


def split_lines_safe(text: str) -> tp.List[str]:
    """Split text into lines on \\n, \\r\\n, or \\r ONLY.

    Drop-in replacement for text.splitlines(True) that does NOT treat
    VT, FF, NEL, LS, PS...etc as line boundaries (see comment above _LINE_SPLIT_RE).
    Keepends behavior is preserved: each returned line includes its
    original terminator, matching what splitlines(True) callers expect.
    A trailing terminator-less remainder (if the text doesn't end in a
    line ending) is included as the final element with no terminator,
    same as splitlines(True). Empty input returns [].

    Details:
    splitlines splits on the following 11 line boundaries: https://docs.python.org/3/library/stdtypes.html#str.splitlines
    - \\n Line Feed
    - \\r Carriage Return
    - \\r\\n Carriage Return + Line Feed
    - \\v or \\x0b Line Tabulation (Vertical Tab (VT))
    - \\f or \\x0c Form Feed (Page Break)
    - \\x1c File Separator (FS, \\u001C)
    - \\x1d Group Separator (GS, \\u001D):
    - \\x1e Record Separator (RS, \\u001E)
    - \\x85 Next Line (C1 Control Code, NEL, \\u0085)
    - \\u2028 Line Separator (LS)
    - \\u2029 Paragraph Separator (PS)

    This functions splits *text* into a list of lines, keeping each line's terminator
    appended (matching str.splitlines(True)'s keepends=True contract),
    but splitting ONLY on \\r\\n, \\r, \\n -- NOT on NEL/VT/FF/LS/PS...etc.
    This matches how CudaText stores lines internally: a line containing
    an embedded NEL/VT/FF/LS/PS...etc is a single logical line, not two.
    A trailing empty element (after a final terminator) is dropped, so
    "abc\\n" -> ["abc\\n"] -- same as str.splitlines(True).

    CudaText's editor only treats CR, LF, and CRLF as line breaks; the other
    characters stay inside a single logical line and are rendered as
    in-line control pictures. Using str.splitlines() UNCONDITIONALLY here
    would split on those extra characters too, producing more "lines" than
    the editor actually has, which causes every diff event line index to
    drift out of sync with the editor (see refresh_compare). That is why
    the splitlines() fast path below is guarded by an explicit absence
    check of the 8 exotic boundary chars: with none of them present,
    splitlines(True) and this contract coincide EXACTLY (verified by
    randomized equivalence tests against the regex walk below).

    Why the fallback uses re.finditer and not str.split(): split() can't
    do this job at all, for one structural reason -- it discards the
    delimiter. "a\\r\\nb".split('\\r\\n') gives you ['a', 'b'] with the
    \\r\\n gone. But set_seqs/unidiff call this with keepends=True
    semantics -- every line needs its original terminator still attached,
    because the diff engine uses that terminator when
    reconstructing/rendering output. So whatever splits also has to
    capture what it split on.
    Three ways to get delimiter-preserving split, ranked:
    1. re.split() with a capturing group — re.split(r'(\\r\\n|\\r|\\n)', text) returns alternating content/delimiter pieces you'd then have to re-zip back together in a loop. Works, but it's an extra reconstruction pass for no benefit over option 2.
    2. finditer (what I used) — one pass, and at each match I already have m.end(), so I slice text[pos:m.end()] directly — content and its trailing terminator in one slice, no reassembly step. This is what I wrote.
    3. Manual two-pointer scan (no regex) — check each position for \\r, \\n, or \\r\\n by hand, same asymptotic cost, more code, easier to get the "is this \\r followed by \\n" lookahead wrong. Not worth it here.
    There's a subtlety str.split() would also get wrong even ignoring the discard problem: splitting on \\r and \\n as separate single-char delimiters (e.g. chaining two .split() calls, or re.split(r'[\\r\\n]')) treats \\r\\n as two boundaries, producing a spurious empty string between them. My pattern lists r'\\r\\n|\\r|\\n' with \\r\\n first, so regex alternation matches the two-char sequence before it'd consider the lone \\r — that ordering is why CRLF collapses to one boundary instead of two. If I'd written r'\\r|\\n|\\r\\n' instead, alternation still tries left-to-right per position, so \\r would win before \\r\\n got a chance and you'd get the same double-split bug. It's already correctly ordered in the delivered code, but worth knowing why the ordering matters if you ever touch that pattern.

    and finditer is faster than re.split() in my tests
    """
    if not text:
        return []
    # Fast path 0 (the overwhelmingly common case): when the text has NO
    # exotic line-boundary characters, str.splitlines(True) is EXACTLY
    # this function's contract -- it splits on \n, \r\n and lone \r
    # (keeping terminators, matching CudaText's line model) and leaves
    # VT/FF/FS/GS/RS/NEL/LS/PS inside single lines. splitlines is one C
    # pass; the guard is 8 memchr scans (~18ms per 50MB, with early
    # break). Measured on a 1M-line / 63MB LF text: ~0.11s vs ~0.83s
    # for the regex walk below (and CRLF texts ~0.10s vs ~0.64s -- both
    # endings now take the fast path). Only texts that actually contain
    # an exotic boundary char pay the precise regex walk.
    if not any(c in text for c in _EXOTIC_BOUNDARY_CHARS):
        return text.splitlines(True)

    # ---- fast path 1: pure-LF text (no CR at all) ----
    # str.split's last element is '' iff the text ends with the
    # separator: that phantom is the "nothing after the final
    # terminator", not a line -- drop it, then re-attach the terminator
    # every remaining piece DID have. Byte-identical to the regex walk
    # below for every CR-free input (test_split_lines_fast.py).
    if '\r' not in text:
        parts = text.split('\n')
        if parts[-1] == '':
            parts.pop()
            return [p + '\n' for p in parts]
        # no trailing terminator: every piece but the last owns one
        if len(parts) == 1:
            return [text]
        return [p + '\n' for p in parts[:-1]] + [parts[-1]]

    # ---- fast path 2: CRLF-only text ----
    # Safe only when NO lone CR and NO lone LF exists (every '\r' starts
    # a '\r\n' and every '\n' ends one): splitting on '\r\n' then finds
    # exactly the terminator boundaries. Three C-speed count() scans
    # decide; mixed-terminator texts fall through to the regex walk.
    n_cr = text.count('\r')
    if n_cr:
        n_lf = text.count('\n')
        if n_cr == n_lf and n_cr == text.count('\r\n'):
            parts = text.split('\r\n')
            if parts[-1] == '':
                parts.pop()
                return [p + '\r\n' for p in parts]
            if len(parts) == 1:
                return [text]
            return [p + '\r\n' for p in parts[:-1]] + [parts[-1]]

    # ---- general path: mixed terminators, regex walk ----
    lines = []
    pos = 0
    for m in _LINE_SPLIT_RE.finditer(text):
        lines.append(text[pos:m.end()])
        pos = m.end()
    if pos < len(text):
        lines.append(text[pos:])
    return lines


class ScrollSplittedTab:
    """Manages synchronized scrolling for split compare tabs.

    How the timing works (and why this code is shaped the way it is):

    CudaText fires the on_scroll event AFTER the scrolled editor has
    painted (ATSynEdit: Paint -> PaintEx -> DoEventScroll), and program-
    atic scroll changes fire it too (the SmoothPos-change detection runs
    at paint time). So a naive "on event, copy the position to the other
    half" implementation always lags one paint behind AND echoes: the
    mirrored write makes the other half fire on_scroll back at the plugin,
    which (without guards) does a redundant set_prop plus an unconditional
    cmd_RepaintEditor on the already-painted half -- an extra full repaint
    per scroll step that visibly delays the following sync updates on big
    compare files.

    This implementation keeps the two halves lock-step by:

    - copying 'smooth_pos' (per-pixel float position) from the scrolled
      half to the other half inside the event -- the mirrored half's
      repaint then happens in the same message-loop batch, right after
      the scrolled half's paint, so both move in the same display frame;
    - skipping the write entirely when the other half already sits at the
      same position: no position change means no repaint, no echo event,
      and the whole cascade dies out instead of ping-ponging;
    - a re-entrancy guard (like the official cuda_sync_scroll plugin) so
      a synchronously re-entered event can never recurse;
    - the end-of-scroll guard from cuda_sync_scroll: when the scrolled
      half is at its last position, the write is skipped -- workaround
      for a CudaText bug with scrolling at the end of non-equal-height
      files (possible here when word-wrap makes the halves differ in
      visual height).

    NOTE: this class is now purely the MIRROR engine -- it owns no
    subscription state anymore. The on_scroll event itself is managed
    by events_sub.py (subscribed while compare tabs exist and
    sync_scroll / enable_overview needs it), and Command.on_scroll
    decides per event whether the mirror runs at all (it is gated on
    the sync_scroll setting there). The old tab_id set + toggle()
    method -- a parallel bookkeeping of "which tabs need on_scroll"
    that could only be kept correct by hand at every call site -- is
    gone: Command._sessions is the single truth, and the bus reads it.

    WHY THE MIRRORED HALF USES EDACTION_UPDATE (synchronous Repaint)
    AND NOT cmd_RepaintEditor (forced Invalidate):

    Users could see the initiating half scroll first and the mirrored
    half catch up a few milliseconds later whenever the RIGHT half (or
    the overview) initiated. cmd_RepaintEditor maps to Ed.Update(false,
    true, false), which is only a FORCED INVALIDATE -- the paint is
    still delivered asynchronously through the message queue, where it
    competes with pending input messages (a scrollbar / overview drag
    floods the queue with mouse moves, and Windows delivers WM_PAINT
    only when the queue is otherwise empty) and can land in the NEXT
    display frame. ed.action(EDACTION_UPDATE) maps to Ed.Repaint --
    Invalidate + LCL Update, i.e. the mirrored half paints
    SYNCHRONOUSLY, right here inside the event callback, so both halves
    are on screen in the same frame no matter which half initiated or
    how busy the message queue is. The synchronous paint of the
    mirrored half fires its own on_scroll echo; the _busy guard below
    drops it, and by then the positions are equal anyway (no write, no
    cascade).
    """

    def __init__(self):
        # Re-entrancy guard: True while an on_scroll handler is mirroring
        # a position, so a nested (synchronous) on_scroll for the opposite
        # half cannot start a second mirror pass. EDACTION_UPDATE's
        # synchronous repaint makes this nesting actually happen now.
        self._busy = False

    def on_scroll(self, ed_self):
        """Mirror the scroll position of ed_self to the opposite half of
        the split tab. Called from __init__.py's on_scroll only for compare
        tabs (already _is_compare_tab-filtered)."""
        if ed_self.get_prop(ct.PROP_SPLIT)[0] == '-':
            return
        if self._busy:
            return
        self._busy = True
        try:
            self._mirror_scroll(ed_self)
        finally:
            self._busy = False

    def _mirror_scroll(self, ed_self):
        info_v = ed_self.get_prop(ct.PROP_SCROLL_VERT_INFO)
        info_h = ed_self.get_prop(ct.PROP_SCROLL_HORZ_INFO)
        pos_v = info_v['smooth_pos']
        pos_h = info_h['smooth_pos']

        hndl_self = ed_self.get_prop(ct.PROP_HANDLE_SELF)
        hndl_primary = ed_self.get_prop(ct.PROP_HANDLE_PRIMARY)
        hndl_secondary = ed_self.get_prop(ct.PROP_HANDLE_SECONDARY)
        if hndl_self == hndl_primary:
            hndl_opposit = hndl_secondary
        else:
            hndl_opposit = hndl_primary
        e = ct.Editor(hndl_opposit)

        info2_v = e.get_prop(ct.PROP_SCROLL_VERT_INFO)
        info2_h = e.get_prop(ct.PROP_SCROLL_HORZ_INFO)

        # End-of-scroll guard (from the official cuda_sync_scroll plugin):
        # skip the write when the scrolled half is at its last position --
        # CudaText misbehaves when scrolling at the end of files whose
        # halves differ in height (word-wrap can do that here).
        # Missing 'smooth_pos_last' (older API) just disables the guard.
        max_v = info_v.get('smooth_pos_last')
        max2_v = info2_v.get('smooth_pos_last')
        max_h = info_h.get('smooth_pos_last')
        max2_h = info2_h.get('smooth_pos_last')

        changed = False

        # Vertical: write only when the position actually differs -- a
        # redundant write would still cost a Python->C call and a
        # scrollbars update, and would keep the echo cascade alive.
        if pos_v != info2_v['smooth_pos']:
            if (max_v is None or pos_v < max_v) and \
               (max2_v is None or pos_v < max2_v):
                e.set_prop(ct.PROP_SCROLL_VERT_INFO, {'smooth_pos': pos_v})
                changed = True

        # Horizontal: same treatment.
        if pos_h != info2_h['smooth_pos']:
            if (max_h is None or pos_h < max_h) and \
               (max2_h is None or pos_h < max2_h):
                e.set_prop(ct.PROP_SCROLL_HORZ_INFO, {'smooth_pos': pos_h})
                changed = True

        # Paint the mirrored half ONLY when its position really changed,
        # and paint it SYNCHRONOUSLY (EDACTION_UPDATE = Ed.Repaint =
        # Invalidate + Update; see the class docstring for why the async
        # forced invalidate of cmd_RepaintEditor left a visible
        # few-millisecond drift when the right half / overview initiated).
        # The scrolled half has already painted (the event is post-paint),
        # so repainting it again would only burn time; and when nothing
        # changed there is nothing to show at all.
        if changed:
            e.action(ct.EDACTION_UPDATE)


# ==========================================================================
# Shared STATE-file healer (used by the _get_state/_set_state wrappers of
# BOTH state writers: __init__.py's compare-tab tracking and compare_dir
# .py's folder-compare state -- the file settings/cuda_differ2_state.json
# they share).
#
# WHY THIS EXISTS -- cudax_lib's set_opt has TWO write shapes for a JSON
# file, and for dict/list values they are NOT format-compatible:
#
#   * CREATE branch (the file does not exist yet): the whole file is
#     written with json.dumps(kv_dct, indent=2) -- the first key's value
#     comes out PRETTY-PRINTED, spanning MANY lines.
#
#   * UPDATE / ADD branches (the file exists): strictly LINE-BASED --
#     the code's own comment says "one key:val into one row". An UPDATE
#     replaces ONLY the key's first line with a compact one-line value;
#     an ADD appends one compact line before the closing brace.
#
# So the SECOND write to a freshly created state file replaces the first
# line of the pretty multi-line value and leaves the remaining lines of
# the old value in the file as an orphaned tail -> invalid JSON, and
# every later read of the file fails (CudaText's tolerant reader logs
# "error on loading json" into cudax.log). On a fresh plugin install the
# first write is the very first compare-tab registration, and the second
# write can be any later state change: the dirty-flag update of the
# first keystroke typed into a diff half, the registration of a second
# diff tab, the unregister of a closed tab, a folder-compare state
# write... (Repro: fresh install -> compare two files -> type in one
# half, don't save -> restart CudaText -> the json error.)
#
# The plugin cannot fix cudax_lib (it ships with the app), so every
# read/write of the shared state file goes through this healer first.
# It guarantees the file is in the ONE shape every cudax_lib write
# expects -- one key per line, compact value, parseable -- and repairs
# files the bug above (or older plugin releases, or a hand edit) left
# in a bad shape:
#
#   * missing file    -> pre-created as '{}' (so cudax_lib's pretty
#                        CREATE branch can never run on it again; every
#                        later write goes through the line-based ADD /
#                        UPDATE branches, which keep each key on ONE
#                        compact line forever);
#   * blank file      -> healed to '{}' (the 28th-release heal, now
#                        shared by both writers);
#   * unparseable file -> the complete one-line '"differ2.*": <value>'
#                        pairs are salvaged (they are exactly the lines
#                        cudax_lib's line-based writes leave behind, so
#                        they carry the authoritative last-written
#                        values), the original is backed up beside it
#                        as <name>.corrupt.bak and the file is rebuilt
#                        from them;
#   * parseable file whose 'differ2.*' values span multiple lines
#     (legacy whole-file writers, hand edits) -> each such value is
#     compacted onto its key's line in place; every other line --
#     including hand-made // comments -- is preserved byte-for-byte.
#
# heal_state_file() returns a short human-readable note when the file
# was changed ('' when it was already healthy) so the callers can log
# it; it never raises (a settings dir the user cannot write to must
# not break the plugin) and never touches keys outside the plugin's
# own 'differ2.*' namespace.
# ==========================================================================

# One '"differ2.<name>": <rest>' line. Mirrors the LINE ANCHORING of
# cudax_lib's own update regex ('^\s*,?\s*"<key>"\s*:(.+)'): a key line
# this pattern cannot find is a key line cudax_lib's UPDATE branch
# cannot find either -- that write then takes its harmless append-only
# ADD branch instead, so the shapes this regex skips are exactly the
# shapes that are safe to skip.
_KEY_LINE_RE = re.compile(
    r'^(\s*),?\s*"(?P<key>differ2\.[^"]+)"\s*:\s*(?P<rest>.*)$')


def _strip_json_comment(match):
    """re.sub callback: cut one line at the first '//' that is outside
    a JSON string (same string-aware scan cudax_lib's _json_loads
    uses, so the healer judges parseability exactly like the reader
    that will consume the file)."""
    line = match.group(0)
    pos = 0
    in_str = False
    while pos < len(line):
        ch = line[pos]
        if ch == '\\':
            pos += 2
        else:
            if ch == '"':
                in_str = not in_str
            elif line[pos:pos + 2] == '//' and not in_str:
                return line[:pos]
            pos += 1
    return line


def tolerant_json_loads(text):
    """json.loads with cudax_lib's tolerance: '//' comments stripped and
    stray commas around '{', '}', '[', ']' removed. SILENT -- returns
    None on failure (cudax_lib's own _json_loads logs an error line and
    writes it to cudax.log, which the healer's probe must not spam:
    probing happens before every state read/write)."""
    s = re.sub(r'^.*//.*$', _strip_json_comment, text, flags=re.MULTILINE)
    s = re.sub(r'{\s*,', '{', s)
    s = re.sub(r',\s*}', '}', s)
    s = re.sub(r'\[\s*,', '[', s)
    s = re.sub(r',\s*\]', ']', s)
    try:
        return json.loads(s)
    except Exception:
        return None


def _scan_value_end(lines, li, ci):
    """lines[li][ci] is the opening '{' or '[' of a JSON value (outside
    any string). Return (end_li, end_ci) pointing just past the matching
    close, or (None, None) when the value never closes. String- and
    '//' comment-aware: pretty values may carry hand-made comments, and
    a brace inside a comment or a string literal would break a naive
    depth counter."""
    depth = 0
    in_str = False
    esc = False
    for i in range(li, len(lines)):
        line = lines[i]
        j = ci if i == li else 0
        while j < len(line):
            ch = line[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == '/' and line[j:j + 2] == '//':
                break               # comment: rest of the line is not JSON
            elif ch in '{[':
                depth += 1
            elif ch in '}]':
                depth -= 1
                if depth == 0:
                    return i, j + 1
            j += 1
    return None, None


def heal_state_file(path):
    """Make the shared plugin STATE file safe for cudax_lib's
    line-based set_opt BEFORE any read or write reaches it (see the
    block comment above for the full rationale and the four heal
    cases). 'path' is the absolute path of the file. Returns a short
    note when the file was changed, '' when it was already healthy;
    never raises."""
    try:
        with open(path, 'r', encoding='utf8') as f:
            text = f.read()
    except FileNotFoundError:
        # Missing: pre-create it as '{}' OURSELVES. cudax_lib's set_opt
        # would create it pretty-printed (indent=2), which is the first
        # half of the corruption; an existing (even empty) file makes
        # every later write take the line-based ADD / UPDATE branches,
        # which are the safe shape.
        try:
            with open(path, 'w', encoding='utf8') as f:
                f.write('{}\n')
            return 'state file was missing: created empty'
        except OSError:
            return ''
    except (OSError, UnicodeDecodeError):
        return ''                   # unreadable for reasons we can't fix

    if not text.strip():
        # Blank (a crash between a writer's open('w') and its write --
        # the 28th-release case, kept): cudax_lib's ADD branch dies on
        # an empty body, so heal it to '{}'.
        try:
            with open(path, 'w', encoding='utf8') as f:
                f.write('{}\n')
            return 'blank state file healed to {}'
        except OSError:
            return ''

    if tolerant_json_loads(text) is None:
        return _salvage_state_file(path, text)
    return _compact_multiline_values(path, text)


def _compact_multiline_values(path, text):
    """The file parses, but a 'differ2.*' value may still span several
    lines (a legacy whole-file writer or a hand edit): cudax_lib's next
    UPDATE of that key would replace only its first line and orphan the
    rest -- the very corruption above. Fold every such value onto its
    key's line; every other line, including hand-made // comments, is
    preserved byte-for-byte."""
    lines = text.splitlines(True)   # keepends: untouched lines pass through
    out = []
    folded = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        core = line.rstrip('\r\n')
        ending = line[len(core):]
        m = _KEY_LINE_RE.match(core)
        fold_col = None
        if m:
            # Is this key's value COMPLETE on this line? (A scalar, or a
            # balanced {..}/[..] pair -- the one-line shape cudax_lib
            # updates safely.) If not, but it OPENS a {/[, the value
            # continues on the following lines -- fold it.
            rest = m.group('rest').strip()
            if rest.endswith(','):
                rest = rest[:-1].rstrip()
            if rest[:1] in ('{', '[') and tolerant_json_loads(rest) is None:
                fold_col = core.find(rest[0], m.start('rest'))
        if fold_col is not None:
            # Multi-line differ2.* value: find its end (from the opener
            # column), parse it, write the compact form on ONE line.
            end_i, end_c = _scan_value_end(lines, i, fold_col)
            ok = end_i is not None
            if ok:
                span = (lines[i][fold_col:]
                        + ''.join(lines[i + 1:end_i])
                        + lines[end_i][:end_c])
                val = tolerant_json_loads(span)
                ok = val is not None
            if not ok:
                # Cannot isolate the value safely: leave the file alone
                # (a half-rewrite could do more harm than the hazard).
                return ''
            new_line = '%s"%s": %s' % (m.group(1), m.group('key'),
                                       json.dumps(val))
            after = lines[end_i][end_c:]
            if after.strip().startswith(','):
                # More pairs follow the close on the same line: glue
                # them after the compact value (their comma is 'after').
                out.append(new_line + after)
            else:
                # Clean line end (or a trailing // comment): end the
                # folded pair with a comma, keep any trailing text.
                out.append(new_line + ',' + (after or '\n'))
            folded += 1
            i = end_i + 1
            continue
        out.append(line)
        i += 1
    if not folded:
        return ''
    new_text = ''.join(out)
    if tolerant_json_loads(new_text) is None:
        return ''                   # safety net; must not happen
    try:
        with open(path, 'w', encoding='utf8') as f:
            f.write(new_text)
    except OSError:
        return ''
    return ('state file normalized: %d multi-line value(s) folded '
            'onto their key lines' % folded)


def _salvage_state_file(path, text):
    """The file does not parse (the orphaned-tail corruption above, or a
    hand-mangled file). Recover what is recoverable -- every COMPLETE
    one-line '\"differ2.*\": <value>' pair (exactly the lines cudax_lib's
    line-based writes leave behind, so they carry the authoritative
    last-written values; the multi-line remainders of an orphaned tail
    never form one) -- back the original up as <name>.corrupt.bak and
    rebuild the file from the survivors."""
    pairs = {}                      # key -> value text, last write wins
    order = []                      # first-seen key order
    for line in text.splitlines():
        m = _KEY_LINE_RE.match(line.rstrip('\r\n'))
        if not m:
            continue
        val_text = m.group('rest').strip()
        if val_text.endswith(','):
            val_text = val_text[:-1].rstrip()
        if tolerant_json_loads(val_text) is None:
            continue                # not a complete one-line value
        if m.group('key') not in pairs:
            order.append(m.group('key'))
        pairs[m.group('key')] = val_text
    bak = path + '.corrupt.bak'
    try:
        with open(bak, 'w', encoding='utf8') as f:
            f.write(text)
    except OSError:
        return ''                   # cannot back up: do not risk a rewrite
    try:
        with open(path, 'w', encoding='utf8') as f:
            if pairs:
                f.write('{\n' + ''.join(
                    '  "%s": %s,\n' % (k, pairs[k]) for k in order) + '}\n')
                note = ('state file was corrupt: repaired from the last '
                        'written %d key(s), original backed up as %s'
                        % (len(order), os.path.basename(bak)))
            else:
                f.write('{}\n')
                note = ('state file was corrupt and unrecoverable: '
                        'reset to {}, original backed up as %s'
                        % os.path.basename(bak))
    except OSError:
        return ''
    return note

