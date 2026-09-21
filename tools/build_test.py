"""Build a headless test copy of index.html.

Injected before the game script:
  * a setTimeout-based requestAnimationFrame shim -- headless Chrome has no
    compositor under --virtual-time-budget, so the real rAF fires exactly once
    and the game could never tick.
  * a seeded Math.random so food always lands on the cell directly in front of
    the starting head, making "did it eat?" a deterministic assertion.

Appended after it: a harness that drives three scenarios with real key events
and reports through document.title.

Board facts the timings rely on (GRID=20, CELL=24, TICK=120ms):
  head starts at (10,10) heading right, body trails to (8,10)
  seeded food lands at (11,10) -- eaten on tick 1 if the snake keeps going right
  running right from x=10 hits the wall on tick 10
  running up   from y=10 hits the wall on tick 11
"""
import io, sys

SRC, DST = sys.argv[1], sys.argv[2]
html = io.open(SRC, encoding="utf-8").read()

SEED = """<script>
  // headless Chrome drives no frames; emulate a 60fps clock
  window.requestAnimationFrame = (cb) => setTimeout(() => cb(performance.now()), 16);
  // 3 snake cells (208,209,210) sit below grid index 211 = (11,10),
  // so the cell in front of the head is index 208 of the 397 free cells.
  Math.random = () => 208 / 397 + 1e-9;
</script>
"""

marker = "<script>\n(() => {\n  'use strict';"
assert marker in html, "game script marker not found"
html = html.replace(marker, SEED + marker, 1)

HARNESS = """
<script>
(() => {
  const log = [];
  const el = (id) => document.getElementById(id);
  const key = (code) => window.dispatchEvent(
    new KeyboardEvent('keydown', { code, bubbles: true, cancelable: true }));
  const playing = () => el('overlay').hidden === true;
  const score = () => el('score').textContent;
  const check = (name, cond) => log.push((cond ? 'PASS ' : 'FAIL ') + name);
  const at = (ms, fn) => setTimeout(fn, ms);

  // ---- A. start, eat, die on the right wall ----
  at(40, () => {
    check('READY overlay visible', el('overlay').hidden === false);
    check('READY greeting is 펭-하!', el('shout').textContent === '펭-하!');
    check('READY score is 0', score() === '0');
    key('Space');
    check('START hides overlay', playing());
  });
  at(220, () => {
    check('EAT score becomes 1', score() === '1');
    check('EAT still playing', playing());
  });
  at(1600, () => {
    check('WALL game over shown', el('overlay').hidden === false);
    check('WALL greeting is 여기까지!', el('shout').textContent === '여기까지!');
    check('WALL tally is 1점', el('tally').textContent === '1점');
    check('WALL best becomes 1', el('best').textContent === '1');
    check('WALL record badge shown', el('record').hidden === false);
    let stored = null;
    try { stored = localStorage.getItem('pengsoo-snake-best'); } catch (e) {}
    check('WALL best persisted', stored === '1');
  });

  // ---- B. reverse input must be ignored, not obeyed and not fatal ----
  at(1700, () => {
    key('Space');
    check('RESTART playing again', playing());
    check('RESTART score reset to 0', score() === '0');
    key('ArrowLeft');            // opposite of current heading
  });
  at(2000, () => {
    check('REVERSE not instantly fatal', playing());
  });
  at(2100, () => {
    // Proves the snake kept heading RIGHT (it reached the food) rather than
    // the game simply having frozen.
    check('REVERSE ignored, ate food heading right', score() === '1');
  });
  at(3100, () => {
    check('REVERSE run ends at wall', el('overlay').hidden === false);
    check('TIE score does not re-flag a record', el('record').hidden === true);
    check('TIE best stays 1', el('best').textContent === '1');
  });

  // ---- C. a legal turn must actually change direction ----
  at(3200, () => { key('Space'); key('ArrowUp'); });
  at(3400, () => {
    // Turning up means it never reaches the food at (11,10).
    check('TURN took effect, no food eaten', score() === '0');
    check('TURN still playing', playing());
  });
  at(4700, () => {
    check('TURN run ends at top wall', el('overlay').hidden === false);
    check('TURN tally is 0점', el('tally').textContent === '0점');
    document.title = 'RESULT::' + log.join(' | ');
  });
})();
</script>
"""

html = html.replace("</body>", HARNESS + "</body>", 1)
io.open(DST, "w", encoding="utf-8", newline="\n").write(html)
print("wrote", DST)
