"""
lottery_lab.py — 彩票实验室命令行客户端 (Skill 用)

直接调用本地项目模块, 不依赖 MCP。优先从 LOTTERY_PROJECT_ROOT 环境变量
或常见路径找项目根; 找不到就提示怎么配。

子命令:
  expectation <dlt|ssq>              期望值/派奖率/凯利
  optimize  --budget N --goal G      胆拖结构优化
  evaluate  --front-dan ... --back-dan ...   具体方案评估 (精确)
  backtest  --front-dan ... ...      真实历史回测
  arb                                竞彩跨市场套利扫描
  truth <topic>                      常见迷思的真答案
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def find_project_root() -> Path:
    env = os.environ.get('LOTTERY_PROJECT_ROOT')
    cands = []
    if env:
        cands.append(Path(env))
    cands += [
        Path(__file__).resolve().parent.parent.parent,   # skill/lottery-lab/scripts -> 项目根
        Path(r'D:\工作区\体育彩票预测项目'),
        Path.cwd(),
    ]
    for c in cands:
        try:
            if (c / 'data' / 'games.py').exists() and (c / 'scripts').exists():
                return c
        except Exception:
            continue
    raise SystemExit(
        '❌ 找不到彩票实验室项目目录。\n'
        '   请设置环境变量:  set LOTTERY_PROJECT_ROOT=D:\\工作区\\体育彩票预测项目\n'
        '   (Windows: setx LOTTERY_PROJECT_ROOT "D:\\工作区\\体育彩票预测项目")')


def main():
    ap = argparse.ArgumentParser(description='彩票实验室 CLI')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('expectation')
    p.add_argument('game', nargs='?', default='dlt', choices=['dlt', 'ssq'])

    p = sub.add_parser('optimize')
    p.add_argument('--game', default='dlt', choices=['dlt', 'ssq'])
    p.add_argument('--budget', type=float, default=100.0)
    p.add_argument('--goal', default='win',
                   choices=['win', 'big', 'value', 'jackpot', 'covernum'])
    p.add_argument('--front-pool', default='')
    p.add_argument('--back-pool', default='')

    for name in ('evaluate', 'backtest'):
        p = sub.add_parser(name)
        p.add_argument('--game', default='dlt', choices=['dlt', 'ssq'])
        p.add_argument('--front-dan', default='')
        p.add_argument('--front-tuo', default='')
        p.add_argument('--back-dan', default='')
        p.add_argument('--back-tuo', default='')

    p = sub.add_parser('arb')
    p.add_argument('--min-profit', type=float, default=0.005)
    p.add_argument('--no-jingcai', action='store_true')

    p = sub.add_parser('truth')
    p.add_argument('topic', nargs='?', default='hot',
                   choices=['hot', 'expectation', 'vip', 'luck', 'dantuo'])

    args = ap.parse_args()
    root = find_project_root()
    sys.path.insert(0, str(root))

    def nums(s):
        return sorted(int(x) for x in s.replace(',', ' ').split()) if s.strip() else []

    out = {}
    if args.cmd == 'expectation':
        from data.games import get_game
        from data.pick_advisor import Pick, calc_expected_prize
        cfg = get_game(args.game)
        p = Pick(front=[1] * cfg.front_count, back=[1] * cfg.back_count)
        exp, net, kelly, p1 = calc_expected_prize(args.game, p)
        out = {'彩种': cfg.name, '单注期望奖金_元': round(exp, 4),
               '单注期望净收益_元': round(net, 4),
               '返奖率_百分比': round(exp / cfg.ticket_price * 100, 2),
               '凯利最优仓位': kelly,
               '一等奖概率': f'1/{int(1 / p1):,}',
               '结论': f'每买 1 注平均净亏 {abs(net):.4f} 元, 凯利最优是 {kelly} (不下注)'}

    elif args.cmd == 'optimize':
        from data.dan_tuo_optimizer import optimize
        r = optimize(args.game, budget=args.budget, goal=args.goal,
                     front_pool=nums(args.front_pool) or None,
                     back_pool=nums(args.back_pool) or None, top_n=5)
        if not r['best']:
            out = {'错误': r.get('note', '预算太小')}
        else:
            b = r['best']
            out = {'目标': r['goal_cn'], '最优结构': b['structure'],
                   '注数': b['n_bets'], '花费_元': b['cost'],
                   '精确中奖率_百分比': round(b['win_rate'], 4),
                   '期望净收益_元': round(b['expected_net'], 2),
                   '单注期望净收益_元': round(b['expected_net'] / b['n_bets'], 4),
                   '前区_胆': b['front_dan'], '前区_拖': b['front_tuo'],
                   '后区_胆': b['back_dan'], '后区_拖': b['back_tuo'],
                   '各奖级命中概率_百分比': {
                       k: round(v, 4) for k, v in
                       sorted(b['prize_prob'].items(), key=lambda x: -x[1])},
                   '提醒': '结构只改中奖率, 改不了期望值; 号码选哪几个对概率零影响'}

    elif args.cmd == 'evaluate':
        from data.dan_tuo_exact import exact_dan_tuo
        try:
            r = exact_dan_tuo(args.game, nums(args.front_dan), nums(args.front_tuo),
                              nums(args.back_dan), nums(args.back_tuo))
        except ValueError as e:
            out = {'错误': str(e)}
        else:
            out = {'注数': r['n_bets'], '花费_元': r['cost'],
                   '精确中奖率_百分比': round(r['win_rate'], 4),
                   '全灭概率_百分比': round(r['lose_rate'], 4),
                   '期望返奖_元': round(r['expected_return'], 2),
                   '期望净收益_元': round(r['expected_net'], 2),
                   '单注期望净收益_元': round(r['expected_net'] / r['n_bets'], 4),
                   '各奖级命中概率_百分比': {
                       p['label']: round(p['prob_any'] * 100, 4)
                       for p in r['prize_dist'] if p['money'] > 0}}

    elif args.cmd == 'backtest':
        from scripts.dan_tuo_backtest_real import backtest
        r = backtest(args.game, nums(args.front_dan), nums(args.front_tuo),
                     nums(args.back_dan), nums(args.back_tuo))
        if not r:
            out = {'错误': '结构不合法'}
        else:
            out = {'历史期数': r['n_draws'], '每期注数': r['n_tickets'],
                   '总判奖次数': r['n_tickets'] * r['n_draws'],
                   '总投入_元': r['stake'],
                   '真实ROI_百分比': round(r['roi'], 2),
                   '中奖率_百分比': round(r['win_rate'], 2),
                   '剔除大奖后的常态ROI_百分比': round(r['roi_no_big'], 2),
                   '各奖级命中次数': r['level_counts'],
                   '提醒': '含大奖ROI受运气支配 (随机对照能到 +64%), 常态ROI才是真实期望'}

    elif args.cmd == 'arb':
        from data.sports_lab2 import run_sports_lab
        r = run_sports_lab(leagues=None, min_profit=args.min_profit,
                           include_jingcai=not args.no_jingcai)
        out = {'结论': r.get('conclusion', ''),
               '扫描场次': r.get('n_matches'),
               '抽水汇总': r.get('vig_summary'),
               '提醒': '数学必赢但实操有摩擦: 多账户/实时下单/赔率会动/额度限制'}

    else:  # truth
        from scripts.mcp_server import explain_lottery_truth
        out = explain_lottery_truth(args.topic)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
