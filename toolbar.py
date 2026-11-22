"""Differ 2 compare-tab toolbar.

A small toolbar docked to the TOP of every compare tab (the editor
parent's top side), built with dlg_proc:

  [(pic) Recompare or (pic) Cancel] | [(pic) Prev][(pic) Next] |
  [(pic) Copy][(pic) Copy] | [(pic) Ignore 2/5][(▾)] [(pic) Preset][(▾)] |
  [(pic) Swap] [(pic) Resize] [(pic) View][(▾)] [(pic) Folders][(▾)]
  [(pic) Config]  ...status label

(the (▾) buttons are the small dropdown-caret companions of the four
menu buttons -- see "PICTURE ICONS" below).

Everything the toolbar does goes through the Command object of
cuda_differ2/__init__.py, which passes itself to every module-level
entry point; this module never imports cuda_differ2's __init__ (that
would be a circular import -- __init__ imports THIS module at load).

Implementation notes:

* EMBEDDING: the toolbar is a borderless dlg_proc form shown non-modal
  and DOCKED into the editor's parent control handle
  (ed.prop(PROP_HANDLE_PARENT)) with DLG_DOCK prop='T' -- the same
  docking mechanism the gap-aware overview panel uses for the right
  side ('R'). PROP_HANDLE_PARENT returns the stable grouping panel
  that parents the two split editors, so the toolbar sits exactly on
  top of the compare view. It is NOT freed when that panel is freed
  at tab close: DLG_DOCK only sets the form's Parent, while its OWNER
  stays CudaText's main form (dlg_proc DLG_CREATE does
  TFormDummy.Create(fmMain)), and LCL's TWinControl.Destroy only
  unparents child controls ("controls are freed by the owner") -- so
  the plugin must free the form itself in on_close (see destroy()).

* BUTTONS are 'button_ex' controls (application-themed, CudaText's own
  button look) in flat mode. Every button carries a PICTURE icon from
  the plugin's own PNG tree icons/toolbar/<set>/<size>/ (see the
  picture-icons section below): kind BTNKIND_TEXT_ICON_HORZ with the
  texts on, BTNKIND_ICON_ONLY with them off; the icon comes from a
  per-form imagelist via button_proc(BTN_SET_IMAGELIST /
  BTN_SET_IMAGEINDEX). Separators are button_ex with kind=
  BTNKIND_SEP_HORZ (a vertical line: the 'HORZ' kind is for controls
  placed in a horizontal row).

* PICTURE ICONS: the old UTF-8 glyph captions (↻ ↑ ↓ → ← ≡ ★ ⇋ ↔ ▦ ⚙
  ◫ ▾) render as tofu boxes on fonts without those code points -- the
  reason this whole tree exists. The PNG files live in
  icons/toolbar/{dark,light}/{16,20,24,28,32}/<name>.png (13 names =
  the 12 buttons + 'cancel' for the Recompare->Cancel swap). The set
  is picked from the LIVE toolbar background (EdTextBg) luminance:
  dark backgrounds get the near-white 'dark' glyphs, light and
  light-grey backgrounds the near-black 'light' glyphs; the pixel size
  is picked from the OS DPI (16px at 100% ... 32px at 200%). The
  options differ2.toolbar.icon_theme / icon_size pin either choice by
  hand ('auto', the default, keeps the automatic pick). apply_theme()
  rebuilds the imagelist when a theme switch moves the background
  across the light/dark midpoint (a pinned set never moves). The
  dropdown caret is NOT baked into the menu buttons' icons -- it is a
  small separate caret button chained to the right of Ignore /
  Preset / View / Folders (icon 'menu', after the text, so the menu
  glyphs themselves stay full-size like every other button; see
  _add_caret_button). When the icon tree is missing or the
  imagelist/button APIs fail, every button falls back to the old
  UTF-8 glyph captions (the _BTNS glyph column) with kind=
  BTNKIND_TEXT_ONLY, so an old build or a pruned install never loses
  the toolbar.

* SIZING: buttons are AUTO-SIZED -- control prop 'autosize' makes
  TATButton compute its width from the caption measured with the REAL
  UI-theme font, DPI-scaled (TATButton.SetAutoSize); with a button
  imagelist attached the ICON's width is counted in as well
  (SetAutoSize: abuTextIconHorz = NText+NGap+NIcon+NGap, abuIconOnly
  = NIcon+NGap), so no text or icon can ever be cut off
  HORIZONTALLY. The KIND is (re)applied before every caption+autosize
  re-set -- the width pass must see the final kind. No widths are
  computed here at all; the w_min constraint only keeps icon-only
  buttons clickable.

  HEIGHT: TATButton.SetAutoSize does NOT size the height -- it centers
  the caption in whatever height the layout gives the control
  ((ClientHeight - TextExtent.cy) div 2) and clips the descenders
  ('g', 'y', 'p'...) when the OS font is a little taller than the
  OS 'button' metrics of PROC_GET_GUI_HEIGHT. So the form's height =
  GUI button height + _TEXT_SLACK extra px (DPI-scaled) + the 1-device-px
  bottom border strip (see below).

* BOTTOM BORDER: the toolbar ends in a full-width 1-device-px line
  separating it from the editor below: a dlg_proc 'panel' control
  of height 1 filled with the theme's SplitMain color (a plain
  TPanel paints a flat solid fill -- the strip IS the line). dlg_proc
  never scales control sizes (scaling is only the explicit DLG_SCALE
  action, which this form never calls), so the strip is exactly one
  device pixel at any DPI; apply_theme() re-feeds the color on every
  UI theme switch. All buttons' a_b anchors reference this strip's
  top ('brd', '[') instead of the form's bottom, so the row sits
  fully above the line.

* POSITIONING: anchors, not coordinates. Every button's LEFT side is
  anchored (a_l) to the RIGHT side (']') of the previous control with
  sp_l spacing, so the whole row re-flows automatically whenever a
  button's width changes (Recompare <-> Cancel swap, Ignore counter,
  show_btn_text toggle). The sp_l gap is roomy between two
  neighboring buttons of one group (_BTN_GAP_INNER, DPI-scaled) and
  tight at the row's start / after a separator (_BTN_GAP); the
  separators' own spacing is unchanged. Tops are anchored to the form
  (a_t), bottoms to the TOP of the bottom-border strip; the status
  label is anchored to the form's right edge (a_r) and vertically
  centered (a_t '-') on the last real button, i.e. on the button
  row's height rather than the (border-including) form height.
  'x'/'w' are never set.

* The status LABEL on the right side carries the compare state
  ("Comparing...", "Cancelled", "N differences") -- the feedback the
  old status-bar timer spam used to provide, now without any running
  timer. It is auto-sized too (TLabel.AutoSize). Its font color is
  set from the UI theme (EdTextFont, the contrast pair of the
  toolbar's EdTextBg background) and re-applied on every theme
  switch: a bare LCL TLabel would draw in the OS widgetset's color
  (black on many systems) and vanish on dark themes.

* The FOLDERS dropdown is the folder-compare hub of the toolbar:
  "Compare folders of these files" opens a NEW folder-compare window
  for the parent folders of the two files this tab compares (an
  untitled half disables the item -- an unsaved document has no
  folder), "Compare two new folders..." opens the folder picker (the
  WinMerge-style dialog of the 'Differ 2\\Compare two folders...'
  command), and "Open compare folders window" brings the most
  recently opened folder-compare window back to the front -- or
  reopens the last picked pair when none is open, or falls back to
  the picker when even the history is empty (Command.
  _toolbar_dirs_timer). Rebuilt on every open, like the other
  dropdowns. The button stays enabled while a compare runs: opening
  a folder window is orthogonal to the file compare.

* The IGNORE dropdown is a popup menu (menu_proc MENU_CREATE) shown
  under the button via MENU_SHOW; its items are checkable and multiple
  can be checked. It is REBUILT on every compare start so it always
  mirrors settings/cuda_differ2.json (the config dialog and the tab
  context menu write there too). While a pure-Python algorithm is the
  effective one, the items disable themselves and an explanatory
  item appears -- same guard as the tab context menu / config dialog.

* The PRESETS dropdown is the quick way to set the algorithm +
  the beautify flags: two mutually exclusive RADIO presets
  ("Preset 1: Fastest comparison - Myers, Fast Align On, Absorb
  Off" and "Preset 2: Better readability (slower) - Histogram,
  Fast Align On, Absorb On" -- the original preset combinations
  with only their align / absorb values updated: BOTH presets turn
  align on with the FAST method (the captions say "Fast Align
  On" -- no "Method" wording), and Preset 2 additionally turns
  absorb on; the algorithms are exactly what they always were), a
  separator, the mutually
  exclusive RADIO algorithms ("Algorithm 1: Native Histogram",
  "Algorithm 2: Native Myers", "Algorithm 3: Hybrid Python
  (slow)"), a separator, the TWO mutually exclusive RADIO choices
  of the SINGLE align_by_similarity dropdown config ("Align by
  similarity: Method 1 - fast" -- the engine-driven joined-block
  mapper; "Align by similarity: Method 2 - slow" -- the original
  pure-Python recursive search (no engine words in the captions);
  there is
  deliberately NO "off" item: re-clicking the checked method turns
  it off, so the off state is reachable without a third item), a
  separator, and the independent checkable toggle "Absorb trivial
  equal blocks". It is REBUILT on every open, so the checkmarks
  always mirror settings/cuda_differ2.json, and the preset
  checkmarks are DERIVED from it -- a preset is an EXACT
  combination of three settings: Preset 1 = native Myers + align
  fast + absorb off; Preset 2 = native Histogram + align fast +
  absorb on; any other combination (align off or slow, the Hybrid
  Python algorithm, included) checks NEITHER (a
  custom selection is visible at a glance). Clicks persist
  'differ2.algorithm.*' (the config dialog's store) and re-compare
  this tab on the 100ms timer, like the ignore items. The two align
  items write the single dropdown VALUE (one key -- nothing to get
  out of sync); clicking the checked Method 1/2 item turns it back
  off (off = the algo-faithful rendering).

* The VIEW dropdown toggles the surrounding UI from the compare tab:
  "Hide all" flips every item at once; "Show all" everything EXCEPT
  the side and bottom panels (a bulk show must not force those docked
  tool windows open, so their items stay unchecked); the checkable items
  are CudaText's status bar, toolbar, sidebar, side panel, bottom
  panel and tab bar (the PROC_SHOW_* app-proc pairs -- the app's own
  View-menu toggles), the gutter's numbers / bookmarks columns (an
  editor prop, set on BOTH halves of the tab) and the gap-aware
  overview panel (the differ2.micromap.enable_overview option; the
  100ms re-compare's refresh then creates or destroys the panel).
  REBUILT on every open, so the checkmarks always mirror the live
  state -- the bars can be toggled from CudaText's own View menu too.
  Unlike Ignore / Presets the button stays enabled while a compare
  runs: visibility is orthogonal to comparing, and the overview
  item's refresh is simply dropped (the usual status hint) when a
  compare is already running.

* CALLBACKS: dlg event handlers (on_change) are live callables
  (dlg_proc cleans them up on DLG_FREE); menu item commands and timers
  use STRING callbacks in the 'module=...;cmd=...;info=...' form
  (Command methods) -- CudaText passes that form's info as the raw
  string, so '<tab id>|<ignore key>' survives without quoting (the
  'func=' form would parse the info value and turn an unquoted
  non-numeric value into None -- the reason the first toolbar version
  silently did nothing on click). The post-toggle refresh goes
  through Command._toolbar_refresh_timer on a 100ms one-shot timer
  (the plugin's established menu-close-first convention).

* SESSION RESTORE: on_start2 schedules Command._toolbar_restore_timer,
  which calls ensure_for_session() for every session-restored compare
  tab, so the toolbars come back at startup.

* TEARDOWN: a toolbar is destroyed when its compare tab is REALLY
  closed (on_close's non-exit branch) -- and that is the ONLY teardown
  there is: nothing is cleaned up at app exit. At app exit CudaText
  fires on_close synthetically from its own exit loop and writes the
  session file only afterwards, so GUI calls there re-enter the
  message loop between the plugin's state-file writes (unregister /
  re-register) and used to cost the compare tabs their persisted
  session entries. The forms are owned by CudaText's main form and
  are freed by it when the app terminates.
  destroy() also NEVER calls menu_proc(MENU_REMOVE) -- that frees the
  popup's ROOT menu item and leaves the (main-form-owned) popup
  dangling; MENU_CLEAR empties it safely.

Options (settings/cuda_differ2.json, chapter 'toolbar' in the config
dialog):
* differ2.toolbar.show_toolbar (default on) -- create/hide toolbars.
* differ2.toolbar.show_btn_text (default on) -- full captions vs
  icon-only buttons.
* differ2.toolbar.icon_theme (default 'auto') -- which picture-icon
  set the buttons use: 'auto' = detect from the toolbar background
  (EdTextBg luminance), 'dark' = the near-white glyphs for dark
  themes, 'light' = the near-black glyphs for light themes.
* differ2.toolbar.icon_size (default 'auto') -- pixel size of the
  picture icons: 'auto' = the OS-DPI pick (16 at 100% ... 32 at
  200%), or one of 16 / 20 / 24 / 28 / 32 pinned by hand (a pinned
  size ignores the DPI).

Narrow windows: when the editor parent is too narrow for the text
row (a small CudaText window, a vertical split, a floating group),
the toolbar AUTOMATICALLY switches to icon-only buttons and back
once there is room again -- the show_btn_text option is honored as
the upper bound (the auto mode never shows texts the option turned
off), and the no-pictures glyph fallback keeps the old overflow
behavior (its glyphs ARE the captions). Debounced 100ms behind the
last resize / layout change, with a hysteresis margin against
boundary flapping (see the _FIT_* constants).
"""

import os

import cudatext as ct
import cudax_lib as ctx
from cudax_lib import get_translation

_ = get_translation(__file__)  # I18N

# The plugin's settings JSON (same file __init__.JSONFILE points to;
# kept in sync by hand -- toolbar.py must not import __init__).
_JSON_FILE = 'cuda_differ2.json'

# Editor text background of the active UI theme -- the toolbar's
# background color (see _ed_text_bg). One flat color that always
# matches the compare view below it, both light and dark themes.
# EdTextFont is its contrast pair: the status label's font color
# (see _ed_text_font). A dlg_proc 'label' is a plain LCL TLabel,
# whose default font color follows the OS WIDGETSET, not CudaText's
# UI theme -- black on many systems, i.e. invisible on the dark
# toolbar background of dark UI themes. So the label's font_color
# is set explicitly from the same theme the background comes from.


def _ed_text_bg():
    """Live editor text background color from the current UI theme
    (PROC_THEME_UI_DICT_GET / EdTextBg), or None when unavailable."""
    try:
        ui = ct.app_proc(ct.PROC_THEME_UI_DICT_GET, '')
        return ui.get('EdTextBg', {}).get('color')
    except Exception:
        return None


def _ed_text_font():
    """Live editor text FONT color from the current UI theme
    (PROC_THEME_UI_DICT_GET / EdTextFont), or None when unavailable.

    The guaranteed-contrast pair of EdTextBg (the toolbar's
    background): whatever the theme does, its editor text color is
    readable on its editor background -- and the toolbar uses that
    very background. Black-on-black status text on dark themes
    (the LCL default font color) is impossible with this."""
    try:
        ui = ct.app_proc(ct.PROC_THEME_UI_DICT_GET, '')
        return ui.get('EdTextFont', {}).get('color')
    except Exception:
        return None


def _split_color():
    """Color of the toolbar's 1px bottom border: the theme's SplitMain
    (the main splitters' color; the overview's left separator reads the
    same key). Fallback 0x808080 = clMedGray."""
    try:
        c = ct.app_proc(ct.PROC_THEME_UI_DICT_GET, '')\
            .get('SplitMain', {}).get('color')
        if c is not None:
            return int(c)
    except Exception:
        pass
    return 0x808080


# ---------------------------------------------------------------------------
# Picture icons (icons/toolbar/...).
#
# The toolbar's buttons express their glyphs as PNG pictures, not as
# UTF-8 font characters: the old glyph captions (↻ ↑ ↓ → ← ≡ ★ ⇋ ↔ ▦ ⚙
# ◫ ▾) are missing from many real-world UI fonts and rendered as tofu
# boxes. The PNG tree ships two theme-tuned sets and five pixel
# sizes:
#
#   icons/toolbar/<set>/<size>/<name>.png
#     set:  'dark'  (near-white glyphs -- black/dark backgrounds)
#           'light' (near-black glyphs -- white/light/light-grey
#                   backgrounds)
#     size: 16 20 24 28 32  (16px at 100% DPI ... 32px at 200%)
#     name: recompare cancel prev next copy_left copy_right ignore
#           presets swap resize view folders config (the 13 button
#           icons)
#           menu                                  (the dropdown caret)
#
# The 14th file menu.png is the dropdown-caret triangle of the four
# caret buttons (see _add_caret_button) and is OPTIONAL: a tree without
# it still loads -- the menu buttons then carry no caret (they open
# their dropdown on click all the same).
#
# The set is re-picked on every UI theme switch (apply_theme -> the
# EdTextBg luminance midpoint) and the size on form creation (OS DPI)
# -- unless the differ2.toolbar.icon_theme / icon_size options pin
# them ('auto', the default, keeps the automatic pick). A missing tree
# / failed imagelist API silently falls back to the old glyph captions
# -- the buttons must never disappear.
# ---------------------------------------------------------------------------

# This file's folder = the plugin's root (cuda_differ2/).
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# The 13 icon names = the 12 buttons + 'cancel' (the Recompare button
# swaps to it while a compare runs, past the _CANCEL_DELAY_MS window).
# The dropdown caret 'menu' is NOT here -- it is optional (see the
# tree comment above and _icon_files).
_ICON_NAMES = (
    'recompare', 'cancel', 'prev', 'next', 'copy_left', 'copy_right',
    'ignore', 'presets', 'swap', 'resize', 'view', 'folders', 'config',
)

# Available pixel sizes of the icon tree, ascending.
_ICON_SIZES = (16, 20, 24, 28, 32)

# Icon set names (the tree's subfolders).
_ICON_SETS = ('dark', 'light')

# EdTextBg luminance midpoint -> icon set: below it the background is
# dark enough for the near-white 'dark' glyphs, at or above it the
# near-black 'light' glyphs win. The value sits at the contrast
# crossover of the two glyph colors (#ECECEC vs #2E2E2E), i.e. just
# around the sRGB mid-grey -- so mid-grey backgrounds (where both are
# mediocre) take the dark set, whose glyphs also looked better there.
_ICON_LUM_MID = 0.22


def _bg_luminance():
    """Perceived (Rec.709, linearized) luminance of the toolbar's
    background color -- 0.0 black .. 1.0 white -- or None when the
    theme does not provide EdTextBg. CudaText color ints are BGR
    (Delphi TColor): the LOW byte is red."""
    c = _ed_text_bg()
    if c is None:
        return None
    try:
        c = int(c)
    except (TypeError, ValueError):
        return None

    def lin(v):
        # sRGB transfer function -> linear light
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r = lin((c & 0xFF) / 255.0)
    g = lin(((c >> 8) & 0xFF) / 255.0)
    b = lin(((c >> 16) & 0xFF) / 255.0)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _icon_set_for_bg():
    """Icon set name for the CURRENT toolbar background: 'dark' /
    'light' (see the midpoint above). An unknown background (no theme
    color) is treated as light -- the create() fallback paints the
    form white there."""
    lum = _bg_luminance()
    if lum is None:
        lum = 1.0
    if lum < _ICON_LUM_MID:
        return 'dark'
    return 'light'


def _icon_size_px():
    """Pixel size of the toolbar icons for the current OS DPI: the
    96-DPI base 16, scaled like every other raw-pixel metric (see
    _scaled), snapped UP to the nearest size the icon tree ships --
    the imagelist API needs PNGs exactly of its own size."""
    want = _scaled(16)
    for s in _ICON_SIZES:
        if s >= want:
            return s
    return _ICON_SIZES[-1]


def _conf_icon_size(value):
    """Pixel size forced by the differ2.toolbar.icon_size option, or
    None for 'auto' / anything unrecognized: the option stores a
    string ('auto', '16', '20', ...), so both str and int are
    accepted."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n in _ICON_SIZES else None


def _conf_icon_set(value):
    """Icon set forced by the differ2.toolbar.icon_theme option, or
    None for 'auto' / anything unrecognized."""
    return value if value in _ICON_SETS else None


def _icon_files(set_name, size):
    """{icon name: PNG path} of one set/size, or {} when the tree (or
    that size) is not installed. The 13 button icons are all required
    -- a half-installed tree is not used (the fallback glyphs are
    better than a toolbar where random buttons lost their faces). The
    dropdown caret 'menu' is optional: it is included when present,
    and a tree without it simply gets no caret buttons."""
    d = os.path.join(_PLUGIN_DIR, 'icons', 'toolbar',
                     set_name, str(size))
    out = {}
    for n in _ICON_NAMES:
        p = os.path.join(d, n + '.png')
        if not os.path.isfile(p):
            return {}
        out[n] = p
    p = os.path.join(d, 'menu.png')
    if os.path.isfile(p):
        out['menu'] = p
    return out


# The five ignore options, exposed as checkable items of the toolbar's
# Ignore dropdown, of the diff-tab context menu and of the config
# dialog ('differ2.ignoreopt.*'). Defined HERE so the toolbar and
# __init__ share one source of truth; __init__ imports it as
# _IGNORE_OPTS. Each entry: (config key suffix, menu caption).
IGNORE_OPTS = (
    ('ignore_case',        _('Ignore case')),
    ('ignore_whitespace',  _('Ignore whitespace')),
    ('ignore_blank_lines', _('Ignore blank lines')),
    ('ignore_eol',         _('Ignore line endings')),
    ('ignore_numbers',     _('Ignore numbers')),
)


def _get_ignore_opt(key):
    """Read one 'differ2.ignoreopt.*' boolean from the plugin's settings
    (mtime-cached by cudax_lib, so values changed in the config dialog
    or the tab context menu are picked up at once)."""
    return bool(ctx.get_opt('differ2.ignoreopt.' + key, False,
                            user_json=_JSON_FILE))


def _set_ignore_opt(key, val):
    """Write one 'differ2.ignoreopt.*' boolean to the plugin's settings
    (same store the config dialog and the tab context menu use)."""
    return ctx.set_opt('differ2.ignoreopt.' + key, bool(val),
                       user_json=_JSON_FILE)


# The Presets dropdown's items: two mutually exclusive preset
# combinations, a separator, the three algorithms (also mutually
# exclusive), a separator, the TWO choices of the SINGLE beautify
# dropdown ('differ2.algorithm.beautify.align_by_similarity' holds
# one of 'fast' / 'slow' / 'off' -- Method 1 is the FAST
# engine-driven joined-block mapper, Method 2 the OLD slow
# pure-Python recursive search, and the "slow" word in the caption
# marks it; there is NO explicit 'off' item: re-clicking the checked
# method writes 'off', so the off state needs no third item), a
# separator, and the independent absorb toggle
# ('differ2.algorithm.beautify.absorb_trivial_equal_blocks').
# The two presets keep their ORIGINAL form -- each is an EXACT
# combination of the three settings (algorithm + align method +
# absorb), picked with one click; only the align / absorb values
# were updated for the new dropdown world (the captions say
# "Fast Align On" -- no "Method" wording -- because BOTH presets
# now align with the fast method):
#   Preset 1 = native Myers + align fast + absorb off
#     (was Myers + align off + absorb off -- align on now, the
#     FAST method, so the preset stays the quick everyday compare);
#   Preset 2 = native Histogram + align fast + absorb on
#     (was Histogram + align on + absorb off -- the slow method
#     the preset always had is replaced by the FAST one, and
#     absorb turns on).
# Each entry: (menu key, menu caption); None = the separator.
# Toolbar-only -- the config dialog / tab context menu keep their own
# algorithm UIs.
_PRESET_ITEMS = (
    ('preset1',  _('Preset 1: Fastest comparison - Myers, '
                   'Fast Align On, Absorb Off')),
    ('preset2',  _('Preset 2: Better readability (slower) - Histogram, '
                   'Fast Align On, Absorb On')),
    (None, None),
    ('algo1',    _('Algorithm 1: Native Histogram')),
    ('algo2',    _('Algorithm 2: Native Myers')),
    ('algo3',    _('Algorithm 3: Hybrid Python (slow)')),
    (None, None),
    ('beautify_fast',  _('Align by similarity: Method 1 - fast')),
    ('beautify_slow',  _('Align by similarity: Method 2 - slow')),
    (None, None),
    ('absorb',   _('Absorb trivial equal blocks')),
)

# Radio-item grouping of the mutually exclusive items (menu_proc
# MENU_SET_RADIOITEM + MENU_SET_GROUPINDEX -- the Lazarus radio
# mechanism: items marked RadioItem that share a GroupIndex form one
# group; clicking one checks it and auto-unchecks the others, and the
# mark renders as a radio dot instead of a checkmark). The two
# presets form one group (as they always did -- a preset is one
# exact combination, so at most one can describe the current
# settings), the three algorithms another, and the two align-method
# choices a third; the absorb toggle stays a plain checkable item
# (an independent feature). Purely visual polish -- the checkmarks
# are still re-derived from the settings on every menu open, and the
# click handlers write the same exclusive values, so behavior is
# unchanged without it.
_PRESET_RADIO = {
    'preset1': 1,
    'preset2': 1,
    'algo1': 2,
    'algo2': 2,
    'algo3': 2,
    'beautify_fast': 3,
    'beautify_slow': 3,
}

# Values written to 'differ2.algorithm.diff_algorithm' by the preset /
# algorithm items (the same values the config dialog writes; on older
# CudaText builds without diff_proc the plugin falls back to the
# closest pure-Python algorithm -- native_histogram -> hybrid,
# native_myers -> myers. 'hybrid' IS a pure-Python algorithm, so it
# runs everywhere; it is the "third algorithm" of the menu, and the
# "(slow)" word in its caption marks that it is not a native one).
_ALGO_MYERS = 'native_myers'
_ALGO_HIST = 'native_histogram'
_ALGO_HYBRID = 'hybrid'


def _get_diff_algo():
    """The configured algorithm ('differ2.algorithm.diff_algorithm'),
    read live from the plugin's settings (mtime-cached by cudax_lib,
    so config-dialog / tab-menu writes are picked up at once)."""
    return ctx.get_opt('differ2.algorithm.diff_algorithm', 'native_myers',
                       user_json=_JSON_FILE)


def _set_diff_algo(val):
    """Write 'differ2.algorithm.diff_algorithm' to the plugin's settings
    (same store the config dialog uses)."""
    return ctx.set_opt('differ2.algorithm.diff_algorithm', val,
                       user_json=_JSON_FILE)


# --- The SINGLE Align-by-similarity dropdown config ------------------
# 'differ2.algorithm.beautify.align_by_similarity' is ONE option with
# three values ('fast' / 'slow' / 'off'), rendered as a dropdown in
# the config dialog and as the radio pair of the Presets menu. ONE
# stored string -- the two methods are exclusive BY CONSTRUCTION
# ("both methods on" is structurally impossible), and 'off' is
# simply the absence of a method (no item needed in the menu).

ALIGN_FAST = 'fast'
ALIGN_SLOW = 'slow'
ALIGN_OFF = 'off'
# All valid values of the dropdown (the OPTS_META 'dct' keys of
# __init__ -- listed there in the display order off / fast / slow).
ALIGN_MODES = (ALIGN_OFF, ALIGN_FAST, ALIGN_SLOW)

_ALIGN_OPT = 'differ2.algorithm.beautify.align_by_similarity'


def resolve_align_mode(raw_val):
    """PURE value resolver of the single align_by_similarity dropdown:
    returns ALIGN_FAST / ALIGN_SLOW / ALIGN_OFF from the raw stored
    value. Shared by the toolbar and Command.get_config -- ONE rule
    everywhere. A valid stored string passes through; anything else
    (a junk hand-edit) falls back to the option's DEFAULT, which is
    ALIGN_FAST -- the fast engine-driven alignment (Method 1) is the
    out-of-the-box behavior since the default change from 'off'."""
    if raw_val in (ALIGN_FAST, ALIGN_SLOW, ALIGN_OFF):
        return raw_val
    return ALIGN_FAST


def get_align_mode():
    """The RESOLVED Align-by-similarity mode (one of ALIGN_MODES),
    read live from the plugin's settings (mtime-cached by cudax_lib,
    so config-dialog / toolbar / hand-edited changes are picked up at
    once), through the shared resolve_align_mode. The read's DEFAULT
    is ALIGN_FAST: a fresh install (no stored value yet) gets the
    fast engine-driven alignment -- the beautified side-by-side look
    out of the box; users who want the raw algo-faithful rendering
    set the dropdown to 'off' once and that choice persists."""
    return resolve_align_mode(
        ctx.get_opt(_ALIGN_OPT, ALIGN_FAST, user_json=_JSON_FILE))


def set_align_mode(mode):
    """Write the single 'differ2.algorithm.beautify.align_by_similarity'
    dropdown value to the plugin's settings (the config dialog's
    store). Anything but 'fast' / 'slow' is stored as 'off'."""
    if mode not in (ALIGN_FAST, ALIGN_SLOW):
        mode = ALIGN_OFF
    ctx.set_opt(_ALIGN_OPT, mode, user_json=_JSON_FILE)
    return mode


def _align_state_text():
    """The live Align-by-similarity state as one word for the status
    line and the Presets tooltip: 'fast' (Method 1: the engine-driven
    joined-block mapper), 'slow' (Method 2: the original pure-Python
    recursive search) or 'off' -- the resolved value of the single
    dropdown config (see get_align_mode)."""
    mode = get_align_mode()
    if mode == ALIGN_FAST:
        return _('fast')
    if mode == ALIGN_SLOW:
        return _('slow')
    return _('off')


def _get_absorb():
    """The Absorb-trivial-equal-blocks flag
    ('differ2.algorithm.beautify.absorb_trivial_equal_blocks'), read
    live from the settings."""
    return bool(ctx.get_opt(
        'differ2.algorithm.beautify.absorb_trivial_equal_blocks', False,
        user_json=_JSON_FILE))


def _set_absorb(val):
    """Write 'differ2.algorithm.beautify.absorb_trivial_equal_blocks'
    to the plugin's settings (same store the config dialog uses)."""
    return ctx.set_opt(
        'differ2.algorithm.beautify.absorb_trivial_equal_blocks',
        bool(val), user_json=_JSON_FILE)


# The View dropdown's checkable items, in the user's order: CudaText's
# six main UI bars, the gutter's two columns, then the overview panel
# ('overview', a single key -- the differ2.micromap.enable_overview
# option). Each bar entry: (menu key, caption, app-proc GET id,
# app-proc SET id) -- the PROC_SHOW_* pairs are the app's own
# View-menu toggles. Each gutter entry: (menu key, caption, editor
# prop). 'Hide all' / 'Show all' (above the separator) are plain
# actions, not checkable.
_VIEW_BARS = (
    ('statusbar',   _('Status bar'),
     ct.PROC_SHOW_STATUSBAR_GET, ct.PROC_SHOW_STATUSBAR_SET),
    ('toolbar',     _('Toolbar'),
     ct.PROC_SHOW_TOOLBAR_GET, ct.PROC_SHOW_TOOLBAR_SET),
    ('sidebar',     _('Sidebar'),
     ct.PROC_SHOW_SIDEBAR_GET, ct.PROC_SHOW_SIDEBAR_SET),
    ('sidepanel',   _('Side panel'),
     ct.PROC_SHOW_SIDEPANEL_GET, ct.PROC_SHOW_SIDEPANEL_SET),
    ('bottompanel', _('Bottom panel'),
     ct.PROC_SHOW_BOTTOMPANEL_GET, ct.PROC_SHOW_BOTTOMPANEL_SET),
    ('tabs',        _('Tab bar'),
     ct.PROC_SHOW_TABS_GET, ct.PROC_SHOW_TABS_SET),
)
_VIEW_GUTTERS = (
    ('gutter_num', _('Gutter numbers'), ct.PROP_GUTTER_NUM),
    ('gutter_bm',  _('Gutter bookmarks'), ct.PROP_GUTTER_BM),
)

# 'Show all' restores the main chrome only: the side and bottom panels
# host docked tool windows (Console / Output / TODO...), so the bulk
# show must not force them open -- their menu items stay untouched
# (unchecked when hidden) and are toggled one by one. 'Hide all'
# still hides them (hiding everything keeps meaning everything).
_SHOW_ALL_SKIP = frozenset(('sidepanel', 'bottompanel'))


# The Folders dropdown's items (the folder-compare hub of the
# toolbar and the tab context menu): 'of_files' compares the parent
# folders of the two files THIS compare tab compares, 'two_new' opens
# the folder picker (the WinMerge-style dialog of the
# 'Differ 2\\Compare two folders...' command), 'window' focuses /
# reopens the folder-compare window. All three run through
# Command._toolbar_dirs_timer on the 100ms menu-close-first timer
# (the picker is a modal dialog). Each entry: (menu key, caption).
_FOLDER_ITEMS = (
    ('of_files', _('Compare folders of these files')),
    ('two_new',  _('Compare two new folders...')),
    ('window',   _('Open compare folders window')),
)


def _get_overview_opt():
    """The gap-aware overview panel option
    ('differ2.micromap.enable_overview'), read live from the plugin's
    settings (mtime-cached by cudax_lib, so config-dialog writes are
    picked up at once)."""
    return bool(ctx.get_opt('differ2.micromap.enable_overview', True,
                            user_json=_JSON_FILE))


def _set_overview_opt(val):
    """Write 'differ2.micromap.enable_overview' to the plugin's settings
    (same store the config dialog uses)."""
    return ctx.set_opt('differ2.micromap.enable_overview', bool(val),
                       user_json=_JSON_FILE)


# ---------------------------------------------------------------------------
# Layout constants.
#
# NO widths are computed anywhere: buttons are auto-sized (control prop
# 'autosize' -> TATButton.SetAutoSize measures the caption with the
# real UI-theme font, DPI-scaled), and positions come from anchors.
# ---------------------------------------------------------------------------

# Tight sp_l spacing at the row's start and after a separator (the
# outer sides of the groups; the separators' own spacing is untouched).
_BTN_GAP = 2
# Roomy sp_l spacing BETWEEN two neighboring buttons of one group (a
# button whose left neighbor is also a button) -- the user asked for
# breathing room between buttons, not around the separators. Logical
# px, DPI-scaled (like _TEXT_SLACK; the tight gaps stay raw: they are
# already fine).
_BTN_GAP_INNER = 8
# Extra spacing to the left of a separator (in addition to _BTN_GAP),
# so groups breathe a little more than single buttons.
_SEP_GAP = 6
# Width of the vertical separator buttons.
_SEP_W = 2
# sp_l of a dropdown-caret companion button -- tight: the caret
# visually belongs to its menu button (like the old caption's
# trailing ' \u25be'), the button's own trailing auto-size gap
# provides the real separation.
_CARET_GAP = 1
# Minimum width of a button (constraint): keeps single-glyph icon-only
# buttons comfortably clickable.
_BTN_W_MIN = 26
# Vertical inset of buttons/separators from the form's top/bottom.
_BTN_V_PAD = 1
# Delay before the toolbar's Recompare button swaps to '× Cancel' after
# a compare is kicked off (see set_comparing / _cancel_swap_tick). Its
# only job is to absorb the accidental second click that follows the
# kick-off click: a click landing inside this window is swallowed
# entirely, so a double-click (or a late button-up) can never cancel a
# compare that just started. One second is long enough to cover any
# realistic double-click yet short enough that a genuine cancel is
# never more than a second away.
_CANCEL_DELAY_MS = 1000
# Spacing between the status label and the form's right edge.
_STATUS_SP_R = 10

# --- Narrow-window auto icon-only mode --------------------------------
#
# When the editor parent is too narrow for the full-text button row
# (a small CudaText window, a vertical split, a detached floating
# group), the toolbar switches ITSELF to icon-only buttons and back
# when there is room again -- chosen over wrapping to a second row
# because every button already HAS a picture icon (the icon-only mode
# is the show_btn_text=False path), the one-row height stays constant
# (no editor-area jump, no re-layout of the compare view below), and
# the tooltips keep every action identifiable. The user option
# differ2.toolbar.show_btn_text stays what it is: the auto mode only
# ever HIDES texts temporarily, it never shows them while the option
# is off; without picture icons (the UTF-8 glyph fallback) there is
# no icon-only mode at all (the glyphs ARE the captions) and the
# toolbar keeps its old overflow behavior.
#
# Hysteresis: collapse as soon as the available width drops below the
# needed width, expand only once it exceeds it by _FIT_HYST logical
# px -- without that margin a window resized to sit exactly at the
# boundary would flip between the two layouts on every caption
# change (the Ignore counter, the Recompare/Cancel swap).
_FIT_HYST = 24
# Debounce of the fit check: resize events storm during an
# interactive drag, and the anchor re-flow needs a settled layout to
# measure -- the one-shot timer restarts on every event (CudaText's
# timer_proc finds the running timer by its callback string), so the
# check runs once, 100ms after the LAST resize / layout change.
_FIT_CHECK_MS = 100


def _bar_height():
    """Height of the toolbar's BUTTON ZONE: the OS/DPI-correct height of
    a GUI button (PROC_GET_GUI_HEIGHT), clamped to a sane band."""
    try:
        h = ct.app_proc(ct.PROC_GET_GUI_HEIGHT, 'button')
        if h and h > 0:
            return max(24, min(int(h), 44))
    except Exception:
        pass
    return 30


def _dpi_percent():
    """OS high-DPI scale in percent (100 = no scaling), read from
    PROC_GET_SYSTEM_PPI: usual value is 96ppi = 100%, 144ppi = 150%.
    dlg_proc control sizes are RAW device pixels (no auto-scaling),
    so the plugin's logical constants must be scaled by hand."""
    try:
        ppi = ct.app_proc(ct.PROC_GET_SYSTEM_PPI, '')
        ppi = int(ppi or 0)
        if ppi >= 96:
            return max(100, ppi * 100 // 96)
    except Exception:
        pass
    return 100


def _scaled(px):
    """Logical (96-DPI) pixels -> physical pixels at the current OS DPI
    (at least 1, so a strip is never zero-sized)."""
    return max(1, int(px) * _dpi_percent() // 100)


def _button_gap(prev_kind):
    """sp_l of a button: the roomy _BTN_GAP_INNER (DPI-scaled) when its
    left neighbor is also a button -- two buttons inside one group;
    the tight _BTN_GAP at the row's start and after a separator (the
    separator sides keep their own spacing, _SEP_GAP / _BTN_GAP)."""
    if prev_kind == 'btn':
        return _scaled(_BTN_GAP_INNER)
    return _BTN_GAP


# Height of the bottom-border strip, DEVICE px -- never scaled: the
# line itself is 1 device px at any DPI (see _add_bottom_border).
_BORDER_H = 1
# Extra logical px on top of the OS GUI button height: TATButton centers
# the caption and clips its descenders when the font's TextExtent is taller
# than the stretched button (the 'g' of 'Config' was eaten at the bottom),
# so the zone gets a little breathing room.
_TEXT_SLACK = 4


def _total_height():
    """Total height of the toolbar form: button zone + descender slack
    (DPI-scaled) + the 1-device-px bottom-border strip."""
    return _bar_height() + _scaled(_TEXT_SLACK) + _BORDER_H


# ---------------------------------------------------------------------------
# The toolbar.
# ---------------------------------------------------------------------------

class CompareToolbar:
    """One toolbar docked to the top of ONE compare tab.

    'cmd' is the Command instance of cuda_differ2 (all actions are its
    methods); 'session' is the tab's _TabSession (the toolbar's
    lifetime is the session's lifetime); 'a_ed' is any editor of that
    tab (used for the parent handle and for refreshes).
    """

    # (name, kind, icon, text) in visual order -- five groups:
    # [Recompare/Cancel] | [Prev][Next] | [Copy to right][Copy to left] |
    # [Ignore][caret][Preset][caret] |
    # [Swap][Resize][View][caret][Folders][caret][Config].
    # The 'icon' column is the LEGACY UTF-8 glyph -- used only when the
    # picture icons are unavailable (missing icon tree / failed
    # imagelist API); with pictures on, the icon comes from the form's
    # own imagelist (see _setup_icons) and the caption is bare text.
    # The 'ignore' caption is assembled dynamically (see
    # _ignore_caption), the 'presets', 'view' and 'folders' captions
    # are plain text, and the Recompute button swaps icon/text with 'Cancel'
    # while a compare runs -- but DELAYED by _CANCEL_DELAY_MS (the
    # swap must not be live at the moment the kick-off click's
    # double-click twin lands on the button).
    _BTNS = (
        ('recompare', 'btn', '\u21bb', 'Recompare'),
        ('sep1',       'sep', None, None),
        ('prev',       'btn', '\u2191', 'Prev'),
        ('next',       'btn', '\u2193', 'Next'),
        ('sep2',       'sep', None, None),
        ('copy_right', 'btn', '\u2192', 'Copy'),
        ('copy_left',  'btn', '\u2190', 'Copy'),
        ('sep3',       'sep', None, None),
        ('ignore',     'btn', '\u2261', 'Ignore'),
        ('presets',    'btn', '\u2605', 'Preset'),
        ('sep4',       'sep', None, None),
        ('swap',       'btn', '\u21cb', 'Swap'),
        ('resize',     'btn', '\u2194', 'Resize'),
        ('view',       'btn', '\u25a6', 'View'),
        ('folders',    'btn', '\u25eb', 'Folders'),
        ('config',     'btn', '\u2699', 'Config'),
    )

    # The four dropdown buttons -- each gets a small caret companion
    # button chained to its right when the icon tree ships menu.png
    # (see _add_caret_button).
    _MENU_BTNS = ('ignore', 'presets', 'view', 'folders')

    def __init__(self, cmd, session, a_ed):
        self.cmd = cmd
        self.session = session
        self.tab_id_str = session.tab_id_str
        self.a_ed = a_ed
        self.h_dlg = None
        self.h_menu = None
        self.h_pmenu = None
        self.h_vmenu = None
        self.h_fmenu = None
        self.ctl = {}          # name -> control index
        self.hbtn = {}         # name -> button_ex handle (button_proc)
        self.menu_items = {}   # ignore key -> popup menu item id
        self.menu_guard_item = None
        self.comparing = False
        # Cancel-button state machine (see set_comparing):
        # _cancel_shown -- the 'Cancel' face (icon + text) is CURRENTLY
        #   on the recompare button (False during the _CANCEL_DELAY_MS
        #   grace window, so the button still reads Recompare right
        #   after kick-off);
        # _cancel_swap_pending -- the one-shot swap timer is armed.
        self._cancel_shown = False
        self._cancel_swap_pending = False
        # Picture-icon state (see _setup_icons): h_imglist -- the
        # form-owned imagelist handle; _icon_idx -- icon name ->
        # imagelist index; _icon_set / _icon_size -- the set and pixel
        # size it was built from ('dark'/'light', 16..32 -- for
        # apply_theme's midpoint check and apply_icon_options');
        # _icons_ok -- False = legacy UTF-8 glyph captions.
        self.h_imglist = None
        self._icon_idx = {}
        self._icon_set = None
        self._icon_size = None
        self._icons_ok = False
        self.n_diffs = 0
        self.show_text = True
        self.status = ''
        self.height = _total_height()
        # --- Narrow-window auto icon-only mode (see the _FIT_* block
        # above): _narrow -- the toolbar is CURRENTLY collapsed to
        # icon-only buttons because the editor parent is too narrow
        # for the text row; _text_row_w -- the needed width of the
        # LAST text-mode layout (row end + status label + right
        # margin), kept while collapsed so the expand test compares
        # against the TEXT row, not the (much narrower) icon row;
        # _in_fit -- re-entrancy guard (the collapse / expand
        # relayouts must not re-enter the fit check synchronously).
        self._narrow = False
        self._text_row_w = None
        self._in_fit = False

    # -- creation ----------------------------------------------------------

    def create(self):
        """Create the form, the buttons and the ignore popup menu, then
        dock the form to the TOP of the compare tab's editor parent.
        Returns True on success."""
        h_parent = 0
        try:
            h_parent = self.a_ed.get_prop(ct.PROP_HANDLE_PARENT)
        except Exception:
            h_parent = 0
        if not h_parent:
            return False

        bgcolor = _ed_text_bg()
        if bgcolor is None:
            bgcolor = 0xFFFFFF
        self.show_text = bool(self.cmd.cfg.get('show_btn_text', True))

        h = ct.dlg_proc(0, ct.DLG_CREATE)
        self.h_dlg = h
        ct.dlg_proc(h, ct.DLG_PROP_SET, prop={
            'cap': 'Differ 2',
            'w': 700,
            'h': self.height,
            'border': ct.DBORDER_NONE,
            'color': bgcolor,
            # Live form-level callback (cudatext.py replaces callables
            # in any 'on_' prop with its proxy string): the docked form
            # is resized by the editor parent on every window / split
            # resize -- the debounce entry of the auto icon-only mode.
            'on_resize': self._on_form_resize,
        })

        # The bottom border FIRST: the buttons' and separators' a_b
        # anchors reference it by name ('brd'), so it must exist before
        # they are created (dlg_proc resolves anchor targets at
        # prop-set time).
        self._add_bottom_border()

        # Picture icons BEFORE the buttons: _add_button asks the icon
        # state for the initial kind (text+icon / icon-only / the
        # legacy text-only fallback), so the first paint is already
        # the final look.
        self._setup_icons()

        # Controls are chained left-to-right with anchors: each control's
        # a_l is the PREVIOUS control's ']' (right side), so the row
        # re-flows by itself whenever any button's auto-sized width
        # changes. No 'x'/'w' is ever set on buttons.
        prev = None
        prev_kind = None
        for name, kind, icon, text in self._BTNS:
            if kind == 'sep':
                self._add_separator(name, prev)
                prev = name
            else:
                self._add_button(name, icon, text, prev, prev_kind)
                prev = name
                # A dropdown button's caret companion is chained to ITS
                # right, so the next control anchors to the caret.
                if name in self._MENU_BTNS and self._icon_idx.get(\
                        'menu', -1) >= 0:
                    self._add_caret_button(name)
                    prev = name + '_caret'
            prev_kind = kind

        # Status label on the right: the compare state / diff count.
        self._add_status_label()

        self._layout_buttons()
        self.set_status('')

        # Show, then dock to the TOP side of the editor's parent (the
        # same DLG_DOCK mechanism the overview panel uses for 'R').
        ct.dlg_proc(h, ct.DLG_SHOW_NONMODAL)
        ct.dlg_proc(h, ct.DLG_DOCK, prop='T', index=h_parent)

        self.rebuild_ignore_menu()
        self._update_nav_enabled()
        # First fit check AFTER the docking (the dock resize fires
        # on_resize too, but the timer's debounce makes this explicit
        # arm the safe catch-all): a compare tab created narrow -- a
        # vertical split, a small window -- starts collapsed.
        self._arm_fit_check()
        return True

    def _add_bottom_border(self):
        """Full-width horizontal line glued to the form's bottom edge:
        a 'panel' control of height 1 filled with the theme's
        SplitMain. dlg_proc never scales control sizes (only the
        explicit DLG_SCALE action scales, and this form never calls
        it), so h=1 is exactly one device pixel at any DPI -- the
        whole strip is the line. Created FIRST: the buttons' a_b
        anchors reference it by name ('brd')."""
        n = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_ADD, 'panel')
        self.ctl['brd'] = n
        ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n, prop={
            'name': 'brd',
            'cap': '',
            'h': _BORDER_H,      # 1 device px at ANY DPI
            'color': _split_color(),
            'a_l': ('', '['),
            'a_r': ('', ']'),
            'a_t': None,
            'a_b': ('', ']'),
        })

    def _anchor_left(self, prev):
        """a_l value chaining this control to the RIGHT side of the
        previous control ('' = the form for the first one)."""
        return (prev, ']') if prev else ('', '[')

    def _texts_on(self):
        """Whether button texts are shown RIGHT NOW: the show_btn_text
        option AND not currently collapsed into the narrow-window
        icon-only mode (see the _FIT_* block). The single accessor every
        caption / kind computation reads -- the option and the auto
        collapse can never disagree about what a button shows."""
        return self.show_text and not self._narrow

    def _btn_kind(self, cap=''):
        """TATButton kind for the current mode: BTNKIND_TEXT_ICON_HORZ
        with button texts on (or when a counter caption survives in
        icon-only mode -- the Ignore button's '2/5'), BTNKIND_ICON_ONLY
        for bare icons, BTNKIND_TEXT_ONLY as the legacy no-pictures
        fallback."""
        if not self._icons_ok:
            return ct.BTNKIND_TEXT_ONLY
        if self._texts_on() or cap:
            return ct.BTNKIND_TEXT_ICON_HORZ
        return ct.BTNKIND_ICON_ONLY

    def _add_button(self, name, icon, text, prev, prev_kind=None):
        n = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_ADD, 'button_ex')
        self.ctl[name] = n
        # Dict order matters: 'cap' BEFORE 'autosize' -- the auto-size
        # pass must measure the final caption. 'w_min' (constraints) is
        # applied by CudaText before everything else.
        ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n, prop={
            'name': name,
            'w_min': _BTN_W_MIN,
            'hint': self._tooltip(name),
            'cap': self._caption(icon, text),
            'autosize': True,
            'a_l': self._anchor_left(prev),
            'a_t': ('', '['),
            'a_b': ('brd', '['),
            'sp_l': _button_gap(prev_kind),
            'sp_t': _BTN_V_PAD,
            'sp_b': _BTN_V_PAD,
            'tab_stop': False,
            'on_change': self._on_button,
        })
        hb = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_HANDLE, index=n)
        self.hbtn[name] = hb
        try:
            ct.button_proc(hb, ct.BTN_SET_KIND, self._btn_kind())
            ct.button_proc(hb, ct.BTN_SET_FLAT, True)
            ct.button_proc(hb, ct.BTN_SET_FOCUSABLE, False)
        except Exception:
            pass
        self._apply_button_icon(name)

    def _add_separator(self, name, prev):
        n = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_ADD, 'button_ex')
        self.ctl[name] = n
        ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n, prop={
            'name': name,
            'w': _SEP_W,
            'a_l': self._anchor_left(prev),
            'a_t': ('', '['),
            'a_b': ('brd', '['),
            'sp_l': _SEP_GAP,
            'sp_t': _BTN_V_PAD + 1,
            'sp_b': _BTN_V_PAD + 1,
            'tab_stop': False,
        })
        hb = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_HANDLE, index=n)
        self.hbtn[name] = hb
        try:
            # BTNKIND_SEP_HORZ is the vertical LINE kind (for controls
            # laid out in a horizontal row); BTNKIND_SEP_VERT draws a
            # horizontal line instead.
            ct.button_proc(hb, ct.BTN_SET_KIND, ct.BTNKIND_SEP_HORZ)
            ct.button_proc(hb, ct.BTN_SET_FOCUSABLE, False)
        except Exception:
            pass

    def _add_caret_button(self, name):
        """The small dropdown-caret companion of a menu button: an
        icon-only flat button showing the 'menu' triangle, chained to
        the RIGHT of '<name>' (so it sits after the button's icon AND
        text) and opening the very same dropdown on click. This is
        what marks Ignore / Preset / View as menus now that their
        icons no longer carry a baked-in caret: the glyphs stay
        full-size like every other button's, and the caret is its own
        clearly visible picture (the old baked one had to shrink the
        glyph to make room and was itself tiny).

        sp_l is tight (the caret visually belongs to its button, like
        the old caption's trailing ' ▾'); the button's own
        trailing auto-size gap provides the actual separation. No
        w_min: the auto-sized icon-cell width (cell + NGap) is
        clickable enough for a secondary target that only duplicates
        the button next to it."""
        cname = name + '_caret'
        n = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_ADD, 'button_ex')
        self.ctl[cname] = n
        ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n, prop={
            'name': cname,
            'cap': '',
            'autosize': True,
            'a_l': self._anchor_left(name),
            'a_t': ('', '['),
            'a_b': ('brd', '['),
            'sp_l': _CARET_GAP,
            'sp_t': _BTN_V_PAD,
            'sp_b': _BTN_V_PAD,
            'tab_stop': False,
            'on_change': self._on_button,
        })
        hb = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_HANDLE, index=n)
        self.hbtn[cname] = hb
        try:
            ct.button_proc(hb, ct.BTN_SET_KIND, ct.BTNKIND_ICON_ONLY)
            ct.button_proc(hb, ct.BTN_SET_FLAT, True)
            ct.button_proc(hb, ct.BTN_SET_FOCUSABLE, False)
        except Exception:
            pass
        self._apply_button_icon(cname)
        self._set_hint(cname, self._tooltip(name))

    def _add_status_label(self):
        n = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_ADD, 'label')
        self.ctl['status'] = n
        # A plain LCL TLabel defaults to the OS widgetset font color
        # (black on many systems) -- invisible on the dark toolbar
        # background of dark UI themes. Font color comes from the SAME
        # theme as the background (EdTextFont vs EdTextBg); the black
        # fallback only pairs with create()'s white bg fallback (both
        # hit only when the theme dict itself is unavailable).
        fontcolor = _ed_text_font()
        if fontcolor is None:
            fontcolor = 0x000000
        ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n, prop={
            'name': 'status',
            'cap': '',
            'autosize': True,    # TLabel sizes itself to the caption
            'a_l': None,         # anchored to the form's RIGHT edge,
            'a_r': ('', ']'),    # vertically centered on the LAST real
            'a_t': ('config', '-'),  # button (the button row's height,
            'sp_r': _STATUS_SP_R,    # not the border-including form)
            'tab_stop': False,
            'font_color': fontcolor,   # theme text color, NOT OS black
        })

    # -- captions / layout --------------------------------------------------

    def _caption(self, icon, text):
        """Caption for a button: with the picture icons on, the bare
        (translated) text while button texts are shown, and '' in
        icon-only mode -- the imagelist carries the glyph. With the
        icons off (missing tree / failed API), the legacy UTF-8 glyph
        caption: 'glyph text' or the bare glyph."""
        if self._icons_ok:
            if self._texts_on() and text:
                return _(text)
            return ''
        if self._texts_on() and text:
            return icon + ' ' + _(text)
        return icon

    def _ignore_counts(self):
        """(enabled, total) over the five ignore options, read live from
        the settings file (config-dialog / tab-menu writes included)."""
        enabled = sum(1 for key, _cap in IGNORE_OPTS if _get_ignore_opt(key))
        return enabled, len(IGNORE_OPTS)

    def _ignore_caption(self):
        """'Ignore 2/5' -- the counter shows how many of the options
        are enabled; with none enabled the numbers are omitted; with
        button texts off the counter ALONE survives next to the icon
        (the dropdown caret is the companion button to the right, and
        the legacy glyph + trailing arrow only appear in the
        no-pictures fallback)."""
        n, total = self._ignore_counts()
        counter = ' {}/{}'.format(n, total) if n else ''
        if self._icons_ok:
            if self._texts_on():
                return _('Ignore') + counter
            return counter.strip()
        arrow = ' \u25be'
        if self._texts_on():
            return '\u2261 ' + _('Ignore') + counter + arrow
        return '\u2261' + counter + arrow

    def _presets_caption(self):
        """'Preset' -- the dropdown caret is the companion button to
        the right; the legacy star glyph + trailing arrow only appear
        in the no-pictures fallback."""
        if self._icons_ok:
            return _('Preset') if self._texts_on() else ''
        if self._texts_on():
            return '\u2605 ' + _('Preset') + ' \u25be'
        return '\u2605 \u25be'

    def _view_caption(self):
        """'View' -- the dropdown caret is the companion button to the
        right; the legacy pane glyph + trailing arrow only appear in
        the no-pictures fallback."""
        if self._icons_ok:
            return _('View') if self._texts_on() else ''
        if self._texts_on():
            return '\u25a6 ' + _('View') + ' \u25be'
        return '\u25a6 \u25be'

    def _folders_caption(self):
        """'Folders' -- the dropdown caret is the companion button to
        the right; the legacy two-panel glyph + trailing arrow only
        appear in the no-pictures fallback (U+25EB is a rectangle
        bisected into a left and a right half -- two folders side by
        side, the folder-compare idea)."""
        if self._icons_ok:
            return _('Folders') if self._texts_on() else ''
        if self._texts_on():
            return '\u25eb ' + _('Folders') + ' \u25be'
        return '\u25eb \u25be'

    def _wanted_set(self):
        """Icon set the options ask for: the differ2.toolbar.icon_theme
        value ('dark'/'light') when it pins one, else the automatic
        EdTextBg-luminance pick ('auto')."""
        conf = None
        try:
            conf = _conf_icon_set(self.cmd.cfg.get('icon_theme', 'auto'))
        except Exception:
            conf = None
        return conf if conf else _icon_set_for_bg()

    def _wanted_size(self):
        """Pixel size the options ask for: the differ2.toolbar.icon_size
        value (16..32) when it pins one, else the automatic OS-DPI
        pick ('auto')."""
        conf = None
        try:
            conf = _conf_icon_size(self.cmd.cfg.get('icon_size', 'auto'))
        except Exception:
            conf = None
        return conf if conf else _icon_size_px()

    def _setup_icons(self, set_name=None, size=None):
        """(Re)build the form-owned imagelist from the wanted
        picture-icon set and fill _icon_idx; _icons_ok ends True only
        when every icon of some set loaded (see _icon_files for the
        all-or-nothing rule). Reused on theme switches and option
        changes: the imagelist handle survives, only its images are
        replaced.

        Candidates, in order: the wanted set at the wanted size (the
        theme/DPI pick, or the option-pinned one), the wanted set at
        16px, then the dark / light sets at 16px -- a pruned tree
        degrades to SOMETHING pictorial before it ever falls back to
        the legacy glyphs. A total failure (no tree at all, or the
        imagelist API missing on an ancient build) leaves _icons_ok
        False and the glyph captions in charge."""
        if self.h_dlg is None:
            return
        if set_name is None:
            set_name = self._wanted_set()
        if size is None:
            size = self._wanted_size()
        for sname, ssize in ((set_name, size), (set_name, 16),
                             ('dark', 16), ('light', 16)):
            files = _icon_files(sname, ssize)
            if not files:
                continue
            try:
                if self.h_imglist is None:
                    self.h_imglist = ct.imagelist_proc(
                        0, ct.IMAGELIST_CREATE, value=self.h_dlg)
                    if not self.h_imglist:
                        self.h_imglist = None
                        return
                else:
                    ct.imagelist_proc(self.h_imglist,
                                      ct.IMAGELIST_DELETE_ALL)
                if ssize != 16:
                    # imagelists are 16x16 by default; PNGs must match
                    # the list size exactly or they load cropped
                    ct.imagelist_proc(self.h_imglist,
                                      ct.IMAGELIST_SET_SIZE,
                                      value=(ssize, ssize))
                idx = {}
                loaded = 0
                for n, p in files.items():
                    i = ct.imagelist_proc(self.h_imglist,
                                          ct.IMAGELIST_ADD, value=p)
                    i = i if i is not None else -1
                    idx[n] = i
                    loaded += 1 if i >= 0 else 0
                if not loaded:
                    continue
                self._icon_idx = idx
                self._icon_set = sname
                self._icon_size = ssize
                self._icons_ok = True
                return
            except Exception:
                continue
        self._icons_ok = False
        self._icon_idx = {}
        self._icon_set = None
        self._icon_size = None

    def _apply_button_icon(self, name, cap=''):
        """(Re)attach one button's picture icon: imagelist, image
        index and kind. Called at creation (from _add_button) and from
        _layout_buttons BEFORE the caption / autosize re-set --
        TATButton's width pass must see the final kind (icon-only
        buttons are as wide as their icon, text+icon buttons count
        both). Caret companion buttons ('<menu>_caret') show the
        'menu' triangle and are always icon-only. The Cancel swap
        lives here too: while a compare runs (past the
        _CANCEL_DELAY_MS grace window) the Recompare button shows the
        'cancel' X icon."""
        hb = self.hbtn.get(name)
        if not hb:
            return
        if not (self._icons_ok and self.h_imglist):
            try:
                ct.button_proc(hb, ct.BTN_SET_KIND, ct.BTNKIND_TEXT_ONLY)
            except Exception:
                pass
            return
        iname = name
        caret = name.endswith('_caret')
        if caret:
            iname = 'menu'
        elif name == 'recompare' and self.comparing \
                and self._cancel_shown:
            iname = 'cancel'
        idx = self._icon_idx.get(iname, -1)
        if caret and idx < 0:
            # The rebuilt set carries no menu.png (a hand-swapped tree):
            # hide the caret instead of showing an empty icon-only
            # button -- the menu button next to it still works.
            try:
                ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET,
                            name=name, prop={'vis': False})
            except Exception:
                pass
            return
        try:
            ct.button_proc(hb, ct.BTN_SET_IMAGELIST, self.h_imglist)
            ct.button_proc(hb, ct.BTN_SET_IMAGEINDEX, idx)
            if caret:
                kind = ct.BTNKIND_ICON_ONLY
            else:
                kind = self._btn_kind(cap)
            ct.button_proc(hb, ct.BTN_SET_KIND, kind)
        except Exception:
            pass
        if caret:
            # un-hide (a previous rebuild may have hidden it)
            try:
                ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET,
                            name=name, prop={'vis': True})
            except Exception:
                pass

    def _layout_buttons(self):
        """(Re)assign the captions of all buttons -- called whenever a
        caption changes (Recompare <-> Cancel swap, Ignore counter,
        show_btn_text toggle) and after the icon set was rebuilt.

        Widths and positions need NO management here: every caption
        change is followed by an 'autosize': True re-set, which re-runs
        TATButton's width computation for the new caption (measured
        with the real UI-theme font; the attached icon's width is
        counted in too), and the a_l anchor chain then re-positions
        all following controls by itself. The picture icon / kind is
        (re)applied BEFORE the caption re-set for the same reason."""
        if self.h_dlg is None:
            return
        for name, kind, icon, text in self._BTNS:
            if kind == 'sep':
                continue
            n = self.ctl.get(name)
            if n is None:
                continue
            if name == 'ignore':
                cap = self._ignore_caption()
            elif name == 'presets':
                cap = self._presets_caption()
            elif name == 'view':
                cap = self._view_caption()
            elif name == 'folders':
                cap = self._folders_caption()
            elif name == 'recompare' and self.comparing \
                    and self._cancel_shown:
                cap = self._caption('\u00d7', 'Cancel')
            else:
                cap = self._caption(icon, text)
            self._apply_button_icon(name, cap)
            try:
                # 'cap' first, 'autosize' second: the width pass must
                # measure the NEW caption.
                ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n,
                            prop={'cap': cap, 'autosize': True})
            except Exception:
                pass
        # The caret companions have no caption to refresh, but their
        # imagelist INDEX changes with every rebuild -- re-attach it.
        for name in self._MENU_BTNS:
            cname = name + '_caret'
            if cname in self.ctl:
                self._apply_button_icon(cname)
        # The row's width may have moved (Ignore counter, Cancel swap,
        # icon size change, collapse / expand flip): re-run the fit
        # decision once the anchors have settled.
        self._arm_fit_check()

    def _tooltip(self, name):
        """Tooltip of a button (hotkey hints included)."""
        if name == 'recompare':
            if self.comparing and self._cancel_shown:
                return _('Cancel the running compare')
            return _('Recompare both sides (F5)')
        if name == 'resize':
            return _('Resize the two editors to equal width')
        if name == 'swap':
            return _('Swap the compared editors (left and right)')
        if name == 'prev':
            return _('Jump to previous difference (Alt+Up)')
        if name == 'next':
            return _('Jump to next difference (Alt+Down)')
        if name == 'copy_left':
            return _('Copy current difference to the left (Alt+Left)')
        if name == 'copy_right':
            return _('Copy current difference to the right (Alt+Right)')
        if name == 'config':
            return _('Differ 2 options...')
        if name == 'ignore':
            return self._ignore_tooltip()
        if name == 'presets':
            return self._presets_tooltip()
        if name == 'view':
            return self._view_tooltip()
        if name == 'folders':
            return self._folders_tooltip()
        return ''

    def _ignore_tooltip(self):
        n, total = self._ignore_counts()
        lines = [_('Ignore options (check any combination)')]
        if n:
            on = [cap for key, cap in IGNORE_OPTS if _get_ignore_opt(key)]
            lines.append(', '.join(on))
        else:
            lines.append(_('None enabled'))
        return '\r'.join(lines)

    def _presets_tooltip(self):
        """Two-line tooltip: what the menu sets + the LIVE combination
        (read from the settings file, so it is always current -- the
        same 'know the current state without opening it' feedback the
        Ignore tooltip's enabled-list gives). The align state shows as
        fast / slow / off: the resolved value of the single
        align_by_similarity dropdown (see _align_state_text)."""
        return '\r'.join((
            _('Comparison presets: algorithm and beautify options'),
            '{}: {} / {} {} / {} {}'.format(
                _('Current'), _get_diff_algo(),
                _('Align by similarity'), _align_state_text(),
                _('Absorb trivial equal blocks'),
                _('on') if _get_absorb() else _('off')),
        ))

    def _view_tooltip(self):
        """Two-line tooltip: what the menu toggles + which of the nine
        elements are currently hidden (the same live-state feedback
        the Ignore / Presets tooltips give; the bars can change from
        CudaText's own View menu in between)."""
        state = self._view_state()
        hidden = [self._view_caption_of(key)
                  for key in state if not state[key]]
        lines = [_('Show or hide UI parts (bars, gutters, overview)')]
        if hidden:
            lines.append('{}: {}'.format(_('Hidden'), ', '.join(hidden)))
        else:
            lines.append(_('All shown'))
        return '\r'.join(lines)

    def _view_caption_of(self, key):
        """Menu caption of one view item (for tooltips / status
        feedback)."""
        for k, cap, _get, _set in _VIEW_BARS:
            if k == key:
                return cap
        for k, cap, _prop in _VIEW_GUTTERS:
            if k == key:
                return cap
        return _('Overview') if key == 'overview' else key

    def _tab_files(self):
        """(fn_left, fn_right) of this compare tab's two ORIGINALS (''
        for an original that is not a real file on disk), from the
        tab's PERSISTED registration (Command._get_orig_names -- the
        set_files / swap time record of which documents the halves
        were built from). NOT the halves' own PROP_FN: the halves are
        deliberately untitled editors (content via set_text_all, no
        temp files), so their PROP_FN is empty and the old
        halves-based read disabled the 'of these files' item forever.
        Feeds the Folders dropdown's live tooltip and that item's
        enable state; os.path.isfile is the 'is a real file' test (an
        untitled original's display title never names an existing
        file, a deleted original's path stops naming one)."""
        fn_l = fn_r = ''
        try:
            fn_l, fn_r = self.cmd._get_orig_names(self.session.tab_id)
        except Exception:
            fn_l = fn_r = ''
        if fn_l and not os.path.isfile(fn_l):
            fn_l = ''
        if fn_r and not os.path.isfile(fn_r):
            fn_r = ''
        return fn_l, fn_r

    def _folders_tooltip(self):
        """Two-line tooltip: what the menu offers + the LIVE folders of
        the two compared files (the same 'know the current state
        without opening it' feedback the Ignore / Presets / View
        tooltips give -- an untitled half says so instead of a
        folder)."""
        fn_l, fn_r = self._tab_files()
        lines = [_('Compare folders: of these files, a new pair, '
                   'or the open window')]
        if fn_l and fn_r:
            lines.append('{}: {} | {}'.format(
                _('Folders of these files'),
                os.path.dirname(fn_l), os.path.dirname(fn_r)))
        else:
            lines.append(_('One of the compared files is not saved yet'))
        return '\r'.join(lines)

    def _set_hint(self, name, hint):
        hb = self.hbtn.get(name)
        if hb:
            try:
                ct.button_proc(hb, ct.BTN_SET_HINT, hint)
            except Exception:
                pass

    def _set_enabled(self, name, en):
        """Enable/disable a button -- and its caret companion when it
        has one (the two must never disagree: a dead caret next to a
        live menu button would promise a menu it cannot open, a live
        caret next to a dead button is a lie the other way round)."""
        en = bool(en)
        for n2 in (name, name + '_caret'):
            n = self.ctl.get(n2)
            if n is None:
                continue
            try:
                ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET, index=n,
                            prop={'en': en})
            except Exception:
                pass

    def _update_nav_enabled(self):
        """Enable/disable the diff-navigation buttons: disabled while a
        compare runs (the diffmap is stale and the editors are locked
        read-only) and when the last compare found no differences
        (nothing to jump to / copy)."""
        on = (not self.comparing) and self.n_diffs > 0
        for name in ('prev', 'next', 'copy_left', 'copy_right'):
            self._set_enabled(name, on)
        self._set_enabled('ignore', not self.comparing)
        self._set_enabled('presets', not self.comparing)

    # -- compare state ------------------------------------------------------

    def set_comparing(self, running):
        """Compare kick-off: put the toolbar into the running state --
        disable the navigation buttons, rebuild the ignore dropdown
        (auto-refresh each compare start), set the status label -- but
        DELAY the Recompare -> '× Cancel' caption swap by
        _CANCEL_DELAY_MS (see _cancel_swap_tick): a click that lands in
        that window is the accidental double-click of the kick-off
        click, and it must hit a Recompare that swallows it (see
        _on_button), not a Cancel that kills the just-started compare.
        """
        self.comparing = bool(running)
        # Any state change disarms a pending swap timer first (the old
        # compare's timer must never fire into the new state).
        self._stop_cancel_swap_timer()
        self._cancel_shown = False
        if self.comparing:
            self._cancel_swap_pending = True
            try:
                ct.timer_proc(ct.TIMER_START_ONE, self._cancel_swap_tick,
                              _CANCEL_DELAY_MS)
            except Exception:
                # Timer API unavailable (should not happen in the app):
                # degrade to the old instant swap -- Cancel stays
                # clickable, the delay guard in _on_button is skipped
                # by _cancel_shown being True.
                self._cancel_swap_pending = False
                self._cancel_shown = True
        if self.h_dlg is None:
            return
        self._layout_buttons()
        self._set_hint('recompare', self._tooltip('recompare'))
        self._set_hint('ignore', self._ignore_tooltip())
        self.rebuild_ignore_menu()
        self._update_nav_enabled()
        if self.comparing:
            self.set_status(_('Comparing...'))

    def _stop_cancel_swap_timer(self):
        """Disarm the pending Cancel-swap timer (idempotent; stopping a
        timer that is not running is a harmless no-op anyway)."""
        if not self._cancel_swap_pending:
            return
        self._cancel_swap_pending = False
        try:
            ct.timer_proc(ct.TIMER_STOP, self._cancel_swap_tick,
                          _CANCEL_DELAY_MS)
        except Exception:
            pass

    def _cancel_swap_tick(self, tag=''):
        """One-shot timer callback (_CANCEL_DELAY_MS after kick-off):
        swap the Recompare caption to '× Cancel' NOW. The compare may
        already have finished before the delay ran out (small files
        compare in well under a second) -- then Recompare is the
        correct button and nothing happens here."""
        self._cancel_swap_pending = False
        if not self.comparing:
            return
        self._cancel_shown = True
        if self.h_dlg is None:
            return
        self._layout_buttons()
        self._set_hint('recompare', self._tooltip('recompare'))

    def compare_finished(self, n_diffs, cancelled=False):
        """Compare end (finished / cancelled): swap Cancel ->
        Recompare (a still-pending delayed swap is disarmed -- the
        compare ended inside the grace window, Recompare is correct),
        re-enable the navigation buttons when there are differences,
        update the status label."""
        self.comparing = False
        self._stop_cancel_swap_timer()
        self._cancel_shown = False
        self.n_diffs = int(n_diffs or 0)
        if self.h_dlg is None:
            return
        self._layout_buttons()
        self._set_hint('recompare', self._tooltip('recompare'))
        self._update_nav_enabled()
        if cancelled:
            self.set_status(_('Cancelled'))
        elif self.n_diffs == 0:
            self.set_status(_('No differences'))
        elif self.n_diffs == 1:
            self.set_status(_('1 difference'))
        else:
            self.set_status('{} {}'.format(self.n_diffs,
                                           _('differences')))

    def set_status(self, text):
        """Text of the right-side status label. The label is auto-sized,
        so the caption change alone adjusts its width; the a_r anchor
        keeps it glued to the form's right edge. The width change feeds
        the narrow-window fit check (a longer status can be what tips
        the row over the edge)."""
        self.status = text
        if self.h_dlg is None:
            return
        try:
            ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET,
                        name='status', prop={'cap': text})
        except Exception:
            pass
        self._arm_fit_check()

    def set_show_text(self, show_text):
        """Apply the differ2.toolbar.show_btn_text option: full captions
        or icons only. The narrow-window auto collapse only ever HIDES
        texts, so turning the option off also drops any active
        collapse (both states are icon-only; the flag must not survive
        as a stale 'expand when wide' promise)."""
        show_text = bool(show_text)
        if self.show_text == show_text:
            return
        self.show_text = show_text
        if not show_text:
            self._narrow = False
        if self.h_dlg is None:
            return
        self._layout_buttons()

    # -- narrow-window auto icon-only mode --------------------------------

    def _on_form_resize(self, id_dlg, id_ctl=-1, data=''):
        """Live on_resize callback of the docked form (cudatext.py's
        proxy calls it with the form handle and id_ctl=-1): the editor
        parent resized the toolbar -- the debounce entry of the fit
        check. Fires a lot during an interactive drag; the armed
        one-shot timer restarts on every call, so the check runs
        once, after the LAST event."""
        self._arm_fit_check()

    def _arm_fit_check(self):
        """(Re)arm the debounced fit check: Command._toolbar_fit_timer
        routes back to this toolbar's _fit_check 100ms later. The
        timer string carries only the tab id (TIMER_STR_SEP rule: no
        '|' inside a timer info -- see __init__.py). Restarting an
        armed one-shot is CudaText's own TIMER_START_ONE semantics
        (the running timer is found by its callback string and
        re-enabled), so this is a free debounce."""
        if self.h_dlg is None:
            return
        try:
            callback = ('module=cuda_differ2;cmd=_toolbar_fit_timer;'
                        'info={};'.format(self.tab_id_str))
            ct.timer_proc(ct.TIMER_START_ONE, callback, _FIT_CHECK_MS)
        except Exception:
            pass

    def _needed_width(self):
        """Width the toolbar needs in its CURRENT layout: the right end
        of the button row (the 'config' button is the last chained
        control; its x+w is the natural row end -- the anchor chain
        never clips, so the value is honest even when the row already
        overflows) plus the auto-sized status label and its right
        margin -- the label must not overlap the last button."""
        row_end = 0
        label_w = 0
        try:
            p = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_GET, name='config')
            if p:
                row_end = int(p.get('x', 0) or 0) + int(p.get('w', 0) or 0)
            p = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_GET, name='status')
            if p:
                label_w = int(p.get('w', 0) or 0)
        except Exception:
            return None
        return row_end + label_w + _STATUS_SP_R

    def _fit_check(self):
        """THE fit decision (runs on the debounced timer, when resize /
        layout storms have settled and the anchor chain has re-flowed):
        compare the toolbar's width with the width the TEXT row needs
        and flip the narrow icon-only mode accordingly. Only runs while
        picture icons exist AND the show_btn_text option is on -- the
        glyph fallback has no icon-only mode (the glyphs are the
        captions) and an option-off toolbar is icon-only already. The
        text row's needed width is measured fresh in text mode and
        CACHED while collapsed (the icon row is much narrower; the
        expand test must compare against the text row it would return
        to), with the _FIT_HYST hysteresis against boundary flapping."""
        if self.h_dlg is None or self._in_fit:
            return
        if not self._icons_ok or not self.show_text:
            if self._narrow:
                self._narrow = False
                self._layout_buttons()
            return
        try:
            self._in_fit = True
            try:
                props = ct.dlg_proc(self.h_dlg, ct.DLG_PROP_GET)
                avail = int((props or {}).get('w', 0) or 0)
            except Exception:
                avail = 0
            if avail <= 0:
                return
            if self._narrow:
                needed = self._text_row_w
            else:
                needed = self._needed_width()
                if needed is not None:
                    self._text_row_w = needed
            if needed is None:
                return
            if not self._narrow and avail < needed:
                # Too narrow for the text row: collapse to icons.
                self._narrow = True
                self._layout_buttons()
            elif self._narrow and avail >= needed + _scaled(_FIT_HYST):
                # Room again: back to texts, then re-measure the row
                # with the restored (fresh) captions on the next tick.
                self._narrow = False
                self._layout_buttons()
                self._arm_fit_check()
        finally:
            self._in_fit = False

    def apply_icon_options(self):
        """Apply the differ2.toolbar.icon_theme / icon_size options
        after a config change: rebuild the imagelist when the wanted
        set or size moved, and relayout the buttons (the new icons may
        be a different pixel size). A toolbar still on the fallback
        glyphs just retries _setup_icons -- when the tree is missing
        that stays a cheap no-op."""
        if self.h_dlg is None:
            return
        want_set = self._wanted_set()
        want_size = self._wanted_size()
        if self._icons_ok and want_set == self._icon_set \
                and want_size == self._icon_size:
            return
        self._setup_icons(set_name=want_set, size=want_size)
        self._layout_buttons()

    def apply_theme(self):
        """Re-apply the toolbar colors for the (possibly switched) UI
        theme: background EdTextBg, status-label font EdTextFont,
        border-line color SplitMain -- and the picture icons: with the
        automatic set pick a theme switch can move the background
        across the dark/light midpoint, and a stale icon set on the
        new background is the black-on-black bug again (light glyphs
        on a light theme read as nothing at all). All must be re-read
        together."""
        if self.h_dlg is None:
            return
        bgcolor = _ed_text_bg()
        fontcolor = _ed_text_font()
        try:
            if bgcolor is not None and fontcolor is not None:
                ct.dlg_proc(self.h_dlg, ct.DLG_PROP_SET,
                            prop={'color': bgcolor})
                ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET,
                            name='status', prop={'color': bgcolor,
                                                 'font_color': fontcolor})
            # the border line's color is a plain prop re-set (the strip
            # is a 'panel': the color lives in the prop dict, no handle)
            ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_SET,
                        name='brd', prop={'color': _split_color()})
        except Exception:
            pass
        # Picture icons: rebuild the imagelist when the (possibly new)
        # background luminance lands on the other side of the midpoint.
        # A pinned set (icon_theme != 'auto') never moves here -- the
        # user asked for it, it stays.
        if self._icons_ok:
            want = self._wanted_set()
            if want != self._icon_set:
                self._setup_icons(set_name=want)
                self._layout_buttons()

    # -- ignore popup menu --------------------------------------------------

    def rebuild_ignore_menu(self):
        """(Re)build the Ignore dropdown. Called on every compare start
        so the checkmarks always mirror the settings file (the config
        dialog and the tab context menu write there too).

        Python-algorithm guard: while a pure-Python algorithm is the
        effective one the DIFF_IGN_* flags do nothing (Python compares
        strictly), so the items disable themselves and an explanatory
        disabled item heads the menu -- the toolbar twin of the tab
        context menu hiding its ignore items.

        The whole body is guarded: a failure here must never propagate
        into the compare flow that called it."""
        if self.h_dlg is None:
            return
        try:
            self._rebuild_ignore_menu_inner()
        except Exception:
            pass

    def _rebuild_ignore_menu_inner(self):
        if self.h_menu is None:
            self.h_menu = ct.menu_proc(0, ct.MENU_CREATE)
        ct.menu_proc(self.h_menu, ct.MENU_CLEAR)
        self.menu_items = {}
        self.menu_guard_item = None

        use_native = True
        try:
            use_native = bool(self.cmd._resolve_algorithm()[1])
        except Exception:
            use_native = True

        if not use_native:
            # Explanatory disabled item (like the tab menu's guard).
            mi = ct.menu_proc(
                self.h_menu, ct.MENU_ADD,
                caption=_('Ignore options need a native algorithm '
                          '(current one is pure-Python)'))
            try:
                ct.menu_proc(mi, ct.MENU_SET_ENABLED, command=False)
            except Exception:
                pass
            self.menu_guard_item = mi
            ct.menu_proc(self.h_menu, ct.MENU_ADD, caption='-')
            for key, caption in IGNORE_OPTS:
                mi = ct.menu_proc(
                    self.h_menu, ct.MENU_ADD, caption=caption)
                try:
                    ct.menu_proc(mi, ct.MENU_SET_ENABLED, command=False)
                    ct.menu_proc(mi, ct.MENU_SET_CHECKED,
                                 command=_get_ignore_opt(key))
                except Exception:
                    pass
                self.menu_items[key] = mi
            return

        for key, caption in IGNORE_OPTS:
            mi = ct.menu_proc(
                self.h_menu, ct.MENU_ADD,
                caption=caption,
                # 'cmd=' form (a Command method): CudaText passes this
                # form's info to the method as the RAW string, so the
                # '<tab id>|<key>' payload survives. (The 'func=' form
                # would parse the info value and an unquoted value like
                # '501|ignore_case' arrives as None -> the click did
                # nothing in the first toolbar version.)
                command='module=cuda_differ2;cmd=toolbar_menu_ignore;'
                        'info={}|{};'.format(self.tab_id_str, key))
            try:
                ct.menu_proc(mi, ct.MENU_SET_CHECKED,
                             command=_get_ignore_opt(key))
            except Exception:
                pass
            self.menu_items[key] = mi

        # 'Uncheck all options' after a separator, at the end.
        ct.menu_proc(self.h_menu, ct.MENU_ADD, caption='-')
        mi = ct.menu_proc(
            self.h_menu, ct.MENU_ADD,
            caption=_('Uncheck all options'),
            command='module=cuda_differ2;cmd=toolbar_menu_ignore;'
                    'info={}|*;'.format(self.tab_id_str))
        self.menu_items['*'] = mi

        self._set_hint('ignore', self._ignore_tooltip())

    def popup_ignore_menu(self):
        """Show the Ignore dropdown right under its button."""
        if self.h_menu is None or self.h_dlg is None:
            return
        try:
            props = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_GET,
                                name='ignore')
            x = int(props.get('x', 0))
            y = int(props.get('y', 0)) + int(props.get('h', 0))
            sx, sy = ct.dlg_proc(self.h_dlg, ct.DLG_COORD_LOCAL_TO_SCREEN,
                                 index=x, index2=y)
            ct.menu_proc(self.h_menu, ct.MENU_SHOW, command=(sx, sy))
        except Exception:
            # Fallback: show at the mouse cursor.
            try:
                ct.menu_proc(self.h_menu, ct.MENU_SHOW, command='')
            except Exception:
                pass

    def on_menu_action(self, action):
        """Menu item executed: 'key' toggles one option, '*' unchecks
        all. Persists the change, updates the checkmark / caption /
        tooltip, then re-runs the compare on a 100ms timer (the
        menu-close-first convention) so the new flags apply at once."""
        if action == '*':
            for key, _cap in IGNORE_OPTS:
                _set_ignore_opt(key, False)
                mi = self.menu_items.get(key)
                if mi:
                    try:
                        ct.menu_proc(mi, ct.MENU_SET_CHECKED, command=False)
                    except Exception:
                        pass
            self._layout_buttons()
            self._set_hint('ignore', self._ignore_tooltip())
            try:
                ct.msg_status(_('Differ 2: all ignore options disabled'))
            except Exception:
                pass
            self._schedule_refresh()
            return
        key = action
        old = _get_ignore_opt(key)
        _set_ignore_opt(key, not old)
        mi = self.menu_items.get(key)
        if mi:
            try:
                ct.menu_proc(mi, ct.MENU_SET_CHECKED, command=not old)
            except Exception:
                pass
        self._layout_buttons()
        self._set_hint('ignore', self._ignore_tooltip())
        captions = dict(IGNORE_OPTS)
        try:
            ct.msg_status('{}: {} -- {}'.format(
                _('Differ 2 ignore option'), captions.get(key, key),
                _('enabled') if not old else _('disabled')))
        except Exception:
            pass
        self._schedule_refresh()

    def _schedule_refresh(self):
        """Recompare THIS tab 100ms later (Command._toolbar_refresh_timer
        resolves the editor by tab id; the timer string command carries
        the tab id)."""
        try:
            callback = ('module=cuda_differ2;cmd=_toolbar_refresh_timer;'
                        'info={};'.format(self.tab_id_str))
            ct.timer_proc(ct.TIMER_START_ONE, callback, 100)
        except Exception:
            pass

    # -- presets popup menu -------------------------------------------------

    def rebuild_preset_menu(self):
        """(Re)build the Presets dropdown: the two mutually exclusive
        preset COMBINATIONS ("Preset 1: Fastest comparison - Myers,
        Fast Align On, Absorb Off" / "Preset 2: Better readability
        (slower) - Histogram, Fast Align On, Absorb On" -- the
        original preset form, each an exact combination of the
        three settings, with only the align / absorb values updated
        for the new dropdown world: BOTH presets align with the
        FAST method), a separator, the three algorithms (also
        mutually exclusive: Native Histogram / Native Myers /
        Hybrid Python), a separator, the TWO radio choices of the
        SINGLE align_by_similarity dropdown config ("Method 1 -
        fast" / "Method 2 - slow" -- there is no "off" item:
        re-clicking the checked method turns it off), a separator,
        and the independent "Absorb trivial equal blocks" toggle.

        The presets, the algorithms and the align-method choices are
        RADIO items (a dot, not a checkmark -- see _PRESET_RADIO);
        the absorb toggle is a plain checkable item (an independent
        feature).

        The checkmarks are DERIVED from the settings file -- a preset
        is an EXACT combination of three settings: Myers + align
        fast + absorb off checks Preset 1, Histogram + align fast +
        absorb on checks Preset 2, any other combination (align off
        or slow, the Hybrid algorithm, included) checks NEITHER.
        Called on every open (popup_preset_menu); the whole body is
        guarded like the ignore twin's."""
        if self.h_dlg is None:
            return
        try:
            self._rebuild_preset_menu_inner()
        except Exception:
            pass

    def _rebuild_preset_menu_inner(self):
        if self.h_pmenu is None:
            self.h_pmenu = ct.menu_proc(0, ct.MENU_CREATE)
        ct.menu_proc(self.h_pmenu, ct.MENU_CLEAR)

        algo = _get_diff_algo()
        # The RESOLVED value of the single align_by_similarity
        # dropdown: exactly one of 'off' / 'fast' / 'slow', always --
        # when NEITHER method item shows a checkmark, the stored
        # value simply IS 'off' (that is why the menu needs no
        # explicit off item).
        align_mode = get_align_mode()
        absorb = _get_absorb()
        marks = {
            # a preset is an EXACT combination of the three settings
            # -- anything else (a custom pick of algorithm + methods)
            # unchecks BOTH, so a custom selection is visible at a
            # glance
            'preset1': algo == _ALGO_MYERS and align_mode == ALIGN_FAST
                       and not absorb,
            'preset2': algo == _ALGO_HIST and align_mode == ALIGN_FAST
                       and absorb,
            'algo1': algo == _ALGO_HIST,
            'algo2': algo == _ALGO_MYERS,
            'algo3': algo == _ALGO_HYBRID,
            'beautify_fast': align_mode == ALIGN_FAST,
            'beautify_slow': align_mode == ALIGN_SLOW,
            'absorb': absorb,
        }
        for key, caption in _PRESET_ITEMS:
            if key is None:
                ct.menu_proc(self.h_pmenu, ct.MENU_ADD, caption='-')
                continue
            mi = ct.menu_proc(
                self.h_pmenu, ct.MENU_ADD,
                caption=caption,
                # 'cmd=' form (a Command method): CudaText passes this
                # form's info to the method as the RAW string, so the
                # '<tab id>|<preset key>' payload survives -- the same
                # convention as the ignore items.
                command='module=cuda_differ2;cmd=toolbar_menu_preset;'
                        'info={}|{};'.format(self.tab_id_str, key))
            try:
                ct.menu_proc(mi, ct.MENU_SET_CHECKED, command=marks[key])
                group = _PRESET_RADIO.get(key)
                if group is not None:
                    # mutually exclusive pair -> radio item (dot mark,
                    # click auto-unchecks the group's other item)
                    ct.menu_proc(mi, ct.MENU_SET_RADIOITEM, command=True)
                    ct.menu_proc(mi, ct.MENU_SET_GROUPINDEX, index=group)
            except Exception:
                pass

    def popup_preset_menu(self):
        """Show the Presets dropdown right under its button. The menu is
        rebuilt FIRST, so the checkmarks always mirror the settings
        file (config-dialog / tab-menu / hand-edited changes included)
        -- the preset checkmarks are re-derived on every open."""
        if self.h_dlg is None:
            return
        self.rebuild_preset_menu()
        if self.h_pmenu is None:
            return
        try:
            props = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_GET,
                                name='presets')
            x = int(props.get('x', 0))
            y = int(props.get('y', 0)) + int(props.get('h', 0))
            sx, sy = ct.dlg_proc(self.h_dlg, ct.DLG_COORD_LOCAL_TO_SCREEN,
                                 index=x, index2=y)
            ct.menu_proc(self.h_pmenu, ct.MENU_SHOW, command=(sx, sy))
        except Exception:
            # Fallback: show at the mouse cursor.
            try:
                ct.menu_proc(self.h_pmenu, ct.MENU_SHOW, command='')
            except Exception:
                pass

    def on_preset_action(self, action):
        """Preset-dropdown item executed: persist the value(s) to
        settings/cuda_differ2.json (the config dialog's store), then
        re-compare this tab on the 100ms timer (the menu-close-first
        convention) -- refresh_compare re-reads the settings file (its
        mtime cache), so this very refresh already uses the new
        algorithm / align mode. A preset click writes ALL THREE
        settings of its exact combination (the algorithm, Align by
        similarity, Absorb trivial equal blocks -- the original
        preset behavior, with the updated align / absorb values):
        Preset 1 = Myers + align fast + absorb off,
        Preset 2 = Histogram + align fast + absorb on.
        The align items write the SINGLE dropdown value through
        set_align_mode -- one key, so the methods are exclusive by
        construction (nothing to keep in step) -- and clicking the
        currently-checked Method 1/2 item turns it back off (off =
        algo-faithful; that is why the menu needs no explicit "off"
        item). The menu is rebuilt on every open, so the new
        checkmarks show up the next time it pops."""
        algo = None          # None = leave the option unchanged
        align_mode = None
        absorb = None
        if action == 'preset1':
            # The exact Preset 1 combination (the original "Fastest
            # comparison" preset with align on -- the FAST method).
            algo, align_mode, absorb = _ALGO_MYERS, ALIGN_FAST, False
        elif action == 'preset2':
            # The exact Preset 2 combination (the original "Better
            # readability (slower)" preset with the FAST align
            # method and absorb on).
            algo, align_mode, absorb = _ALGO_HIST, ALIGN_FAST, True
        elif action == 'algo1':
            algo = _ALGO_HIST
        elif action == 'algo2':
            algo = _ALGO_MYERS
        elif action == 'algo3':
            algo = _ALGO_HYBRID
        elif action == 'beautify_fast':
            # Toggle Method 1 (fast): off when it is already the
            # current mode (the old toggle-off workflow), on when
            # anything else (off / the slow method) is current.
            align_mode = ALIGN_OFF if get_align_mode() == ALIGN_FAST \
                else ALIGN_FAST
        elif action == 'beautify_slow':
            # Toggle Method 2 (slow): off when it is already the
            # current mode, on when anything else is current.
            align_mode = ALIGN_OFF if get_align_mode() == ALIGN_SLOW \
                else ALIGN_SLOW
        elif action == 'absorb':
            absorb = not _get_absorb()
        else:
            return
        if algo is not None:
            _set_diff_algo(algo)
        if align_mode is not None:
            set_align_mode(align_mode)
        if absorb is not None:
            _set_absorb(absorb)
        try:
            ct.msg_status('{}: {} / {} {} / {} {}'.format(
                _('Differ 2 presets'), _get_diff_algo(),
                _('Align by similarity'), _align_state_text(),
                _('Absorb trivial equal blocks'),
                _('on') if _get_absorb() else _('off')))
        except Exception:
            pass
        self._schedule_refresh()

    # -- view popup menu ----------------------------------------------------

    def rebuild_view_menu(self):
        """(Re)build the View dropdown: 'Hide all' / 'Show all', a
        separator, then the checkable items (the six app bars, the two
        gutter columns, the overview panel). REBUILT on every open so
        the checkmarks always mirror the live state -- the bars can be
        toggled from CudaText's own View menu too. The whole body is
        guarded like the ignore / presets twins."""
        if self.h_dlg is None:
            return
        try:
            self._rebuild_view_menu_inner()
        except Exception:
            pass

    def _rebuild_view_menu_inner(self):
        if self.h_vmenu is None:
            self.h_vmenu = ct.menu_proc(0, ct.MENU_CREATE)
        ct.menu_proc(self.h_vmenu, ct.MENU_CLEAR)

        state = self._view_state()

        def _add(key, caption, checked):
            # 'cmd=' form (a Command method): CudaText passes this
            # form's info to the method as the RAW string, so the
            # '<tab id>|<view key>' payload survives -- the same
            # convention as the ignore / preset items.
            mi = ct.menu_proc(
                self.h_vmenu, ct.MENU_ADD,
                caption=caption,
                command='module=cuda_differ2;cmd=toolbar_menu_view;'
                        'info={}|{};'.format(self.tab_id_str, key))
            if checked is not None:
                try:
                    ct.menu_proc(mi, ct.MENU_SET_CHECKED,
                                 command=checked)
                except Exception:
                    pass

        _add('hide_all', _('Hide all'), None)
        _add('show_all', _('Show all'), None)
        ct.menu_proc(self.h_vmenu, ct.MENU_ADD, caption='-')
        for key, caption, _get, _set in _VIEW_BARS:
            _add(key, caption, state[key])
        for key, caption, _prop in _VIEW_GUTTERS:
            _add(key, caption, state[key])
        _add('overview', _('Overview'), state['overview'])

    def popup_view_menu(self):
        """Show the View dropdown right under its button. The menu is
        rebuilt FIRST, so the checkmarks always mirror the live
        visibility state (CudaText's own View menu can change the bars
        in between) -- the view twin of the presets popup."""
        if self.h_dlg is None:
            return
        self.rebuild_view_menu()
        if self.h_vmenu is None:
            return
        try:
            props = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_GET,
                                name='view')
            x = int(props.get('x', 0))
            y = int(props.get('y', 0)) + int(props.get('h', 0))
            sx, sy = ct.dlg_proc(self.h_dlg, ct.DLG_COORD_LOCAL_TO_SCREEN,
                                 index=x, index2=y)
            ct.menu_proc(self.h_vmenu, ct.MENU_SHOW, command=(sx, sy))
        except Exception:
            # Fallback: show at the mouse cursor.
            try:
                ct.menu_proc(self.h_vmenu, ct.MENU_SHOW, command='')
            except Exception:
                pass

    def _view_state(self):
        """Live visibility of every checkable View item (dict, menu
        key -> bool): the bars through their PROC_SHOW_* GET pairs, the
        gutter columns from the tab's left half (both halves are always
        set together, so one IS the pair's state), the overview from
        the settings file."""
        state = {}
        for key, _cap, get_id, _set in _VIEW_BARS:
            try:
                state[key] = bool(ct.app_proc(get_id, ''))
            except Exception:
                state[key] = True
        for key, _cap, prop in _VIEW_GUTTERS:
            try:
                state[key] = bool(self.a_ed.get_prop(prop))
            except Exception:
                state[key] = True
        state['overview'] = _get_overview_opt()
        return state

    def _tab_editors(self):
        """Both halves of this compare tab (the toolbar's a_ed + its
        secondary): the gutter column toggles must hit both sides or
        the compare view goes asymmetric."""
        eds = [self.a_ed]
        try:
            h2 = self.a_ed.get_prop(ct.PROP_HANDLE_SECONDARY)
            if h2:
                eds.append(ct.Editor(h2))
        except Exception:
            pass
        return eds

    def _set_view_item(self, key, val):
        """Apply ONE view item's visibility ('val' = the new shown
        state). Returns True when the change needs the 100ms
        re-compare (only the overview: its panel is created /
        destroyed by the refresh)."""
        for k, _cap, _get, set_id in _VIEW_BARS:
            if k == key:
                ct.app_proc(set_id, bool(val))
                return False
        for k, _cap, prop in _VIEW_GUTTERS:
            if k == key:
                for e in self._tab_editors():
                    e.set_prop(prop, bool(val))
                return False
        if key == 'overview':
            _set_overview_opt(bool(val))
            return True
        return False

    def on_view_action(self, action):
        """View-dropdown item executed: 'hide_all' flips EVERY item at
        once, 'show_all' every item EXCEPT the side and bottom panels
        (_SHOW_ALL_SKIP: a bulk show must not force those docked tool
        windows open, so their items stay unchecked); any other key
        toggles ONE element. The overview writes
        differ2.micromap.enable_overview (the config dialog's store)
        and re-compares this tab on the
        100ms timer -- the refresh creates or destroys the panel,
        exactly like the preset items; hide/show-all schedule the same
        refresh once for their overview part. The menu is rebuilt on
        every open, so the new checkmarks show up the next time it
        pops; unknown keys are safe no-ops."""
        if action in ('hide_all', 'show_all'):
            show = (action == 'show_all')
            for key in self._view_state():
                if show and key in _SHOW_ALL_SKIP:
                    continue    # side/bottom panels: not force-shown
                self._set_view_item(key, show)
            try:
                ct.msg_status(
                    _('Differ 2: all view items {}').format(
                        _('shown') if show else _('hidden')))
            except Exception:
                pass
            self._schedule_refresh()
            self._set_hint('view', self._view_tooltip())
            return
        state = self._view_state()
        if action not in state:
            return
        val = not state[action]
        if self._set_view_item(action, val):
            self._schedule_refresh()
        try:
            ct.msg_status('{}: {} -- {}'.format(
                _('Differ 2 view'), self._view_caption_of(action),
                _('shown') if val else _('hidden')))
        except Exception:
            pass
        self._set_hint('view', self._view_tooltip())

    # -- folders popup menu ------------------------------------------------

    def rebuild_folders_menu(self):
        """(Re)build the Folders dropdown: the folder-compare hub with
        its three items -- 'Compare folders of these files' (a NEW
        folder-compare window for the parent folders of the two files
        this tab compares; DISABLED while either ORIGINAL is not a
        real file on disk, since an unsaved document has no folder --
        _tab_files, the persisted-registration read), 'Compare two
        new folders...' (the folder picker) and 'Open compare folders
        window' (focus the most recent folder-compare window / reopen
        the last picked pair / the picker as the last resort). All
        three are plain actions (no checkmarks); REBUILT on every
        open so the enable state is always fresh. The whole body is
        guarded like the ignore / presets / view twins."""
        if self.h_dlg is None:
            return
        try:
            self._rebuild_folders_menu_inner()
        except Exception:
            pass

    def _rebuild_folders_menu_inner(self):
        if self.h_fmenu is None:
            self.h_fmenu = ct.menu_proc(0, ct.MENU_CREATE)
        ct.menu_proc(self.h_fmenu, ct.MENU_CLEAR)

        fn_l, fn_r = self._tab_files()
        for key, caption in _FOLDER_ITEMS:
            mi = ct.menu_proc(
                self.h_fmenu, ct.MENU_ADD,
                caption=caption,
                # 'cmd=' form (a Command method): CudaText passes this
                # form's info to the method as the RAW string, so the
                # '<tab id>|<folder key>' payload survives -- the same
                # convention as the ignore / preset / view items.
                command='module=cuda_differ2;cmd=toolbar_menu_dirs;'
                        'info={}|{};'.format(self.tab_id_str, key))
            if key == 'of_files' and not (fn_l and fn_r):
                try:
                    ct.menu_proc(mi, ct.MENU_SET_ENABLED, command=False)
                except Exception:
                    pass

    def popup_folders_menu(self):
        """Show the Folders dropdown right under its button. The menu is
        rebuilt FIRST, so the 'of these files' item's enable state
        always mirrors the tab's originals (a compare of two saved
        files has it enabled -- the old halves-based read kept it
        disabled because the halves are untitled)."""
        if self.h_dlg is None:
            return
        self.rebuild_folders_menu()
        if self.h_fmenu is None:
            return
        try:
            props = ct.dlg_proc(self.h_dlg, ct.DLG_CTL_PROP_GET,
                                name='folders')
            x = int(props.get('x', 0))
            y = int(props.get('y', 0)) + int(props.get('h', 0))
            sx, sy = ct.dlg_proc(self.h_dlg, ct.DLG_COORD_LOCAL_TO_SCREEN,
                                 index=x, index2=y)
            ct.menu_proc(self.h_fmenu, ct.MENU_SHOW, command=(sx, sy))
        except Exception:
            # Fallback: show at the mouse cursor.
            try:
                ct.menu_proc(self.h_fmenu, ct.MENU_SHOW, command='')
            except Exception:
                pass

    def on_folders_action(self, action):
        """Folders-dropdown item executed: schedule the action on the
        100ms menu-close-first timer (Command._toolbar_dirs_timer does
        the work: 'of_files' compares the parent folders of this tab's
        two files, 'two_new' opens the picker -- a MODAL dialog that
        must not open while the dropdown is still closing --, 'window'
        focuses / reopens the folder-compare window). The same
        convention as the tabmenu_* callbacks and the toolbar's own
        _schedule_refresh.

        The TIMER payload joins the tab id and the folder key with
        '::' (see TIMER_STR_SEP in __init__.py): a '|' inside a timer
        callback's info is cut at CudaText's own callback|tag splitter
        and the whole callback dies as 'Bad API callback'."""
        try:
            callback = ('module=cuda_differ2;cmd=_toolbar_dirs_timer;'
                        'info={}::{};'.format(self.tab_id_str, action))
            ct.timer_proc(ct.TIMER_START_ONE, callback, 100)
        except Exception:
            pass

    # -- button actions -----------------------------------------------------

    def _on_button(self, id_dlg, id_ctl, data='', info=''):
        """on_change dispatcher of all toolbar buttons (id_ctl is the
        control index). Caret companion buttons route to their menu
        button's action -- clicking either opens the same dropdown."""
        name = None
        for key, n in self.ctl.items():
            if n == id_ctl:
                name = key
                break
        if name is None:
            return
        if name.endswith('_caret'):
            name = name[:-len('_caret')]
        try:
            if name == 'recompare':
                if self.comparing:
                    if not self._cancel_shown:
                        # Grace window (see set_comparing / _CANCEL_DELAY_MS):
                        # this click landed within the Cancel-swap delay of
                        # the kick-off click -- the accidental double-click
                        # (or a late button-up). Swallow it: the compare just
                        # started must survive, and starting another one on
                        # top of the running job is not sensible either. A
                        # genuine cancel is available one second later (or
                        # immediately via the 'Cancel compare' command).
                        return
                    self.cmd.cancel_compare(self.a_ed)
                else:
                    self.cmd.refresh_compare(self.a_ed)
            elif name == 'resize':
                self.cmd.resize_equal_width(self.a_ed)
            elif name == 'swap':
                self.cmd.swap_view(self.a_ed)
            elif name == 'prev':
                self.cmd.jump_prev()
            elif name == 'next':
                self.cmd.jump_next()
            elif name == 'copy_left':
                self.cmd.copy_left()
            elif name == 'copy_right':
                self.cmd.copy_right()
            elif name == 'ignore':
                self.popup_ignore_menu()
            elif name == 'presets':
                self.popup_preset_menu()
            elif name == 'view':
                self.popup_view_menu()
            elif name == 'folders':
                self.popup_folders_menu()
            elif name == 'config':
                self.cmd.change_config()
        except Exception:
            import traceback
            traceback.print_exc()

    # -- teardown -----------------------------------------------------------

    def destroy(self):
        """Free the form (+ its live on_change callbacks -- DLG_FREE
        cleans them) and empty the popup menus. No DLG_UNDOCK: see the
        comment below.

        The popup menu is NOT disposed with menu_proc(MENU_REMOVE):
        that Pascal handler frees the menu ITEM it is given -- meant
        for items ADDED to an existing menu -- and our handle IS the
        popup's ROOT item. Freeing it would leave the TPopupMenu (owned
        by CudaText's main form) with a dangling root for the rest of
        the app's life, crashing/corrupting the exit that eventually
        frees it. MENU_CLEAR frees all items + their callback data and
        is the safe way to empty the menu; the emptied popup itself is
        owned by the main form and dies safely with the app (the same
        convention CudaText's own plugins use for their popups)."""
        # Disarm the pending Cancel-swap timer FIRST: a one-shot that
        # fires after the form is freed would call _cancel_swap_tick on
        # a destroyed toolbar (harmless today -- it checks h_dlg -- but
        # the timer also holds a bound-method reference to this object
        # that must not outlive its session).
        self._stop_cancel_swap_timer()
        h = self.h_dlg
        self.h_dlg = None
        if h is not None:
            # NO DLG_UNDOCK before DLG_FREE. DLG_UNDOCK does
            # Form.Parent := nil, and LCL's TCustomForm.SetParent
            # immediately allocates a native floating top-level window
            # for a form unparented while Visible
            #   if (Parent = nil) and Visible then HandleNeeded;
            # the window manager maps that window -- the whole screen
            # repaints (the flash that dismissed open menus on tab
            # close) -- and DLG_FREE then hides and frees it a few
            # microseconds later. Freeing the DOCKED form directly is
            # safe and flash-free: DLG_FREE hides it while it is still
            # a child of the (hidden) editor frame -- no screen change
            # -- and TControl.Destroy unparents it itself with
            # Visible=False, so HandleNeeded never runs and no
            # floating window is ever created.
            try:
                ct.dlg_proc(h, ct.DLG_FREE)
            except Exception:
                pass
        if self.h_menu is not None:
            try:
                ct.menu_proc(self.h_menu, ct.MENU_CLEAR)
            except Exception:
                pass
            self.h_menu = None
        if self.h_pmenu is not None:
            try:
                ct.menu_proc(self.h_pmenu, ct.MENU_CLEAR)
            except Exception:
                pass
            self.h_pmenu = None
        if self.h_vmenu is not None:
            try:
                ct.menu_proc(self.h_vmenu, ct.MENU_CLEAR)
            except Exception:
                pass
            self.h_vmenu = None
        if self.h_fmenu is not None:
            try:
                ct.menu_proc(self.h_fmenu, ct.MENU_CLEAR)
            except Exception:
                pass
            self.h_fmenu = None
        self.ctl = {}
        self.hbtn = {}
        self.menu_items = {}
        self.menu_guard_item = None
        # The imagelist is OWNED by the (now freed) form and dies with
        # it -- compare_dir's row icons use the same pattern. Only the
        # bookkeeping is cleared here.
        self.h_imglist = None
        self._icon_idx = {}
        self._icon_set = None
        self._icon_size = None
        self._icons_ok = False

    def is_created(self):
        return self.h_dlg is not None


# ---------------------------------------------------------------------------
# Module-level registry and entry points (used by cuda_differ2/__init__).
# ---------------------------------------------------------------------------

_TOOLBARS = {}  # str(PROP_TAB_ID) -> CompareToolbar


def get_for(session):
    """The toolbar of a compare tab's session, or None."""
    if session is None:
        return None
    return _TOOLBARS.get(session.tab_id_str)


def fit_check_for(tab_id_str):
    """Run the narrow-window fit decision of ONE compare tab's toolbar
    (the Command._toolbar_fit_timer routing target; the timer fires
    100ms after the last resize / layout change). Unknown tab (closed
    since the timer was armed) or a destroyed toolbar is a no-op."""
    tb = _TOOLBARS.get(str(tab_id_str))
    if tb is not None and tb.is_created():
        try:
            tb._fit_check()
        except Exception:
            pass


def ensure_for_session(cmd, session, a_ed=None):
    """Create the toolbar of a compare tab if the option is on and it
    does not exist yet. 'a_ed' (any editor of the tab) is optional --
    resolved by tab id when omitted. A toolbar that exists while the
    option is off (hand-edited JSON, no config-dialog OK to sync_all)
    is destroyed here. Returns the toolbar or None."""
    if session is None:
        return None
    tb = _TOOLBARS.get(session.tab_id_str)
    if tb is not None and tb.is_created():
        if not cmd.cfg.get('show_toolbar', True):
            destroy_for(session.tab_id_str)
            return None
        return tb
    if not cmd.cfg.get('show_toolbar', True):
        return None
    if a_ed is None:
        try:
            a_ed = cmd._editor_by_tab_id(session.tab_id)
        except Exception:
            a_ed = None
    if a_ed is None:
        return None
    try:
        tb = CompareToolbar(cmd, session, a_ed)
        if not tb.create():
            return None
    except Exception as ex:
        print('Differ 2 toolbar: failed to create: {}'.format(ex))
        return None
    _TOOLBARS[session.tab_id_str] = tb
    return tb


def destroy_for(tab_id_str):
    """Destroy the toolbar of a compare tab (tab closed / option
    turned off)."""
    tb = _TOOLBARS.pop(str(tab_id_str), None)
    if tb is not None:
        tb.destroy()


def on_compare_start(cmd, session):
    """Compare kick-off hook: swap Recompare -> Cancel, rebuild the
    ignore dropdown (auto-refresh each compare start), status label
    'Comparing...'."""
    tb = get_for(session)
    if tb is not None:
        tb.set_comparing(True)


def on_compare_end(cmd, session, n_diffs=None, cancelled=False):
    """Compare end hook (finished / cancelled): swap Cancel ->
    Recompare, refresh the navigation buttons and the status label
    ('N differences' / 'No differences' / 'Cancelled')."""
    tb = get_for(session)
    if tb is None:
        return
    if n_diffs is None:
        diff = session.diff if session is not None else None
        diffmap = getattr(diff, 'diffmap', None)
        n_diffs = len(diffmap) if diffmap else 0
    tb.compare_finished(n_diffs, cancelled)


def sync_ignore_state(cmd):
    """Refresh the Ignore captions/tooltips of every toolbar after an
    ignore option was changed elsewhere (tab context menu, config
    dialog) -- two-way sync with zero bookkeeping."""
    for tb in list(_TOOLBARS.values()):
        if tb.is_created():
            tb._layout_buttons()
            tb._set_hint('ignore', tb._ignore_tooltip())


def update_theme_all():
    """Re-apply the toolbar background colors after a UI theme switch
    (on_state APPSTATE_THEME_UI)."""
    for tb in list(_TOOLBARS.values()):
        tb.apply_theme()


def sync_all(cmd):
    """Make the set of toolbars match the current options after a config
    change: destroy toolbars of closed tabs or when show_toolbar is off,
    apply show_btn_text / icon_theme / icon_size and refresh the Ignore
    menus of the surviving ones, and create the missing toolbar of the
    FOCUSED compare tab only. The toolbars of unvisited compare tabs
    stay lazy (each is created on its first activation -- on_tab_change
    / on_focus, see cuda_differ2._ensure_toolbar_for_visit): a config
    dialog OK must not turn 'lazy' back into 'create N idle forms at
    once', it only has to show the effect on the tab the user is
    looking at."""
    show = bool(cmd.cfg.get('show_toolbar', True))
    show_text = bool(cmd.cfg.get('show_btn_text', True))
    for key in list(_TOOLBARS):
        tb = _TOOLBARS[key]
        dead = True
        try:
            dead = cmd._session_for(key) is None
        except Exception:
            dead = True
        if not show or dead or not tb.is_created():
            tb.destroy()
            del _TOOLBARS[key]
    if not show:
        return
    for tb in list(_TOOLBARS.values()):
        if tb.is_created():
            tb.set_show_text(show_text)
            tb.apply_icon_options()
            tb.rebuild_ignore_menu()
    # Lazy creation, focused tab only (None / not a compare tab: the
    # next visit serves it).
    a_ed = None
    try:
        a_ed = ct.ed
        session = cmd._session_for(a_ed.get_prop(ct.PROP_TAB_ID))
    except Exception:
        session = None
    if session is not None and _TOOLBARS.get(session.tab_id_str) is None:
        ensure_for_session(cmd, session, a_ed)


# ---------------------------------------------------------------------------
# String-callback entry points.
#
# Menu items use the 'module=cuda_differ2;cmd=toolbar_menu_ignore /
# toolbar_menu_preset / toolbar_menu_view / toolbar_menu_dirs;
# info=<tab id>|<action>;' form
# (Command methods -- info arrives as the RAW string). The
# module-level entries below are the belt-and-braces twins for any
# 'module=cuda_differ2.toolbar;
# func=_menu_click; info="<tab id>|<action>;"' callback (info QUOTED:
# the engine's ValueFromString turns an unquoted non-numeric value
# into None).
# ---------------------------------------------------------------------------

def menu_action(info):
    """'info' is '<tab_id_str>|<ignore key or *>': route the click to the
    toolbar of that compare tab. Returns True when a toolbar handled
    it (False: unknown tab / no toolbar / bad payload)."""
    if not info or not isinstance(info, str) or '|' not in info:
        return False
    try:
        tab_id_str, action = info.split('|', 1)
    except ValueError:
        return False
    tb = _TOOLBARS.get(tab_id_str)
    if tb is None:
        return False
    tb.on_menu_action(action)
    return True


def preset_menu_action(info):
    """'info' is '<tab_id_str>|<preset key>': route the click to the
    toolbar of that compare tab. Returns True when a toolbar handled
    it (False: unknown tab / no toolbar / bad payload)."""
    if not info or not isinstance(info, str) or '|' not in info:
        return False
    try:
        tab_id_str, action = info.split('|', 1)
    except ValueError:
        return False
    tb = _TOOLBARS.get(tab_id_str)
    if tb is None:
        return False
    tb.on_preset_action(action)
    return True


def view_menu_action(info):
    """'info' is '<tab_id_str>|<view key>': route the click to the
    toolbar of that compare tab. Returns True when a toolbar handled
    it (False: unknown tab / no toolbar / bad payload)."""
    if not info or not isinstance(info, str) or '|' not in info:
        return False
    try:
        tab_id_str, action = info.split('|', 1)
    except ValueError:
        return False
    tb = _TOOLBARS.get(tab_id_str)
    if tb is None:
        return False
    tb.on_view_action(action)
    return True


def folders_menu_action(info):
    """'info' is '<tab_id_str>|<folder key>': route the click to the
    toolbar of that compare tab (which schedules the folder action on
    the 100ms menu-close-first timer). Returns True when a toolbar
    handled it (False: unknown tab / no toolbar / bad payload)."""
    if not info or not isinstance(info, str) or '|' not in info:
        return False
    try:
        tab_id_str, action = info.split('|', 1)
    except ValueError:
        return False
    tb = _TOOLBARS.get(tab_id_str)
    if tb is None:
        return False
    tb.on_folders_action(action)
    return True


def _menu_click(*args, **kwargs):
    """'func=' callback twin of menu_action: info must be QUOTED in the
    command string ('info="501|ignore_case";') so the engine passes it
    as a string -- an unquoted value would arrive as None here (that
    was the silent no-op of the first toolbar version)."""
    info = kwargs.get('info', '')
    if not info:
        for a in args:
            if isinstance(a, str) and '|' in a:
                info = a
                break
    if not info:
        import cudatext as _ct
        try:
            _ct.msg_log_console(
                'Differ 2 toolbar: menu callback got empty info')
        except Exception:
            pass
        return
    menu_action(info)
