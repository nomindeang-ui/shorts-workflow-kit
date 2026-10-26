"""Render an offline workflow board from workflow-status.json."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "workflow-status.json"
OUTPUT = ROOT / "쇼츠-작업현황.html"
VALID_STATES = {"completed", "conditional", "in_progress", "waiting", "blocked", "needs_revision"}


def validate(data: dict) -> None:
    stages = data.get("stages")
    if not isinstance(stages, list) or [item.get("id") for item in stages] != list(range(1, 10)):
        raise ValueError("stages must contain steps 1 through 9 in order")
    for item in stages:
        if item.get("status") not in VALID_STATES:
            raise ValueError(f"invalid status for step {item.get('id')}")
        for output in item.get("outputs", []):
            target = Path(output["path"])
            if target.is_absolute() or ".." in target.parts or ":" in output["path"]:
                raise ValueError("output links must stay inside this project folder")


HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>쇼츠 작업 현황</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f5f7fb; --panel: #ffffff; --ink: #172235; --sub: #536176;
    --line: #c8d0dd; --edge: #8b98ab; --done: #157347; --done-bg: #e5f6ec;
    --conditional: #975600; --conditional-bg: #fff2d8; --active: #1658ad;
    --active-bg: #e7f0ff; --blocked: #ad2934; --blocked-bg: #ffebed;
    --pending-bg: #e9edf3; --focus: #315fba;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #111923; --panel: #1b2735; --ink: #edf2f8; --sub: #aebdd0;
      --line: #445369; --edge: #8191a6; --done: #63d99b; --done-bg: #173d2b;
      --conditional: #ffd17e; --conditional-bg: #483516; --active: #8fbafa;
      --active-bg: #203d65; --blocked: #ff9da4; --blocked-bg: #572c34;
      --pending-bg: #303e50; --focus: #95bbff;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.5 system-ui, -apple-system, "Malgun Gothic", sans-serif; }
  main { width: min(1180px, calc(100% - 32px)); margin: 28px auto 60px; }
  h1 { margin: 0 0 4px; font-size: clamp(1.45rem, 3vw, 2rem); }
  h2 { margin: 0 0 12px; font-size: 1.12rem; }
  p { margin: 0; }
  .topline { display: flex; justify-content: space-between; gap: 16px; align-items: start; flex-wrap: wrap; }
  .muted { color: var(--sub); }
  .overview { margin-top: 22px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
  .metric, .detail, .next-action { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; }
  .metric strong { display: block; font-size: 1.55rem; line-height: 1.25; margin-top: 4px; }
  .progress { height: 10px; margin: 18px 0 8px; background: var(--pending-bg); border-radius: 999px; overflow: hidden; }
  .progress > span { display: block; height: 100%; background: var(--done); width: 0; transition: width .25s ease; }
  .legend { display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 18px 0 6px; color: var(--sub); font-size: .9rem; }
  .legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 7px; background: var(--edge); }
  .legend .l-done::before { background: var(--done); }
  .legend .l-conditional::before { background: var(--conditional); }
  .legend .l-active::before { background: var(--active); }
  .legend .l-blocked::before { background: var(--blocked); }
  .flow { position: relative; margin: 24px 0 12px; padding: 0 22px; }
  .edges { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; overflow: visible; }
  .nodes { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 42px 48px; }
  .node { min-width: 0; min-height: 108px; position: relative; z-index: 1; text-align: left; border: 2px solid var(--line); border-radius: 14px; background: var(--panel); color: var(--ink); padding: 14px 16px; font: inherit; cursor: pointer; }
  .node:hover { border-color: var(--focus); }
  .node:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
  .node[aria-pressed="true"] { border-color: var(--focus); box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 20%, transparent); }
  .node.completed { border-left: 6px solid var(--done); }
  .node.conditional { border-left: 6px solid var(--conditional); }
  .node.in_progress { border-left: 6px solid var(--active); }
  .node.blocked, .node.needs_revision { border-left: 6px solid var(--blocked); }
  .node.waiting { border-left: 6px solid var(--edge); }
  .node-head { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
  .node-number { font-weight: 700; color: var(--sub); font-size: .9rem; }
  .node-name { display: block; font-size: 1.06rem; font-weight: 700; margin: 4px 0; }
  .node-agent { display: block; color: var(--sub); font-size: .85rem; }
  .badge { border-radius: 999px; padding: 2px 8px; font-size: .79rem; font-weight: 700; white-space: nowrap; }
  .completed .badge { color: var(--done); background: var(--done-bg); }
  .conditional .badge { color: var(--conditional); background: var(--conditional-bg); }
  .in_progress .badge { color: var(--active); background: var(--active-bg); }
  .blocked .badge, .needs_revision .badge { color: var(--blocked); background: var(--blocked-bg); }
  .waiting .badge { color: var(--sub); background: var(--pending-bg); }
  .detail { min-height: 132px; }
  .detail-header { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 6px; }
  .detail-header h2 { margin: 0; }
  .links { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 12px; }
  a { color: var(--active); text-underline-offset: 3px; }
  .next-action { margin-top: 14px; }
  .next-action h2 { margin-bottom: 5px; }
  .loop-note { color: var(--sub); font-size: .88rem; margin: 0 0 18px; }
  .footnote { margin-top: 12px; color: var(--sub); font-size: .85rem; }
  .n1 { grid-area: 1 / 1; } .n2 { grid-area: 1 / 2; } .n3 { grid-area: 1 / 3; }
  .n4 { grid-area: 2 / 3; } .n5 { grid-area: 2 / 2; } .n6 { grid-area: 2 / 1; }
  .n7 { grid-area: 3 / 1; } .n8 { grid-area: 3 / 2; } .n9 { grid-area: 3 / 3; }
  @media (max-width: 720px) {
    .overview { grid-template-columns: 1fr 1fr; }
    .overview .metric:last-child { grid-column: 1 / -1; }
    .nodes { grid-template-columns: 1fr; gap: 35px; }
    .flow { padding: 0 14px; }
    .node { grid-area: auto !important; min-height: 90px; }
  }
  @media (max-width: 420px) { .overview { grid-template-columns: 1fr; } .overview .metric:last-child { grid-column: auto; } }
</style>
</head>
<body>
<main>
  <div class="topline">
    <div><h1 id="project-title"></h1><p class="muted">9개 에이전트 작업 흐름 · <span id="updated-at"></span></p></div>
    <span id="public-badge" class="badge"></span>
  </div>
  <div class="overview" aria-label="작업 요약">
    <div class="metric"><span class="muted">완료</span><strong id="complete-count"></strong></div>
    <div class="metric"><span class="muted">조건부 완료</span><strong id="conditional-count"></strong></div>
    <div class="metric"><span class="muted">남은 단계</span><strong id="remaining-count"></strong></div>
  </div>
  <div class="progress" role="progressbar" aria-label="완료 단계" aria-valuemin="0" aria-valuemax="9" aria-valuenow="0"><span></span></div>
  <div class="legend" aria-label="상태 설명">
    <span class="l-done">완료</span><span class="l-conditional">조건부 완료</span><span class="l-active">진행 중</span><span class="l-blocked">확인·수정 필요</span><span>대기</span>
  </div>
  <section class="flow" aria-label="에이전트 진행 흐름"><svg class="edges" aria-hidden="true"></svg><div class="nodes" id="nodes"></div></section>
  <p class="loop-note">수정 흐름: ⑦에서 문제를 찾으면 ⑥ 편집으로, ⑨에서 대본 피드백을 받으면 ④ 대본 작성으로 돌아갑니다.</p>
  <section class="detail" aria-live="polite" aria-label="선택한 단계 상세"><div class="detail-header"><h2 id="detail-title"></h2><span id="detail-badge" class="badge"></span></div><p id="detail-summary"></p><div id="detail-links" class="links"></div></section>
  <section class="next-action"><h2>다음 확인</h2><p id="next-action"></p></section>
  <p class="footnote">이 화면은 작업 기록을 반영한 확인용입니다. 새 단계가 끝나면 에이전트가 기록을 갱신하고 화면을 다시 만듭니다. 열린 화면은 새로고침하세요.</p>
</main>
<script id="workflow-data" type="application/json">__DATA__</script>
<script>
(() => {
  const data = JSON.parse(document.getElementById('workflow-data').textContent);
  const labels = {completed:'완료', conditional:'조건부 완료', in_progress:'진행 중', waiting:'대기', blocked:'보류', needs_revision:'수정 필요'};
  const $ = id => document.getElementById(id);
  $('project-title').textContent = data.projectTitle;
  $('updated-at').textContent = data.updatedAt + ' 기준';
  $('next-action').textContent = data.nextAction;
  const ready = $('public-badge');
  ready.textContent = data.publicReady ? '공개 준비 완료' : '내부 검토 단계';
  ready.style.color = data.publicReady ? 'var(--done)' : 'var(--conditional)';
  ready.style.background = data.publicReady ? 'var(--done-bg)' : 'var(--conditional-bg)';
  const count = state => data.stages.filter(stage => stage.status === state).length;
  const completed = count('completed');
  const conditional = count('conditional');
  $('complete-count').textContent = `${completed} / 9`;
  $('conditional-count').textContent = String(conditional);
  $('remaining-count').textContent = String(9 - completed - conditional);
  const bar = document.querySelector('.progress');
  bar.setAttribute('aria-valuenow', String(completed));
  bar.querySelector('span').style.width = `${completed / 9 * 100}%`;
  const list = $('nodes');
  data.stages.forEach(stage => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `node n${stage.id} ${stage.status}`;
    button.id = `node-${stage.id}`;
    button.setAttribute('aria-pressed', 'false');
    const head = document.createElement('span'); head.className = 'node-head';
    const number = document.createElement('span'); number.className = 'node-number'; number.textContent = `0${stage.id}`;
    const badge = document.createElement('span'); badge.className = 'badge'; badge.textContent = labels[stage.status];
    head.append(number, badge);
    const name = document.createElement('strong'); name.className = 'node-name'; name.textContent = stage.name;
    const agent = document.createElement('span'); agent.className = 'node-agent'; agent.textContent = stage.agent;
    button.append(head, name, agent);
    button.addEventListener('click', () => select(stage.id));
    list.append(button);
  });
  function select(id) {
    const stage = data.stages.find(item => item.id === id);
    document.querySelectorAll('.node').forEach(node => node.setAttribute('aria-pressed', node.id === `node-${id}` ? 'true' : 'false'));
    $('detail-title').textContent = `0${id} ${stage.name}`;
    const badge = $('detail-badge'); badge.textContent = labels[stage.status];
    badge.style.color = `var(--${stage.status === 'completed' ? 'done' : stage.status === 'conditional' ? 'conditional' : stage.status === 'in_progress' ? 'active' : stage.status === 'waiting' ? 'sub' : 'blocked'})`;
    badge.style.background = `var(--${stage.status === 'completed' ? 'done-bg' : stage.status === 'conditional' ? 'conditional-bg' : stage.status === 'in_progress' ? 'active-bg' : stage.status === 'waiting' ? 'pending-bg' : 'blocked-bg'})`;
    $('detail-summary').textContent = stage.summary;
    const links = $('detail-links'); links.replaceChildren();
    (stage.outputs || []).forEach(output => {
      const link = document.createElement('a'); link.href = output.path; link.textContent = output.label + ' ↗';
      links.append(link);
    });
  }
  function drawEdges() {
    const svg = document.querySelector('.edges');
    const frame = document.querySelector('.flow').getBoundingClientRect();
    svg.replaceChildren();
    svg.setAttribute('viewBox', `0 0 ${frame.width} ${frame.height}`);
    const marker = document.createElementNS('http://www.w3.org/2000/svg','marker');
    marker.setAttribute('id','arrow'); marker.setAttribute('viewBox','0 0 10 10'); marker.setAttribute('refX','9'); marker.setAttribute('refY','5'); marker.setAttribute('markerWidth','7'); marker.setAttribute('markerHeight','7'); marker.setAttribute('orient','auto-start-reverse');
    const arrow = document.createElementNS('http://www.w3.org/2000/svg','path');
    arrow.setAttribute('d','M 0 0 L 10 5 L 0 10 z'); arrow.setAttribute('fill','var(--edge)'); marker.append(arrow);
    const defs = document.createElementNS('http://www.w3.org/2000/svg','defs'); defs.append(marker); svg.append(defs);
    for (let id=1; id<9; id++) {
      const a = $(`node-${id}`).getBoundingClientRect();
      const b = $(`node-${id+1}`).getBoundingClientRect();
      const ax = a.left + a.width/2 - frame.left, ay = a.top + a.height/2 - frame.top;
      const bx = b.left + b.width/2 - frame.left, by = b.top + b.height/2 - frame.top;
      const vertical = Math.abs(bx-ax) < Math.abs(by-ay);
      const x1 = vertical ? ax : (bx>ax ? a.right-frame.left : a.left-frame.left);
      const y1 = vertical ? a.bottom-frame.top : ay;
      const x2 = vertical ? bx : (bx>ax ? b.left-frame.left : b.right-frame.left);
      const y2 = vertical ? b.top-frame.top : by;
      const line = document.createElementNS('http://www.w3.org/2000/svg','path');
      line.setAttribute('d',`M ${x1} ${y1} L ${x2} ${y2}`);
      line.setAttribute('fill','none'); line.setAttribute('stroke','var(--edge)'); line.setAttribute('stroke-width','2');
      line.setAttribute('marker-end','url(#arrow)'); svg.append(line);
    }
    if (frame.width > 720) {
      [[7,6,8,'left'], [9,4,frame.width-8,'right']].forEach(([from,to,outer,side]) => {
        const a = $(`node-${from}`).getBoundingClientRect();
        const b = $(`node-${to}`).getBoundingClientRect();
        const ax = (side === 'left' ? a.left : a.right) - frame.left;
        const bx = (side === 'left' ? b.left : b.right) - frame.left;
        const ay = a.top + a.height/2 - frame.top;
        const by = b.top + b.height/2 - frame.top;
        const line = document.createElementNS('http://www.w3.org/2000/svg','path');
        line.setAttribute('d',`M ${ax} ${ay} L ${outer} ${ay} L ${outer} ${by} L ${bx} ${by}`);
        line.setAttribute('fill','none'); line.setAttribute('stroke','var(--active)');
        line.setAttribute('stroke-width','2'); line.setAttribute('stroke-dasharray','5 5');
        line.setAttribute('marker-end','url(#arrow)'); svg.append(line);
      });
    }
  }
  select(data.stages.find(item => item.status === 'in_progress')?.id || data.stages.find(item => item.status === 'waiting')?.id || 1);
  requestAnimationFrame(drawEdges);
  window.addEventListener('resize', drawEdges);
})();
</script>
</body>
</html>'''


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    validate(data)
    embedded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    OUTPUT.write_text(HTML.replace("__DATA__", embedded), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
