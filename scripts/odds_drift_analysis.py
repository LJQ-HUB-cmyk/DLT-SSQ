"""
竞彩赔率漂移分析
================
用自建快照库 (data-raw/odds_snapshots.db) 做实证分析, 回答三个问题:

  Q1  竞彩抽水率随时间漂移吗? (市场结构在变吗?)
  Q2  哪些联赛抽水最高 / 最低?
  Q3  同一场比赛, 早盘 → 临盘的赔率和抽水率怎么变?
      → 如果临场抽水率系统性更高, 那**早盘下注更划算** (这是一个可执行的结论);
        如果没有系统性差异, 那"择时下注"是幻觉。

★ 数据限制 (必须先说清):
  - 快照只存了**赔率**, 没存比赛结果 → 本脚本**不能**检验"赔率能否预测胜负"
  - 只抓了竞彩官方 (source=jingcai), 没有境外盘口 → 不能算跨市场套利
  - 样本 425 条 / 170 场比赛, 覆盖 13 个有效日 → 统计效力有限, 只看方向, 不下重结论

用法:
  python scripts/odds_drift_analysis.py
"""
from __future__ import annotations

import collections
import sqlite3
import statistics
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

DB = PROJECT_ROOT / 'data-raw' / 'odds_snapshots.db'
CST = timezone(timedelta(hours=8))


def load():
    if not DB.exists():
        print(f'❌ 快照库不存在: {DB}')
        return []
    conn = sqlite3.connect(str(DB))
    rows = list(conn.execute(
        'SELECT ts, game, period, league, home, away, book, '
        'odds_h, odds_d, odds_a, vig, source FROM odds_snapshots ORDER BY ts'))
    conn.close()
    out = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(r[0]).astimezone(CST)
        except Exception:
            dt = None
        out.append({
            'ts': r[0], 'dt': dt,
            'game': r[1], 'period': r[2], 'league': r[3],
            'home': r[4], 'away': r[5], 'book': r[6],
            'oh': r[7], 'od': r[8], 'oa': r[9],
            'vig': float(r[10]) if r[10] is not None else None,
            'source': r[11],
        })
    return out


def bar(v, vmax, width=28, ch='█'):
    if vmax <= 0:
        return ''
    return ch * max(1, int(round(v / vmax * width)))


def main():
    rows = load()
    if not rows:
        return 1

    print()
    print('=' * 92)
    print('  竞彩赔率漂移分析 (基于自建快照库)')
    print('=' * 92)
    print(f'  快照 {len(rows)} 条 | 比赛 '
          f'{len(set((r["period"], r["home"], r["away"]) for r in rows))} 场 | '
          f'联赛 {len(set(r["league"] for r in rows))} 个')
    if rows[0]['dt'] and rows[-1]['dt']:
        print(f'  时间跨度: {rows[0]["dt"].date()} ~ {rows[-1]["dt"].date()} '
              f'(本地时区)')
    print(f'  来源: {collections.Counter(r["source"] for r in rows).most_common()}')
    print()

    # ---------- Q1 抽水率随时间 ----------
    print('  ── Q1: 抽水率随时间的漂移 ──')
    byday = collections.defaultdict(list)
    for r in rows:
        if r['vig'] is not None and r['dt']:
            byday[r['dt'].date()].append(r['vig'])
    print(f'    {"日期":<12}{"场次":>6}{"均值":>10}{"最小":>10}{"最大":>10}   分布')
    days = sorted(byday)
    allv = [v for vs in byday.values() for v in vs]
    gmean = statistics.mean(allv)
    for d in days:
        vs = byday[d]
        print(f'    {str(d):<12}{len(vs):>6}{statistics.mean(vs) * 100:>9.3f}%'
              f'{min(vs) * 100:>9.3f}%{max(vs) * 100:>9.3f}%   {bar(vs and statistics.mean(vs), 0.16)}')
    # 趋势: 前后半段对比 + 相关系数
    if len(days) >= 4:
        half = len(days) // 2
        first = [v for d in days[:half] for v in byday[d]]
        second = [v for d in days[half:] for v in byday[d]]
        m1, m2 = statistics.mean(first), statistics.mean(second)
        print(f'\n    前半段 ({days[0]}~{days[half-1]}) 均值 {m1 * 100:.3f}%  '
              f'n={len(first)}')
        print(f'    后半段 ({days[half]}~{days[-1]}) 均值 {m2 * 100:.3f}%  '
              f'n={len(second)}')
        print(f'    变化: {(m2 - m1) * 100:+.3f} 个百分点')
        # 相关系数 (日期序号 vs 抽水率)
        pts = [(i, statistics.mean(byday[d])) for i, d in enumerate(days)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        try:
            mx, my = statistics.mean(xs), statistics.mean(ys)
            cov = sum((x - mx) * (y - my) for x, y in pts)
            vx = sum((x - mx) ** 2 for x in xs) ** 0.5
            vy = sum((y - my) ** 2 for y in ys) ** 0.5
            rho = cov / (vx * vy) if vx and vy else 0.0
            n = len(pts)
            # z 分数 (Fisher 近似)
            z = rho * ((n - 2) / (1 - rho ** 2)) ** 0.5 if abs(rho) < 1 else 0.0
            print(f'    时间相关系数 ρ = {rho:+.3f}  (n={n} 天, z = {z:+.2f})')
            print(f'    → {"有" if abs(z) > 2 else "无"}显著漂移趋势 (|z| > 2 才算显著)')
        except Exception as e:
            print(f'    相关系数计算失败: {e}')
    print()

    # ---------- Q2 按联赛 ----------
    print('  ── Q2: 抽水率按联赛 (越高越贵) ──')
    bylg = collections.defaultdict(list)
    for r in rows:
        if r['vig'] is not None:
            bylg[r['league']].append(r['vig'])
    stats = []
    for lg, vs in bylg.items():
        stats.append((statistics.mean(vs), lg, len(vs), min(vs), max(vs)))
    stats.sort(reverse=True)
    vmax = stats[0][0] if stats else 0
    for mean, lg, n, lo, hi in stats:
        print(f'    {lg:<14}{n:>5} 条  均值 {mean * 100:>7.3f}%  '
              f'[{lo * 100:.2f}%~{hi * 100:.2f}%]  {bar(mean, vmax, 24)}')
    print(f'\n    全局均值 {gmean * 100:.3f}%   '
          f'跨联赛极差 {(stats[0][0] - stats[-1][0]) * 100:.3f} 个百分点')
    print()

    # ---------- Q3 早盘 → 临盘漂移 ----------
    print('  ── Q3: 同一场比赛 早盘 → 临盘 的变化 ──')
    games = collections.defaultdict(list)
    for r in rows:
        games[(r['period'], r['home'], r['away'])].append(r)
    multi = {k: v for k, v in games.items() if len(v) >= 2}
    print(f'    有 >=2 次快照的比赛: {len(multi)} 场 (共 {len(games)} 场)')

    if multi:
        deltas_vig, deltas_h, hours = [], [], []
        up_h = down_h = 0
        for k, vs in multi.items():
            vs = sorted(vs, key=lambda r: r['ts'])
            first, last = vs[0], vs[-1]
            if first['vig'] is None or last['vig'] is None:
                continue
            if first['oh'] and last['oh']:
                dh = float(last['oh']) - float(first['oh'])
                deltas_h.append(dh)
                if dh > 0:
                    up_h += 1
                elif dh < 0:
                    down_h += 1
            deltas_vig.append(float(last['vig']) - float(first['vig']))
            if first['dt'] and last['dt']:
                hours.append((last['dt'] - first['dt']).total_seconds() / 3600)

        if deltas_vig:
            n = len(deltas_vig)
            mv = statistics.mean(deltas_vig)
            sd = statistics.pstdev(deltas_vig) or 1e-12
            se = sd / (n ** 0.5)
            z = mv / se
            print(f'\n    抽水率变化 (临盘 - 早盘):')
            print(f'      n={n}  均值 {mv * 100:+.4f} 个百分点  '
                  f'标准差 {sd * 100:.4f}  标准误 {se * 100:.4f}')
            print(f'      z = {z:+.2f}  → '
                  f'{"有" if abs(z) > 2 else "无"}显著变化 (|z| > 2)')
            print(f'      上升 {sum(1 for d in deltas_vig if d > 0)} 场 / '
                  f'下降 {sum(1 for d in deltas_vig if d < 0)} 场 / '
                  f'持平 {sum(1 for d in deltas_vig if d == 0)} 场')
            if z > 2:
                print('      → 临盘抽水更高 → **早盘下注更划算** (可执行结论)')
            elif z < -2:
                print('      → 临盘抽水更低 → **临盘下注更划算** (可执行结论)')
            else:
                print('      → 抽水率在一场之内基本不动 → '
                      '"择时下注"在抽水这个维度上没有空间')

        if deltas_h:
            n = len(deltas_h)
            mv = statistics.mean(deltas_h)
            med = statistics.median(deltas_h)
            sd = statistics.pstdev(deltas_h) or 1e-12
            se = sd / (n ** 0.5)
            z = mv / se
            n_up = sum(1 for d in deltas_h if d > 0)
            n_down = sum(1 for d in deltas_h if d < 0)
            print(f'\n    主胜赔率变化 (临盘 - 早盘):')
            print(f'      n={n}  均值 {mv:+.4f}  中位数 {med:+.4f}  '
                  f'标准误 {se:.4f}  z = {z:+.2f}')
            print(f'      升 {n_up} 场 / 降 {n_down} 场')
            # ★ 均值 vs 中位数 的陷阱:
            #   均值显著(z>2)但升/降场数接近 → 说明均值被少数大幅上涨的场次拉高,
            #   **方向上并没有系统性趋势**。这时中位数才是诚实的描述。
            balanced = abs(n_up - n_down) <= max(2, n * 0.15)
            if abs(z) > 2 and (med <= 0 or balanced):
                print(f'      ⚠ 均值 z={z:+.2f} 看似显著, 但中位数 {med:+.4f} ≈ 0, '
                      f'且升 {n_up} / 降 {n_down} 接近对半 ——')
                print(f'        说明均值被少数大幅上涨的场次拉高, '
                      f'**方向上并无系统性趋势**。')
                print(f'        诚实结论: 主胜赔率漂移**没有可靠方向**, '
                      f'不能据此择时。')
            elif abs(z) > 2:
                print(f'      → 赔率整体{"上" if mv > 0 else "下"}行, '
                      f'{"上" if mv > 0 else "下"}行说明庄家对主胜的信心在'
                      f'{"增强" if mv > 0 else "减弱"}')
            else:
                print(f'      → 无显著漂移方向 (z={z:+.2f})')

        if hours:
            print(f'\n    两次快照间隔: 中位 {statistics.median(hours):.1f} 小时 '
                  f'(最短 {min(hours):.1f}h / 最长 {max(hours):.1f}h)')
    print()

    # ---------- 诚实声明 ----------
    print('  ' + '=' * 88)
    print('  【数据边界 — 这些结论不能推广到哪】')
    print('  ' + '=' * 88)
    print('    · 只有竞彩官方赔率, 没有境外盘口 → 这里**算不出**跨市场套利')
    print('    · 没有比赛结果 → 这里**检验不了**"赔率能否预测胜负"')
    print('    · 425 条 / 170 场 / 13 个有效日 → 统计效力有限, 只看方向')
    print('    · 快照日期不连续 (电脑关机 6 天) → 任何"日均"都被缺口影响')
    print('  ' + '=' * 88)
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
