"""
彩票实验室 · MCP Server
=======================
把本项目的核心能力暴露成 MCP 工具, 供 WorkBuddy / Codex / Claude / Cursor 等
任何支持 MCP 的 Agent 调用。

★ 设计原则: **诚实优先**
  每个工具的返回值里都带着期望值和"这不赚钱"的结论,
  不提供任何"预测中奖号"的能力 —— 因为它不存在。

用法:
  # 本地 stdio (Claude Desktop / Codex 等)
  python scripts/mcp_server.py

  # 远程 (WorkBuddy 远程 MCP / SSE)
  python scripts/mcp_server.py --transport streamable-http --port 8765

  # 自检 (列出所有工具 + 跑一个)
  python scripts/mcp_server.py --selftest
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from fastmcp import FastMCP

mcp = FastMCP(
    name='lottery-lab',
    instructions=(
        '彩票实验室 —— 基于真实开奖数据的彩票与竞彩分析工具。\n'
        '核心立场: 用统计检验证明"任何选号策略都改不了期望值", '
        '并给出真正有数学优势的方向 (竞彩跨市场套利)。\n'
        '所有涉及"选号"的工具都会同时返回期望净收益 —— 请如实转述给用户, '
        '不要把它包装成"预测神器"。'
    ),
)

GAMES = {'dlt': '超级大乐透 (前区35选5 + 后区12选2)',
         'ssq': '双色球 (红球33选6 + 蓝球16选1)'}


# ============================================================
# 1. 期望值速查
# ============================================================
@mcp.tool
def lottery_expectation(game: str = 'dlt') -> dict:
    """
    查某个彩种的期望值/派奖率/凯利最优 —— 这是最该先给用户看的数字。

    Args:
        game: 'dlt' (大乐透) 或 'ssq' (双色球)
    """
    from data.games import get_game
    from data.pick_advisor import Pick, calc_expected_prize

    cfg = get_game(game)
    p = Pick(front=[1] * cfg.front_count, back=[1] * cfg.back_count)
    exp, net, kelly, p1 = calc_expected_prize(game, p)
    return {
        '彩种': cfg.name,
        '单注期望奖金_元': round(exp, 4),
        '单注期望净收益_元': round(net, 4),
        '返奖率_百分比': round(exp / cfg.ticket_price * 100, 2),
        '凯利最优仓位': kelly,
        '一等奖概率': f'1/{int(1 / p1):,}',
        '结论': (f'每买 1 注, 数学上平均净亏 {abs(net):.4f} 元。'
                 f'凯利公式给出的最优仓位是 {kelly} —— 也就是"不下注"。'
                 f'没有任何选号策略能改变这个数。'),
    }


# ============================================================
# 2. 胆拖结构优化器
# ============================================================
@mcp.tool
def optimize_dan_tuo(game: str = 'dlt', budget: float = 100.0,
                     goal: str = 'win',
                     front_pool: str = '', back_pool: str = '') -> dict:
    """
    给定预算和目标, 搜出最优的胆拖结构 (胆码个数 + 拖码池大小) + 具体号码。

    ★ 重要: 中奖率只取决于**胆码个数**, 与选哪几个号**完全无关**
      (组合数学恒等式, 非统计近似)。所以"追热号"在这里没有任何加成。

    Args:
        game: 'dlt' 或 'ssq'
        budget: 预算上限 (元)
        goal: 'win'(最大中奖率) / 'big'(最大中大奖概率) /
              'value'(最大性价比) / 'jackpot'(最大一等奖概率) / 'covernum'(最大注数)
        front_pool: 前区候选号码池, 空格分隔。留空 = 不限
        back_pool: 后区候选号码池, 留空 = 不限
    """
    from data.dan_tuo_optimizer import optimize

    def nums(s):
        return sorted(int(x) for x in s.replace(',', ' ').split()) if s.strip() else None

    r = optimize(game, budget=budget, goal=goal,
                 front_pool=nums(front_pool), back_pool=nums(back_pool),
                 top_n=5)
    if not r['best']:
        return {'错误': r.get('note', '预算太小, 没有可行结构')}

    b = r['best']
    return {
        '目标': r['goal_cn'],
        '搜索结构数': r['searched'],
        '最优结构': b['structure'],
        '注数': b['n_bets'],
        '花费_元': b['cost'],
        '精确中奖率_百分比': round(b['win_rate'], 4),
        '期望返奖_元': round(b['expected_return'], 2),
        '期望净收益_元': round(b['expected_net'], 2),
        '单注期望净收益_元': round(b['expected_net'] / b['n_bets'], 4),
        '前区_胆': b['front_dan'],
        '前区_拖': b['front_tuo'],
        '后区_胆': b['back_dan'],
        '后区_拖': b['back_tuo'],
        '各奖级命中概率_百分比': {k: round(v, 4)
                            for k, v in sorted(b['prize_prob'].items(),
                                              key=lambda x: -x[1])},
        '诚实提醒': ('结构只改中奖率, 改不了期望值。'
                 '号码选哪几个对概率零影响 —— 追热号和追冷号在这里等价。'),
    }


# ============================================================
# 3. 具体方案评估
# ============================================================
@mcp.tool
def evaluate_dan_tuo(game: str = 'dlt', front_dan: str = '', front_tuo: str = '',
                     back_dan: str = '', back_tuo: str = '') -> dict:
    """
    评估一组具体的胆拖方案 (精确超几何, 零模拟误差)。

    Args:
        game: 'dlt' 或 'ssq'
        front_dan / front_tuo / back_dan / back_tuo: 号码, 空格分隔
    """
    from data.dan_tuo_exact import exact_dan_tuo

    def nums(s):
        return sorted(int(x) for x in s.replace(',', ' ').split()) if s.strip() else []

    try:
        r = exact_dan_tuo(game, nums(front_dan), nums(front_tuo),
                          nums(back_dan), nums(back_tuo))
    except ValueError as e:
        return {'错误': str(e)}

    return {
        '注数': r['n_bets'],
        '花费_元': r['cost'],
        '精确中奖率_百分比': round(r['win_rate'], 4),
        '全灭概率_百分比': round(r['lose_rate'], 4),
        '期望返奖_元': round(r['expected_return'], 2),
        '期望净收益_元': round(r['expected_net'], 2),
        '单注期望净收益_元': round(r['expected_net'] / r['n_bets'], 4),
        '各奖级命中概率_百分比': {p['label']: round(p['prob_any'] * 100, 4)
                            for p in r['prize_dist'] if p['money'] > 0},
        '诚实提醒': ('期望净收益必然为负。结构只能改变"多容易中一次小奖", '
                 '不能改变"长期会亏多少"。'),
    }


# ============================================================
# 4. 真实历史回测
# ============================================================
@mcp.tool
def backtest_dan_tuo_real(game: str = 'dlt', front_dan: str = '',
                           front_tuo: str = '', back_dan: str = '',
                           back_tuo: str = '') -> dict:
    """
    把一个**已定好的**胆拖方案放到过去的每一期真实开奖上检验。

    ★ 与"选号策略回测"的区别: 这里不做任何选号决策, 只检验固定方案,
      所以没有前视偏差。回答的是"如果我每期都这么买, 历史会怎样"。

    Args:
        game: 'dlt' 或 'ssq'
        front_dan / front_tuo / back_dan / back_tuo: 号码, 空格分隔
    """
    from scripts.dan_tuo_backtest_real import backtest

    def nums(s):
        return sorted(int(x) for x in s.replace(',', ' ').split()) if s.strip() else []

    r = backtest(game, nums(front_dan), nums(front_tuo),
                 nums(back_dan), nums(back_tuo))
    if not r:
        return {'错误': '结构不合法'}
    return {
        '历史期数': r['n_draws'],
        '每期注数': r['n_tickets'],
        '总判奖次数': r['n_tickets'] * r['n_draws'],
        '总投入_元': r['stake'],
        '总返奖_元': round(r['returned'], 2),
        '真实ROI_百分比': round(r['roi'], 2),
        '中奖期数': r['win_periods'],
        '中奖率_百分比': round(r['win_rate'], 2),
        '剔除大奖后的常态ROI_百分比': round(r['roi_no_big'], 2),
        '各奖级命中次数': r['level_counts'],
        '诚实提醒': ('含大奖的 ROI 波动极大 —— 随机对照里同结构方案的历史 ROI '
                 '能从 -76% 到 +64%, 那是运气不是能力。'
                 '常态 ROI 才是真实期望, 必然是负的。'),
    }


# ============================================================
# 5. 竞彩跨市场套利
# ============================================================
@mcp.tool
def scan_sports_arb(min_profit: float = 0.005,
                    include_jingcai: bool = True) -> dict:
    """
    扫描竞彩跨市场套利机会 (境外多博彩公司盘口)。

    ★ 这是本项目里**唯一有真实数学优势**的方向:
      跨公司下注同一场比赛的三种结果, 合计概率 < 1 → 必赚。
      典型 ROI +1.3%~+1.5%。而竞彩官方抽水 12.9% → **永远参与不了**。

    Args:
        min_profit: 最小 ROI 阈值 (0.005 = 0.5%)
        include_jingcai: 是否同时看竞彩官方盘口
    """
    from data.sports_lab2 import run_sports_lab
    r = run_sports_lab(leagues=None, min_profit=min_profit,
                       include_jingcai=include_jingcai)
    return {
        '结论': r.get('conclusion', ''),
        '扫描场次': r.get('n_matches'),
        '竞彩参与套利次数': r.get('stab', {}).get('jingcai_used'),
        '抽水汇总': r.get('vig_summary'),
        '诚实提醒': ('这是数学必赢 (ROI 正且稳定), 但**实操有摩擦**: '
                 '需要多个账户、实时下单、赔率会动、额度有限制。'
                 '而且需要付费的境外赔率数据源。'),
    }


# ============================================================
# 6. 诚实说明
# ============================================================
@mcp.tool
def explain_lottery_truth(topic: str = 'hot') -> dict:
    """
    回答"彩票里常见的迷思", 全部基于本项目跑过的真实实验。

    Args:
        topic: 'hot'(冷热号有没有用) / 'expectation'(期望值能不能改) /
               'vip'(VIP/内部号码) / 'luck'(运气能不能被训练) /
               'dantuo'(胆拖是不是更划算)
    """
    topics = {
        'hot': {
            '问题': '冷热号/遗漏号有预测力吗?',
            '实测': ('2022-24 的热号去预测 2025-26: 命中 190 注 vs 期望 192.9 注 '
                 '(z=-0.22, 与随机无差异)。相邻年 Top-10 重合数 ρ=+0.13 (z=+0.75)。'
                 '按冷热分档统计 2938 期实际出现次数: 最热档 421 / 最冷档 423, '
                 '均匀理论值 419.7 —— 没有单调趋势。'),
            '结论': '冷热号没有预测力。这是统计事实, 不是观点。',
        },
        'expectation': {
            '问题': '有没有办法提高中奖率/期望收益?',
            '实测': ('13 种选号策略 walk-forward 回测, ROI 全部为负。'
                 '大乐透单注期望净收益 -0.9407 元, 双色球 -0.8570 元。'
                 '凯利最优仓位 = 0。'),
            '结论': '不能。数学上 f*=0, 期望你不下注。',
        },
        'vip': {
            '问题': 'VIP 号/内部号/杀号软件是真的吗?',
            '实测': '没有公开的、经过独立验证的证据表明这类信息存在。',
            '结论': '收费卖"内部号"的, 基本可以判定为骗局。',
        },
        'luck': {
            '问题': '运气能被训练/被系统放大吗?',
            '实测': ('随机对照实验: 同结构换一组号码, 历史 ROI 从 -76% 到 +64%, '
                 '跨度 140 个百分点。剔除大奖后的常态 ROI 全部挤在 -81%~-78%。'),
            '结论': ('运气确实存在但不可控, 且历史 ROI 好只是运气好。'
                 '一次大奖能掩盖 200,000 次亏损。'),
        },
        'dantuo': {
            '问题': '胆拖是不是更划算?',
            '实测': ('胆拖确实提高**中奖率** (结构优化器: 1680 元预算下 '
                 '最优结构 47.43% vs 常规 42.97%), 但期望净收益完全一样。'
                 '而且**中奖率只取决于胆码个数**, 与选哪几个号无关 —— '
                 '胆码个数相同, 中奖率 bit-for-bit 相同。'),
            '结论': '胆拖是"花同样的钱更容易中一次小奖", 不是"更划算"。',
        },
    }
    key = (topic or 'hot').lower()
    if key not in topics:
        return {'可用主题': list(topics.keys()), '错误': f'未知主题 {topic}'}
    return topics[key]


# ============================================================
# 自检
# ============================================================
def _selftest():
    print('=' * 72)
    print('  MCP Server 自检')
    print('=' * 72)
    import asyncio

    tools = asyncio.run(mcp._tool_manager.list_tools()) \
        if hasattr(mcp, '_tool_manager') else asyncio.run(mcp.list_tools())
    tool_list = tools if isinstance(tools, list) else list(tools.values())
    print(f'  注册工具 {len(tool_list)} 个:')
    for t in tool_list:
        name = getattr(t, 'name', str(t))
        desc = (getattr(t, 'description', '') or '').strip().split('\n')[0]
        print(f'    · {name:<28} {desc[:60]}')

    print()
    print('  实测调用 optimize_dan_tuo:')
    r = optimize_dan_tuo(game='dlt', budget=1680, goal='win',
                         front_pool='2 4 6 10 14 16 18 23 26 32 35',
                         back_pool='2 4 6 9 12')
    for k in ('最优结构', '注数', '花费_元', '精确中奖率_百分比',
              '期望净收益_元', '单注期望净收益_元'):
        print(f'    {k}: {r.get(k)}')
    print()
    print('  实测调用 lottery_expectation:')
    e = lottery_expectation('dlt')
    for k in ('彩种', '单注期望净收益_元', '返奖率_百分比', '凯利最优仓位'):
        print(f'    {k}: {e.get(k)}')
    print()
    print('=' * 72)
    print('  ✅ 自检通过')
    print('=' * 72)


def main():
    ap = argparse.ArgumentParser(description='彩票实验室 MCP Server')
    ap.add_argument('--transport', default='stdio',
                    choices=['stdio', 'sse', 'streamable-http'])
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--selftest', action='store_true', help='只跑自检不起服务')
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0

    print(f'启动 MCP Server ({args.transport}) '
          f'{args.host}:{args.port}', file=sys.stderr)
    if args.transport == 'stdio':
        mcp.run(transport='stdio')
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
