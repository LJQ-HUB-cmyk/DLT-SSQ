"""
竞彩赔率漂移分析图
==================
把 scripts/odds_drift_analysis.py 的三个结论画出来:
  ① 抽水率随时间 (极稳定, 无显著漂移)
  ② 抽水率按联赛 (全局 13.87%, 跨联赛极差 1.08pp)
  ③ 早盘 → 临盘 漂移 (抽水率不动; 赔率方向无系统性)

用法:
  python scripts/make_odds_drift_chart.py
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

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _f in ('Microsoft YaHei', 'Noto Sans SC', 'SimHei'):
    if any(f.name == _f for f in font_manager.fontManager.ttflist):
        plt.rcParams['font.sans-serif'] = [_f]
        break
plt.rcParams['axes.unicode_minus'] = False

DB = PROJECT_ROOT / 'data-raw' / 'odds_snapshots.db'
REPORTS = PROJECT_ROOT / 'reports'
CST = timezone(timedelta(hours=8))

C_DARK = '#0f172a'
C_GRAY = '#64748b'
C_RED = '#dc2626'
C_BLUE = '#2563eb'
C_GREEN = '#059669'
C_AMBER = '#d97706'


def load():
    conn = sqlite3.connect(str(DB))
    rows = list(conn.execute(
        'SELECT ts, period, league, home, away, odds_h, odds_d, odds_a, vig '
        'FROM odds_snapshots ORDER BY ts'))
    conn.close()
    out = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(r[0]).astimezone(CST)
        except Exception:
            dt = None
        out.append({'ts': r[0], 'dt': dt, 'period': r[1], 'league': r[2],
                    'home': r[3], 'away': r[4],
                    'oh': r[5], 'vig': float(r[8]) if r[8] is not None else None})
    return out


def main():
    rows = load()
    if not rows:
        print('❌ 无快照数据')
        return 1

    fig = plt.figure(figsize=(18.5, 6.6))
    fig.patch.set_facecolor('white')
    gs = fig.add_gridspec(1, 4, width_ratios=[1.05, 0.95, 0.85, 0.95],
                          wspace=0.32, left=0.05, right=0.985,
                          top=0.815, bottom=0.175)

    # ---------- ① 抽水率随时间 ----------
    ax = fig.add_subplot(gs[0, 0])
    byday = collections.defaultdict(list)
    for r in rows:
        if r['vig'] is not None and r['dt']:
            byday[r['dt'].date()].append(r['vig'])
    days = sorted(byday)
    xs = list(range(len(days)))
    ys = [statistics.mean(byday[d]) * 100 for d in days]
    ns = [len(byday[d]) for d in days]
    gmean = statistics.mean([v for vs in byday.values() for v in vs]) * 100
    ax.bar(xs, ys, 0.62, color=C_BLUE, alpha=0.85, edgecolor='white',
           linewidth=1.2, zorder=3)
    ax.axhline(gmean, color=C_AMBER, lw=2.0, ls='--', zorder=4)
    ax.text(len(days) - 0.4, gmean + 0.012, f'全局均值 {gmean:.3f}%',
            ha='right', fontsize=9.2, color=C_AMBER, fontweight='bold')
    for i, (y, n) in enumerate(zip(ys, ns)):
        ax.text(i, y + 0.006, f'{y:.2f}', ha='center', fontsize=7.6,
                color=C_DARK)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(d)[5:] for d in days], fontsize=8, rotation=45,
                       ha='right')
    ax.set_ylabel('竞彩抽水率 (%)', fontsize=10.5, color=C_DARK)
    ax.set_ylim(min(ys) - 0.06, max(ys) + 0.09)
    ax.set_title('① 抽水率几乎不动', fontsize=13.5, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015,
            f'13 天 ρ=+0.47 但 z=+1.77 → 无显著漂移 (柱高=条数, 标签=均值)',
            transform=ax.transAxes, ha='center', fontsize=9.0, color=C_GRAY)
    ax.grid(axis='y', alpha=0.25, ls='--')
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    # ---------- ② 按联赛 ----------
    ax = fig.add_subplot(gs[0, 1])
    bylg = collections.defaultdict(list)
    for r in rows:
        if r['vig'] is not None:
            bylg[r['league']].append(r['vig'])
    stats = sorted(((statistics.mean(v), lg, len(v))
                    for lg, v in bylg.items()), reverse=True)
    top = stats[:12]
    labs = [t[1] for t in top][::-1]
    vals = [t[0] * 100 for t in top][::-1]
    ns = [t[2] for t in top][::-1]
    cols = [C_GREEN if v >= gmean else C_GRAY for v in vals]
    ax.barh(range(len(labs)), vals, 0.66, color=cols, alpha=0.9,
            edgecolor='white', linewidth=1.1, zorder=3)
    ax.axvline(gmean, color=C_AMBER, lw=2.0, ls='--', zorder=4)
    ax.set_yticks(range(len(labs)))
    ax.set_yticklabels(labs, fontsize=9)
    for i, (v, n) in enumerate(zip(vals, ns)):
        ax.text(v + 0.004, i, f'{v:.2f}%  (n={n})', va='center',
                fontsize=7.8, color=C_DARK)
    ax.set_xlim(min(vals) - 0.02, max(vals) + 0.14)
    ax.set_xlabel('抽水率 (%)  —  越高越贵', fontsize=10.5, color=C_DARK)
    ax.set_title('② 跨联赛差异很小', fontsize=13.5, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015,
            f'前 12 联赛 · 全局 13.87% · 极差仅 1.08pp (且由小样本造成)',
            transform=ax.transAxes, ha='center', fontsize=9.0, color=C_GRAY)
    ax.grid(axis='x', alpha=0.25, ls='--')
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    # ---------- ③ 抽水率变化 (独立面板, 放大 x 轴) ----------
    ax = fig.add_subplot(gs[0, 2])
    # 先算同一场比赛 早盘→临盘 的变化
    games = collections.defaultdict(list)
    for r in rows:
        games[(r['period'], r['home'], r['away'])].append(r)
    dv, dh = [], []
    for k, vs in games.items():
        if len(vs) < 2:
            continue
        vs = sorted(vs, key=lambda r: r['ts'])
        f, l = vs[0], vs[-1]
        if f['vig'] is not None and l['vig'] is not None:
            dv.append((l['vig'] - f['vig']) * 100)
        if f['oh'] and l['oh']:
            dh.append(float(l['oh']) - float(f['oh']))
    if dv:
        ax.hist(dv, bins=26, color=C_BLUE, alpha=0.85, edgecolor='white',
                linewidth=0.8, zorder=3)
        mv = statistics.mean(dv)
        sd = statistics.pstdev(dv) or 1e-12
        z = mv / (sd / (len(dv) ** 0.5))
        ax.axvline(0, color=C_DARK, lw=1.2, zorder=4)
        ax.axvline(mv, color=C_RED, lw=2.0, ls='--', zorder=5)
        ax.text(mv, ax.get_ylim()[1] * 0.95,
                f'均值 {mv:+.4f}pp\nz = {z:+.2f}',
                fontsize=9, color=C_RED, fontweight='bold', ha='left', va='top')
    ax.set_xlabel('抽水率变化 (临盘 - 早盘, 个百分点)', fontsize=9.6,
                  color=C_DARK)
    ax.set_ylabel('场次数', fontsize=10.5, color=C_DARK)
    ax.set_title('③ 一场之内: 抽水率不动', fontsize=13, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015, 'n=114 · z=+1.14 → 无显著变化',
            transform=ax.transAxes, ha='center', fontsize=8.8, color=C_GRAY)
    ax.grid(axis='y', alpha=0.22, ls='--')
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    # ---------- ④ 主胜赔率变化 ----------
    ax = fig.add_subplot(gs[0, 3])
    if dh:
        ax.hist(dh, bins=30, color=C_AMBER, alpha=0.82, edgecolor='white',
                linewidth=0.8, zorder=3)
        mh = statistics.mean(dh)
        med = statistics.median(dh)
        sd = statistics.pstdev(dh) or 1e-12
        z = mh / (sd / (len(dh) ** 0.5))
        n_up = sum(1 for d in dh if d > 0)
        n_down = sum(1 for d in dh if d < 0)
        ax.axvline(0, color=C_DARK, lw=1.2, zorder=4)
        ax.axvline(mh, color=C_RED, lw=2.0, ls='--', zorder=5)
        ax.text(mh, ax.get_ylim()[1] * 0.96,
                f'均值 {mh:+.3f} (z={z:+.2f})\n中位数 {med:+.3f} ≈ 0\n'
                f'升 {n_up} / 降 {n_down}',
                fontsize=9, color=C_RED, fontweight='bold', ha='left', va='top')
    ax.set_xlabel('主胜赔率变化 (临盘 - 早盘)', fontsize=9.6, color=C_DARK)
    ax.set_ylabel('场次数', fontsize=10.5, color=C_DARK)
    ax.set_title('④ 赔率漂移: 均值假象', fontsize=13, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015, 'z=+2.60 看似显著, 但中位数≈0 → 无可靠方向',
            transform=ax.transAxes, ha='center', fontsize=8.8, color=C_GRAY)
    ax.grid(axis='y', alpha=0.22, ls='--')
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    fig.suptitle('竞彩赔率漂移: 三个"没有空间"的结论',
                 fontsize=18, fontweight='bold', color=C_DARK, y=0.965)
    fig.text(0.5, 0.905,
             f'自建快照库 {len(rows)} 条 / {len(games)} 场 / {len(byday)} 个有效日 · '
             f'仅竞彩官方赔率 (无境外盘口, 无比赛结果)',
             ha='center', fontsize=11, color=C_GRAY)
    fig.text(0.5, 0.045,
             '结论: 抽水率稳定在 13.87% 且一场之内不动 → '
             '"择时下注"在抽水维度没有空间; 赔率漂移也没有可靠方向 → 不能据此择时',
             ha='center', fontsize=11.5, color=C_RED, fontweight='bold')

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / 'headline_odds_drift.png'
    fig.savefig(out, dpi=145, bbox_inches='tight', facecolor='white',
                pad_inches=0.3)
    plt.close(fig)
    print(f'✅ 已生成: {out}  ({out.stat().st_size / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
