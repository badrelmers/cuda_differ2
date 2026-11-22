# ============================================================================
# CudaText callback leak fixes - console test snippets: button_proc
# ----------------------------------------------------------------------------
# Paste into the CudaText console (View > Panels > Console), one line at a
# time or the whole file at once - every line is self-contained.
# Expected output (with the FIXED cudatext.py) is in the comment above each
# line; "[stock: ...]" shows what the ORIGINAL cudatext.py prints instead.
# Each line pins a 200 MB bytearray through the callback (~400 MB transient)
# and builds a throwaway dialog with a 'button_ex' control.
# ============================================================================

# 1) click-callback on a dialog button, dialog freed
# expected: 1) button_ex + BTN_SET_DATA1 + DLG_FREE: freed (fixed)  [stock: LEAKED 200MB]
import cudatext as ct, weakref, gc; f = lambda blob=bytearray(200<<20): blob; r = weakref.ref(f); d = ct.dlg_proc(0, ct.DLG_CREATE); n = ct.dlg_proc(d, ct.DLG_CTL_ADD, 'button_ex'); ct.dlg_proc(d, ct.DLG_CTL_PROP_SET, index=n, prop={'name':'b1'}); h = ct.dlg_proc(d, ct.DLG_CTL_HANDLE, name='b1'); ct.button_proc(h, ct.BTN_SET_DATA1, f); ct.dlg_proc(d, ct.DLG_FREE); del f; gc.collect(); print('1) button_ex + BTN_SET_DATA1 + DLG_FREE:', 'LEAKED 200MB' if r() else 'freed (fixed)')

# 2) callback replaced by a plain int command
# expected: 2) callback replaced by int command: freed (fixed)  [stock: LEAKED 200MB]
import cudatext as ct, weakref, gc; f = lambda blob=bytearray(200<<20): blob; r = weakref.ref(f); d = ct.dlg_proc(0, ct.DLG_CREATE); n = ct.dlg_proc(d, ct.DLG_CTL_ADD, 'button_ex'); ct.dlg_proc(d, ct.DLG_CTL_PROP_SET, index=n, prop={'name':'b1'}); h = ct.dlg_proc(d, ct.DLG_CTL_HANDLE, name='b1'); ct.button_proc(h, ct.BTN_SET_DATA1, f); ct.button_proc(h, ct.BTN_SET_DATA1, 2707); del f; gc.collect(); print('2) callback replaced by int command:', 'LEAKED 200MB' if r() else 'freed (fixed)'); ct.dlg_proc(d, ct.DLG_FREE)

# 3) the button control itself deleted from the dialog
# expected: 3) DLG_CTL_DELETE of button control: freed (fixed)  [stock: LEAKED 200MB]
import cudatext as ct, weakref, gc; f = lambda blob=bytearray(200<<20): blob; r = weakref.ref(f); d = ct.dlg_proc(0, ct.DLG_CREATE); n = ct.dlg_proc(d, ct.DLG_CTL_ADD, 'button_ex'); ct.dlg_proc(d, ct.DLG_CTL_PROP_SET, index=n, prop={'name':'b1'}); h = ct.dlg_proc(d, ct.DLG_CTL_HANDLE, name='b1'); ct.button_proc(h, ct.BTN_SET_DATA1, f); ct.dlg_proc(d, ct.DLG_CTL_DELETE, name='b1'); del f; gc.collect(); print('3) DLG_CTL_DELETE of button control:', 'LEAKED 200MB' if r() else 'freed (fixed)'); ct.dlg_proc(d, ct.DLG_FREE)

# 4) click-callback on a TOOLBAR button (the engine ignores ADD_ITEM's command;
#    only button_proc(BTN_SET_DATA1) installs it), dialog freed
# expected: 4) toolbar button (engine ignores ADD command) + DLG_FREE: freed (fixed)  [stock: LEAKED 200MB]
import cudatext as ct, weakref, gc; f = lambda blob=bytearray(200<<20): blob; r = weakref.ref(f); d = ct.dlg_proc(0, ct.DLG_CREATE); n = ct.dlg_proc(d, ct.DLG_CTL_ADD, 'toolbar'); tb = ct.dlg_proc(d, ct.DLG_CTL_HANDLE, index=n); hb = ct.toolbar_proc(tb, ct.TOOLBAR_ADD_ITEM); ct.button_proc(hb, ct.BTN_SET_DATA1, f); ct.dlg_proc(d, ct.DLG_FREE); del f; gc.collect(); print('4) toolbar button (engine ignores ADD command) + DLG_FREE:', 'LEAKED 200MB' if r() else 'freed (fixed)')

# 5) one callback shared by a menu item and the button
# expected: 5a) shared f, menu cleared, button alive: still alive (correct)
#           5b) after dialog freed too: freed (fixed)    [stock 5b: LEAKED]
import cudatext as ct, weakref, gc; f = lambda blob=bytearray(200<<20): blob; r = weakref.ref(f); d = ct.dlg_proc(0, ct.DLG_CREATE); n = ct.dlg_proc(d, ct.DLG_CTL_ADD, 'button_ex'); ct.dlg_proc(d, ct.DLG_CTL_PROP_SET, index=n, prop={'name':'b1'}); h = ct.dlg_proc(d, ct.DLG_CTL_HANDLE, name='b1'); m = ct.menu_proc(0, ct.MENU_CREATE); ct.menu_proc(m, ct.MENU_ADD, command=f, caption='x'); ct.button_proc(h, ct.BTN_SET_DATA1, f); ct.menu_proc(m, ct.MENU_CLEAR); del f; gc.collect(); print('5a) shared f, menu cleared, button alive:', 'BROKEN: freed too early' if not r() else 'still alive (correct)'); ct.dlg_proc(d, ct.DLG_FREE); gc.collect(); print('5b) after dialog freed too:', 'LEAKED' if r() else 'freed (fixed)')

# 6) one callback shared by the button and a timer: TIMER_STOP must NOT kill the button
# expected: 6a) after TIMER_STOP of shared f: still alive (correct)   [stock: BROKEN: freed too early]
#           6b) after dialog freed: freed                              [stock: freed (already dead)]
import cudatext as ct, weakref, gc; f = lambda blob=bytearray(200<<20): blob; r = weakref.ref(f); d = ct.dlg_proc(0, ct.DLG_CREATE); n = ct.dlg_proc(d, ct.DLG_CTL_ADD, 'button_ex'); ct.dlg_proc(d, ct.DLG_CTL_PROP_SET, index=n, prop={'name':'b1'}); h = ct.dlg_proc(d, ct.DLG_CTL_HANDLE, name='b1'); ct.button_proc(h, ct.BTN_SET_DATA1, f); ct.timer_proc(ct.TIMER_START, f, 500); ct.timer_proc(ct.TIMER_STOP, f, 0); del f; gc.collect(); print('6a) after TIMER_STOP of shared f:', 'BROKEN: freed too early' if not r() else 'still alive (correct)'); ct.dlg_proc(d, ct.DLG_FREE); gc.collect(); print('6b) after dialog freed:', 'LEAKED' if r() else 'freed')

# 7) registry check
# expected: 7) _live: 0 | buttons tracked: 0 | toolbar bars: 0 | dlg ctl handles: 0  [stock: N/A]
import cudatext as ct; print('7) _live:', len(ct._live), '| buttons tracked:', len(ct._button_data), '| toolbar bars:', len(ct._toolbar_btns), '| dlg ctl handles:', len(ct._dlg_ctl_handles))
