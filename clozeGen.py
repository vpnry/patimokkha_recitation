#!/usr/bin/env python3
import argparse
import hashlib
import html
import random
import re
import sys

# Try lxml for better performance/compliance, fallback to standard ElementTree
try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pali Memorizer</title>
<style>
    :root {
        --bg-color: #fcfcfc;
        --text-color: #222;
        --panel-bg: #eee;
        --border: #ccc;
        --input-bg: #fff;
        --input-border: #666;
        --correct: #2e7d32;
        --incorrect: #c62828;
        --btn-bg: #e0e0e0;
        --btn-hover: #d5d5d5;
    }
    body.dark-mode {
        --bg-color: #1a1a1a;
        --text-color: #e0e0e0;
        --panel-bg: #2d2d2d;
        --border: #444;
        --input-bg: #333;
        --input-border: #888;
        --correct: #66bb6a;
        --incorrect: #ef5350;
        --btn-bg: #444;
        --btn-hover: #555;
    }
    body {
        font-family: 'Noto Serif', 'Gentium Plus', serif;
        background-color: var(--bg-color);
        color: var(--text-color);
        margin: 0;
        padding: 0;
        line-height: 1.6;
        transition: background-color 0.3s, color 0.3s;
    }
    .menu-toggle {
        position: fixed;
        top: 12px;
        right: 12px;
        z-index: 1100;
        width: 44px;
        height: 44px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 5px;
        background: var(--panel-bg);
        color: var(--text-color);
        border: 1px solid var(--border);
        border-radius: 8px;
        cursor: pointer;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
    }
    .menu-toggle span {
        width: 20px;
        height: 2px;
        background: var(--text-color);
        border-radius: 2px;
    }
    .toolbar {
        position: fixed;
        top: 64px;
        right: 12px;
        width: min(360px, calc(100vw - 24px));
        max-height: calc(100vh - 84px);
        overflow-y: auto;
        background: var(--panel-bg);
        padding: 14px;
        border: 1px solid var(--border);
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        align-items: stretch;
        z-index: 1000;
        font-family: sans-serif;
        font-size: 0.9rem;
        box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
        opacity: 0;
        pointer-events: none;
        transform: translateY(-8px);
        transition: opacity 0.2s, transform 0.2s;
    }
    .toolbar.open {
        opacity: 1;
        pointer-events: auto;
        transform: translateY(0);
    }
    .toolbar button {
        background: var(--btn-bg);
        color: var(--text-color);
        border: 1px solid var(--border);
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        transition: background 0.2s;
        text-align: left;
    }
    .toolbar button:hover { background: var(--btn-hover); }
    .slider-container { display: flex; align-items: center; gap: 8px; }
    .slider-container input { flex: 1; }
    .progress-container { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
    .progress-bar-bg { flex: 1 1 120px; height: 10px; background: var(--border); border-radius: 5px; overflow: hidden; }
    .progress-bar-fill { height: 100%; background: var(--correct); width: 0%; transition: width 0.3s; }
    .container { max-width: 800px; margin: 30px auto; padding: 0 20px; font-size: 1.25rem; }
    .segment { margin-bottom: 1.5em; }
    .gatha { margin-bottom: 0.3em; padding-left: 2rem; font-style: italic; }
    input.cloze {
        font-family: inherit;
        font-size: inherit;
        background: var(--input-bg);
        color: var(--text-color);
        border: none;
        border-bottom: 2px solid var(--input-border);
        text-align: center;
        margin: 0 2px;
        padding: 0 2px;
        outline: none;
        border-radius: 0;
        transition: border-color 0.2s;
    }
    input.cloze:focus { border-bottom-color: #1976d2; }
    input.cloze.correct {
        color: var(--correct);
        border-bottom-color: var(--correct);
        background: transparent;
    }
    input.cloze.incorrect {
        color: var(--incorrect);
        border-bottom-color: var(--incorrect);
        animation: shake 0.4s;
    }
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25%, 75% { transform: translateX(-5px); }
        50% { transform: translateX(5px); }
    }
    .sentence-nav { display: none; justify-content: space-between; margin-top: 30px; font-family: sans-serif; }
    .sentence-nav button { padding: 10px 20px; font-size: 1rem; cursor: pointer; background: var(--btn-bg); color: var(--text-color); border: 1px solid var(--border); border-radius: 4px; }
    .sentence-nav button:hover { background: var(--btn-hover); }
</style>
</head>
<body>
<button class="menu-toggle" id="btn-menu" aria-label="Open menu" aria-controls="toolbar" aria-expanded="false">
    <span></span>
    <span></span>
    <span></span>
</button>
<div class="toolbar" id="toolbar" aria-hidden="true">
    <button id="btn-reshuffle" title="Shortcut: Ctrl+R">New Test</button>
    <button id="btn-reveal" title="Shortcut: Ctrl+H">Reveal All</button>
    <button id="btn-reset">Reset</button>
    <button id="btn-mode">Sentence Mode</button>
    <button id="btn-dark">Dark Mode</button>
    <div class="slider-container" title="Target Hide Rate">
        <label for="hide-rate">Hide Rate:</label>
        <input type="range" id="hide-rate" min="5" max="100" value="{{HIDE_RATE_PERCENT}}">
        <span id="rate-val">{{HIDE_RATE_PERCENT}}%</span>
    </div>
    <div class="progress-container">
        <span id="last-session" style="font-size: 0.8rem; opacity: 0.8;"></span>
        <span id="progress-text">0 / {{TOTAL_CLOZE}}</span>
        <div class="progress-bar-bg"><div id="progress-bar" class="progress-bar-fill"></div></div>
    </div>
</div>

<div class="container" id="text-container">
    {{CONTENT}}
    <div class="sentence-nav" id="sentence-nav">
        <button id="btn-prev">&laquo; Previous</button>
        <button id="btn-next">Next &raquo;</button>
    </div>
</div>

<script>
    const HASH = "{{HASH}}";
    const STORAGE_KEY = 'pali_memo_state_' + HASH;
    const LEGACY_STORAGE_KEY = 'pali_memo_' + HASH;
    let hideRate = {{HIDE_RATE}};
    let sentenceMode = false;
    let currentSentenceIndex = 0;
    let isRestoring = false;
    let pendingRestoreScrollY = null;

    function init() {
        bindEvents();
        isRestoring = true;
        restoreState();
        setupSentenceMode();
        updateProgress();
        requestAnimationFrame(() => {
            if (!sentenceMode && Number.isFinite(pendingRestoreScrollY)) {
                window.scrollTo(0, pendingRestoreScrollY);
            }
            isRestoring = false;
            updateProgress();
        });
    }

    function checkAnswer(input) {
        if (input.readOnly) return;
        const answer = input.dataset.answer.toLowerCase();
        const value = input.value.toLowerCase();
        if (value === answer) {
            input.classList.remove('incorrect');
            input.classList.add('correct');
            input.readOnly = true;
            updateProgress();
        } else {
            input.classList.add('incorrect');
            setTimeout(() => input.classList.remove('incorrect'), 400);
            input.focus();
        }
    }

    function bindEvents() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key.toLowerCase() === 'r') { e.preventDefault(); reshuffle(); }
            if (e.ctrlKey && e.key.toLowerCase() === 'h') { e.preventDefault(); toggleAnswers(); }
            if (e.key === 'Escape') closeMenu();
        });

        document.addEventListener('click', (e) => {
            const toolbar = document.getElementById('toolbar');
            const menuButton = document.getElementById('btn-menu');
            if (!toolbar.contains(e.target) && !menuButton.contains(e.target)) closeMenu();
        });

        window.addEventListener('beforeunload', saveState);
        window.addEventListener('pagehide', saveState);
        window.addEventListener('scroll', debounce(saveState, 250), {passive: true});

        document.getElementById('text-container').addEventListener('keyup', (e) => {
            if (e.target.tagName === 'INPUT' && e.target.classList.contains('cloze')) {
                if (e.key === 'Enter') checkAnswer(e.target);
                saveState();
            }
        });
        document.getElementById('text-container').addEventListener('input', (e) => {
            if (e.target.tagName === 'INPUT' && e.target.classList.contains('cloze')) saveState();
        });

        document.getElementById('hide-rate').addEventListener('input', (e) => {
            hideRate = e.target.value / 100;
            document.getElementById('rate-val').textContent = e.target.value + '%';
            saveState();
        });
        document.getElementById('hide-rate').addEventListener('change', reshuffle);
        document.getElementById('btn-reset').addEventListener('click', reset);
        document.getElementById('btn-reveal').addEventListener('click', revealAll);
        document.getElementById('btn-reshuffle').addEventListener('click', reshuffle);
        document.getElementById('btn-mode').addEventListener('click', toggleMode);
        document.getElementById('btn-dark').addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            saveState();
        });
        document.getElementById('btn-prev').addEventListener('click', () => showSentence(currentSentenceIndex - 1));
        document.getElementById('btn-next').addEventListener('click', () => showSentence(currentSentenceIndex + 1));
        document.getElementById('btn-menu').addEventListener('click', toggleMenu);
    }

    function makeSpanFromInput(inp) {
        const span = document.createElement('span');
        span.className = 'hideable';
        span.dataset.id = inp.dataset.id;
        span.dataset.word = inp.dataset.answer;
        span.dataset.context = inp.dataset.context;
        span.textContent = inp.dataset.answer;
        return span;
    }

    function makeInputFromSpan(span) {
        const inp = document.createElement('input');
        inp.className = 'cloze';
        inp.type = 'text';
        inp.dataset.id = span.dataset.id;
        inp.dataset.answer = span.dataset.word;
        inp.dataset.context = span.dataset.context;
        inp.size = span.dataset.word.length;
        inp.setAttribute('aria-label', 'Context: ' + span.dataset.context);
        return inp;
    }

    function applyHiddenIds(hiddenIds) {
        const ids = new Set(hiddenIds.map(String));
        document.querySelectorAll('input.cloze').forEach(inp => {
            inp.replaceWith(makeSpanFromInput(inp));
        });

        document.querySelectorAll('.hideable').forEach(span => {
            if (ids.has(span.dataset.id)) span.replaceWith(makeInputFromSpan(span));
        });
    }

    function reshuffle() {
        document.querySelectorAll('input.cloze').forEach(inp => {
            inp.replaceWith(makeSpanFromInput(inp));
        });

        const spans = Array.from(document.querySelectorAll('.hideable'));
        spans.sort(() => Math.random() - 0.5);
        const toHide = Math.floor(spans.length * hideRate);

        for (let i = 0; i < toHide; i++) {
            const span = spans[i];
            span.replaceWith(makeInputFromSpan(span));
        }
        resetProgress();
        setupSentenceMode();
    }

    function toggleAnswers() {
        document.querySelectorAll('input.cloze').forEach(inp => {
            if (!inp.readOnly) inp.placeholder = inp.placeholder ? '' : inp.dataset.answer;
        });
    }

    function revealAll() {
        document.querySelectorAll('input.cloze').forEach(inp => {
            inp.value = inp.dataset.answer;
            inp.classList.add('correct');
            inp.readOnly = true;
        });
        updateProgress();
    }

    function reset() {
        document.querySelectorAll('input.cloze').forEach(inp => {
            inp.value = '';
            inp.classList.remove('correct');
            inp.readOnly = false;
            inp.placeholder = '';
        });
        resetProgress();
    }

    function updateProgress() {
        const total = document.querySelectorAll('input.cloze').length;
        const correct = document.querySelectorAll('input.cloze.correct').length;
        document.getElementById('progress-text').textContent = correct + ' / ' + total;
        document.getElementById('progress-bar').style.width = (total === 0 ? 0 : (correct/total)*100) + '%';
        saveState();
    }

    function resetProgress() {
        localStorage.removeItem(LEGACY_STORAGE_KEY);
        updateProgress();
    }

    function getClozeState() {
        const answers = {};
        const hiddenIds = [];
        document.querySelectorAll('input.cloze').forEach(inp => {
            const id = inp.dataset.id;
            hiddenIds.push(id);
            answers[id] = {
                value: inp.value,
                correct: inp.classList.contains('correct'),
                readOnly: inp.readOnly
            };
        });
        return {answers, hiddenIds};
    }

    function saveState() {
        if (isRestoring) return;
        const total = document.querySelectorAll('input.cloze').length;
        const correct = document.querySelectorAll('input.cloze.correct').length;
        const clozeState = getClozeState();
        const state = {
            correct,
            total,
            hideRate,
            darkMode: document.body.classList.contains('dark-mode'),
            sentenceMode,
            currentSentenceIndex,
            scrollY: window.scrollY,
            answers: clozeState.answers,
            hiddenIds: clozeState.hiddenIds,
            savedAt: new Date().toISOString()
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }

    function restoreState() {
        const stored = localStorage.getItem(STORAGE_KEY);
        const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
        if (!stored && legacy) {
            try {
                const p = JSON.parse(legacy);
                document.getElementById('last-session').textContent = `Last session: ${p.correct}/${p.total}`;
            } catch(e) {}
            return;
        }
        if (!stored) return;

        try {
            const state = JSON.parse(stored);
            if (typeof state.hideRate === 'number') {
                hideRate = state.hideRate;
                const percent = Math.round(hideRate * 100);
                document.getElementById('hide-rate').value = percent;
                document.getElementById('rate-val').textContent = percent + '%';
            }
            if (state.darkMode) document.body.classList.add('dark-mode');
            if (Array.isArray(state.hiddenIds)) applyHiddenIds(state.hiddenIds);
            if (state.answers) {
                document.querySelectorAll('input.cloze').forEach(inp => {
                    const saved = state.answers[inp.dataset.id];
                    if (!saved) return;
                    inp.value = saved.value || '';
                    inp.readOnly = Boolean(saved.readOnly);
                    inp.classList.toggle('correct', Boolean(saved.correct));
                });
            }
            sentenceMode = Boolean(state.sentenceMode);
            currentSentenceIndex = Number.isInteger(state.currentSentenceIndex) ? state.currentSentenceIndex : 0;
            if (state.total > 0) {
                document.getElementById('last-session').textContent = `Last session: ${state.correct}/${state.total}`;
            }
            if (!sentenceMode && Number.isFinite(state.scrollY)) {
                pendingRestoreScrollY = state.scrollY;
            }
        } catch(e) {
            localStorage.removeItem(STORAGE_KEY);
        }
    }

    function toggleMode() {
        sentenceMode = !sentenceMode;
        document.getElementById('btn-mode').textContent = sentenceMode ? 'Full Text Mode' : 'Sentence Mode';
        setupSentenceMode();
        saveState();
    }

    function setupSentenceMode() {
        const segments = document.querySelectorAll('.segment');
        document.getElementById('btn-mode').textContent = sentenceMode ? 'Full Text Mode' : 'Sentence Mode';
        if (!sentenceMode) {
            segments.forEach(s => s.style.display = '');
            document.getElementById('sentence-nav').style.display = 'none';
        } else {
            showSentence(currentSentenceIndex);
        }
    }

    function showSentence(index) {
        const segments = document.querySelectorAll('.segment');
        if (!segments.length) return;
        if (index < 0) index = 0;
        if (index >= segments.length) index = segments.length - 1;
        currentSentenceIndex = index;
        segments.forEach((s, i) => s.style.display = (i === index) ? '' : 'none');
        document.getElementById('sentence-nav').style.display = 'flex';
        saveState();
    }

    function toggleMenu() {
        const toolbar = document.getElementById('toolbar');
        const menuButton = document.getElementById('btn-menu');
        const open = !toolbar.classList.contains('open');
        toolbar.classList.toggle('open', open);
        toolbar.setAttribute('aria-hidden', String(!open));
        menuButton.setAttribute('aria-expanded', String(open));
    }

    function closeMenu() {
        const toolbar = document.getElementById('toolbar');
        const menuButton = document.getElementById('btn-menu');
        toolbar.classList.remove('open');
        toolbar.setAttribute('aria-hidden', 'true');
        menuButton.setAttribute('aria-expanded', 'false');
    }

    function debounce(fn, delay) {
        let timer;
        return function() {
            clearTimeout(timer);
            timer = setTimeout(fn, delay);
        };
    }

    window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
"""

def remove_namespaces(tree):
    for el in tree.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

def extract_blocks(node, target_tags, depth=1):
    blocks =[]
    editorial_tags = {'note', 'app', 'rdg', 'corr', 'sic'}

    def get_text(n, in_foreign=False):
        res =[]
        if n.text:
            res.append((n.text, in_foreign))
        for child in n:
            if child.tag not in editorial_tags:
                is_foreign = in_foreign or child.tag == 'foreign'
                res.extend(get_text(child, is_foreign))
            # tail text belongs to the parent flow conceptually, always include it
            if child.tail:
                res.append((child.tail, in_foreign))
        return res

    if node.tag == 'div':
        for child in node:
            blocks.extend(extract_blocks(child, target_tags, depth + 1))
    elif node.tag == 'head':
        h = min(depth + 1, 6)
        blocks.append(('head', h, get_text(node)))
    elif node.tag in target_tags:
        blocks.append((node.tag, None, get_text(node)))
    else:
        for child in node:
            blocks.extend(extract_blocks(child, target_tags, depth))
            
    return blocks

def main():
    parser = argparse.ArgumentParser(description="PaliMemorizer Builder")
    parser.add_argument('input', help="Input XML file")
    parser.add_argument('--output', default='index.html', help="Output HTML file")
    parser.add_argument('--hide-rate', type=float, default=0.18, help="Initial hide rate (0.0 to 1.0)")
    parser.add_argument('--tags', default='p,seg,l,verse,gatha', help="Comma-separated tags to extract")
    args = parser.parse_args()

    # Read bytes for hashing, then parse XML
    with open(args.input, 'rb') as f:
        file_data = f.read()
    file_hash = hashlib.md5(file_data).hexdigest()

    try:
        tree = ET.fromstring(file_data)
        remove_namespaces(tree)
    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        sys.exit(1)

    target_tags = set(tag.strip() for tag in args.tags.split(','))
    blocks = extract_blocks(tree, target_tags)

    pali_word_re = re.compile(r'([a-zA-ZāīūṃṅñṭḍḷĀĪŪṂṄÑṬḌḶ]+)')
    candidates = []
    html_chunks =[]

    for block_type, level, text_tuples in blocks:
        chunk_html =[]
        if block_type == 'head':
            chunk_html.append(f'<h{level}>')
        else:
            cls = "segment gatha" if block_type in ['l', 'verse', 'gatha'] else "segment"
            chunk_html.append(f'<div class="{cls}">')

        for text_val, in_foreign in text_tuples:
            parts = pali_word_re.split(text_val)
            for part in parts:
                if not part:
                    continue
                if pali_word_re.match(part) and len(part) >= 3 and not in_foreign and block_type != 'head':
                    idx = len(candidates)
                    chunk_html.append(f'__CLOZE_{idx}__')
                    candidates.append(part)
                else:
                    # Escape safe print components
                    chunk_html.append(part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

        if block_type == 'head':
            chunk_html.append(f'</h{level}>')
        else:
            chunk_html.append('</div>')
            
        html_chunks.append(''.join(chunk_html))

    # Pick indices to initially obscure
    num_to_hide = int(len(candidates) * args.hide_rate)
    indices_to_hide = set(random.sample(range(len(candidates)), num_to_hide))

    final_html_parts =[]
    for chunk in html_chunks:
        def repl(m):
            idx = int(m.group(1))
            word = candidates[idx]
            prev_w = candidates[idx-1] if idx > 0 else ""
            next_w = candidates[idx+1] if idx < len(candidates)-1 else ""
            ctx = f"{prev_w} ___ {next_w}".strip()
            word_attr = html.escape(word, quote=True)
            ctx_attr = html.escape(ctx, quote=True)
            word_text = html.escape(word)
            
            if idx in indices_to_hide:
                return f'<input class="cloze" type="text" data-id="{idx}" data-answer="{word_attr}" data-context="{ctx_attr}" size="{len(word)}" aria-label="Context: {ctx_attr}">'
            else:
                return f'<span class="hideable" data-id="{idx}" data-word="{word_attr}" data-context="{ctx_attr}">{word_text}</span>'

        final_html_parts.append(re.sub(r'__CLOZE_(\d+)__', repl, chunk))

    # Compile the final page
    html_out = HTML_TEMPLATE.replace('{{CONTENT}}', "\n".join(final_html_parts))
    html_out = html_out.replace('{{HIDE_RATE}}', str(args.hide_rate))
    html_out = html_out.replace('{{HIDE_RATE_PERCENT}}', str(int(args.hide_rate * 100)))
    html_out = html_out.replace('{{TOTAL_CLOZE}}', str(num_to_hide))
    html_out = html_out.replace('{{HASH}}', file_hash)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_out)

    num_segments = sum(1 for chunk in html_chunks if 'class="segment' in chunk)
    print(f"Built {args.output} from {args.input} ({num_segments} sentences, {num_to_hide} words hidden)")

if __name__ == '__main__':
    main()
