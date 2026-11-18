"""
胆拖方案真实历史回测 · 结果图
==============================
三联图:
  ① 你的方案 vs 优化器最优: 中奖率 / 含大奖ROI / 常态ROI
  ② 随机对照组的真实 ROI 分布 —— 展示"运气能有多大"
  ③ 随机对照的常态 ROI 分布 —— 展示"结构改不了亏损"

用法:
  python scripts/make_backtest_real_chart.py
"""
from __future__ import annotations

import sys
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

from scripts.dan_tuo_backtest_real import backtest, random_control
from data.dan_tuo_optimizer import optimize

REPORTS = PROJECT_ROOT / 'reports'
C_DARK = '#0f172a'
C_GRAY = '#64748b'
C_RED = '#dc2626'
C_BLUE = '#2563eb'
C_GREEN = '#059669'
C_AMBER = '#d97706'

FP = [2, 4, 6, 10, 14, 16, 18, 23, 26, 32, 35]
BP = [2, 4, 6, 9, 12]
N_CTRL = 12


def main():
    r1 = backtest('dlt', [6], [x for x in FP if x != 6], [4], [x for x in BP if x != 4])
    ro = optimize('dlt', budget=1680, goal='win', front_pool=FP, back_pool=BP,
                  top_n=1)
    b = ro['best']
    r2 = backtest('dlt', b['front_dan'], b['front_tuo'],
                   b['back_dan'], b['back_tuo'])
    ctrl = random_control('dlt', len(FP), len(BP), b['k'], b['m'], N_CTRL, 20261118)
    rois = [c['roi'] for c in ctrl]
    rois_nb = [c['roi_no_big'] for c in ctrl]

    fig = plt.figure(figsize=(17.5, 6.6))
    fig.patch.set_facecolor('white')
    gs = fig.add_gridspec(1, 3, width_ratios=[0.95, 1.25, 1.0],
                          wspace=0.28, left=0.055, right=0.982,
                          top=0.815, bottom=0.175)

    # ---------- ① 两个方案对比 ----------
    ax = fig.add_subplot(gs[0, 0])
    x = np.arange(2)
    w = 0.26
    ax.bar(x - w, [r1['win_rate'], r2['win_rate']], w, label='中奖率 %',
           color=C_BLUE, edgecolor='white', linewidth=1.2, zorder=3)
    ax.bar(x, [r1['roi'], r2['roi']], w, label='含大奖 ROI %',
           color=C_AMBER, edgecolor='white', linewidth=1.2, zorder=3)
    ax.bar(x + w, [r1['roi_no_big'], r2['roi_no_big']], w,
           label='常态 ROI % (剔除大奖)', color=C_RED, edgecolor='white',
           linewidth=1.2, zorder=3)
    for i, (a, c, d) in enumerate([(r1['win_rate'], r1['roi'], r1['roi_no_big']),
                                   (r2['win_rate'], r2['roi'], r2['roi_no_big'])]):
        for off, v in ((-w, a), (0, c), (w, d)):
            ax.text(i + off, v + (3 if v >= 0 else -9), f'{v:.1f}',
                    ha='center', fontsize=8.2, color=C_DARK, fontweight='bold')
    ax.axhline(0, color=C_DARK, lw=1.2, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels(['你的方案\n1前胆/1后胆', '优化器最优\n2前胆/0后胆'],
                       fontsize=9.5)
    ax.set_ylabel('%', fontsize=10.5, color=C_DARK)
    ax.set_title('① 同一预算, 两个结构', fontsize=13.5, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015,
            f'真实历史 {r1["n_draws"]:,} 期 × 840 注 = '
            f'{r1["n_tickets"] * r1["n_draws"]:,} 次判奖',
            transform=ax.transAxes, ha='center', fontsize=9.0, color=C_GRAY)
    ax.legend(fontsize=8.4, frameon=False, loc='lower right')
    ax.grid(axis='y', alpha=0.25, ls='--')
    ax.set_axisbelow(True)
    ax.set_ylim(-105, 62)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    # ---------- ② 含大奖 ROI 分布 ----------
    ax = fig.add_subplot(gs[0, 1])
    idx = sorted(range(len(rois)), key=lambda i: rois[i])
    vals = [rois[i] for i in idx]
    cols = [C_GREEN if v > 0 else C_RED for v in vals]
    ax.bar(range(len(vals)), vals, 0.68, color=cols, alpha=0.85,
           edgecolor='white', linewidth=1.1, zorder=3)
    ax.axhline(0, color=C_DARK, lw=1.4, zorder=5)
    ax.axhline(r2['roi'], color=C_AMBER, lw=2.2, ls='--', zorder=6)
    ax.text(len(vals) - 0.4, r2['roi'] + 4,
            f'优化器方案 {r2["roi"]:+.1f}%', ha='right', fontsize=9.4,
            color=C_AMBER, fontweight='bold')
    for i, v in enumerate(vals):
        ax.text(i, v + (5 if v >= 0 else -14), f'{v:+.0f}', ha='center',
                fontsize=8, color=C_DARK)
    ax.set_xticks([])
    ax.set_xlabel(f'{len(vals)} 组随机同规模号码池 (前11后5, 胆2/0)',
                  fontsize=10, color=C_DARK)
    ax.set_ylabel('真实历史 ROI (%)', fontsize=10.5, color=C_DARK)
    ax.set_title('② 运气能有多大', fontsize=13.5, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015,
            f'跨度 {max(vals) - min(vals):.0f} 个百分点! 有一组历史 ROI 为正 '
            f'→ "历史赚钱"可能只是撞上了大奖',
            transform=ax.transAxes, ha='center', fontsize=9.0, color=C_GRAY)
    ax.grid(axis='y', alpha=0.25, ls='--')
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    # ---------- ③ 常态 ROI 分布 ----------
    ax = fig.add_subplot(gs[0, 2])
    idx2 = sorted(range(len(rois_nb)), key=lambda i: rois_nb[i])
    vals2 = [rois_nb[i] for i in idx2]
    ax.bar(range(len(vals2)), vals2, 0.68, color=C_BLUE, alpha=0.85,
           edgecolor='white', linewidth=1.1, zorder=3)
    ax.axhline(r2['roi_no_big'], color=C_AMBER, lw=2.2, ls='--', zorder=6)
    ax.text(len(vals2) - 0.4, r2['roi_no_big'] + 0.25,
            f'优化器 {r2["roi_no_big"]:+.2f}%', ha='right', fontsize=9.4,
            color=C_AMBER, fontweight='bold')
    ax.axhline(r1['roi_no_big'], color=C_RED, lw=1.8, ls=':', zorder=6)
    ax.text(len(vals2) - 0.4, r1['roi_no_big'] - 0.75,
            f'你的 {r1["roi_no_big"]:+.2f}%', ha='right', fontsize=9.4,
            color=C_RED, fontweight='bold')
    ax.set_xticks([])
    ax.set_xlabel(f'同样 {len(vals2)} 组随机号码池 (剔除 ≥1万 的大奖期)',
                  fontsize=10, color=C_DARK)
    ax.set_ylabel('常态 ROI (%)', fontsize=10.5, color=C_DARK)
    ax.set_title('③ 结构改不了亏损', fontsize=13.5, fontweight='bold',
                 color=C_DARK, pad=26)
    ax.text(0.5, 1.015,
            f'全部挤在 {min(vals2):+.2f}% ~ {max(vals2):+.2f}% '
            f'(跨度仅 {max(vals2) - min(vals2):.2f}pp)',
            transform=ax.transAxes, ha='center', fontsize=9.0, color=C_GRAY)
    ax.grid(axis='y', alpha=0.25, ls='--')
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color('#cbd5e1')

    fig.suptitle('真实历史回测: 期望值铁律, 一次判奖 247 万次',
                 fontsize=18, fontweight='bold', color=C_DARK, y=0.965)
    fig.text(0.5, 0.905,
             f'超级大乐透 {r1["n_draws"]:,} 期真实开奖 · '
             f'每个方案 {r1["n_tickets"]:,} 注/期 · 精确超几何判奖 · '
             f'随机对照 {len(vals2)} 组',
             ha='center', fontsize=11, color=C_GRAY)
    fig.text(0.5, 0.045,
             '结论: 含大奖 ROI 能在 -76% ~ +64% 之间乱跳 (纯运气), '
             '但常态 ROI 全部挤在 -81% ~ -78% —— 任何结构都在亏, 结构只改中奖率',
             ha='center', fontsize=11.5, color=C_RED, fontweight='bold')

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / 'headline_backtest_real.png'
    fig.savefig(out, dpi=145, bbox_inches='tight', facecolor='white',
                pad_inches=0.3)
    plt.close(fig)
    print(f'✅ 已生成: {out}  ({out.stat().st_size / 1024:.0f} KB)')


if __name__ == '__main__':
    import numpy as np
    main()
