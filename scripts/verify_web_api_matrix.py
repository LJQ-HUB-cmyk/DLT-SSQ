"""
Web GUI 全端点 × 双彩种 实测
============================
逐个调用所有 API, 对 DLT 和 SSQ 各跑一遍, 输出"能不能用 / 报什么错"。

用途: 用户要自己上手测, 得先知道每个 Tab 在双色球下到底能不能跑 ——
      不能让他到家点一下发现是 DLT-only 的。

用法:
  python scripts/verify_web_api_matrix.py
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from scripts.pick_gui import app

# (Tab 名, 端点, 请求体模板)
CASES = [
    ('① 历史期验证', '/api/check',
     {'game': '{g}', 'period': '{period}', 'front': [1, 2, 3, 4, 5], 'back': [1, 2]}),
    ('② 算法评分', '/api/score',
     {'game': '{g}', 'front': [1, 2, 3, 4, 5], 'back': [1, 2], 'window': 300}),
    ('④ 预测玩法回测', '/api/strategy-lab',
     {'game': '{g}', 'train_years': 3, 'test_years': 1,
      'strategies': ['random', 'hot']}),
    ('⑤ 快速算账', '/api/quick-settle',
     {'game': '{g}', 'stake': 1680, 'returned': 200}),
    ('⑥ 热号幻觉', '/api/hot-illusion',
     {'game': '{g}', 'train_start': 2018, 'train_end': 2022,
      'test_start': 2023, 'test_end': 2024, 'pick_n': 5}),
    ('⑩ 结构优化器', '/api/dan-tuo-optimize',
     {'game': '{g}', 'budget': 1680, 'goal': 'win'}),
    ('③ 胆拖分析', '/api/dan-tuo',
     {'game': '{g}', 'front_dan': [1], 'front_tuo': [2, 3, 4, 5, 6, 7],
      'back_dan': [1], 'back_tuo': [2, 3, 4], 'draws': 2000}),
    ('⑦ 竞彩分析', '/api/sports-lab',
     {'min_profit': 0.005, 'include_jingcai': True}),
    ('⑨ 历史记录', '/api/history', {}),
]

GET_CASES = [
    ('⑦ 竞彩实时盘口', '/api/jingcai-live', None),
]


def run(c):
    ok = c.test_client()
    return ok


def main():
    client = app.test_client()
    print()
    print('=' * 100)
    print('  Web GUI 全端点 × 双彩种 实测')
    print('=' * 100)

    # 取两个彩种各自最新一期期号
    from data.sqlite_storage import SQLiteStorage
    st = SQLiteStorage()
    latest = {g: st.get_latest_period(g) for g in ('dlt', 'ssq')}
    print(f'  最新期号: 大乐透 {latest["dlt"]}  双色球 {latest["ssq"]}')

    results = []
    for label, ep, body_tpl in CASES:
        for g in ('dlt', 'ssq'):
            # 与彩种无关的端点 (body 里没有 {g}) 只在 dlt 下跑一次
            if g == 'ssq' and '{g}' not in str(body_tpl):
                continue
            body = body_tpl
            if isinstance(body, dict):
                body = {k: (v.replace('{g}', g).replace('{period}',
                                            str(latest[g] or ''))
                            if isinstance(v, str) else v)
                        for k, v in body.items()}
            t0 = time.time()
            try:
                r = client.post(ep, json=body)
                dt = time.time() - t0
                j = r.get_json() or {}
                if r.status_code == 200 and j.get('ok', True):
                    note = ''
                    if isinstance(j, dict):
                        for k in ('message', 'note'):
                            if isinstance(j.get(k), str):
                                note = j[k][:40]
                                break
                    status = '✅ OK'
                else:
                    err = (j.get('error') if isinstance(j, dict) else '') or f'HTTP {r.status_code}'
                    status = f'❌ {str(err)[:60]}'
            except Exception as e:
                dt = time.time() - t0
                status = f'❌ {type(e).__name__}: {str(e)[:50]}'
                traceback.print_exc()
            results.append((label, g, status, dt))
            print(f'  {status:<12}{label:<16}{g:<6}{dt:>7.1f}s')

    for label, ep, _ in GET_CASES:
        t0 = time.time()
        try:
            r = client.get(ep)
            dt = time.time() - t0
            j = r.get_json() or {}
            status = ('✅ OK' if r.status_code == 200 and j.get('ok', True)
                      else f'❌ {str(j.get("error"))[:60]}')
        except Exception as e:
            dt = time.time() - t0
            status = f'❌ {type(e).__name__}'
        results.append((label, '-', status, dt))
        print(f'  {status:<12}{label:<16}{"-":<6}{dt:>7.1f}s')

    print()
    print('=' * 100)
    bad = [r for r in results if not r[2].startswith('✅')]
    if bad:
        print(f'  ❌ {len(bad)}/{len(results)} 项不可用:')
        for label, g, st, dt in bad:
            print(f'     {label} [{g}]  {st}')
    else:
        print(f'  ✅ {len(results)}/{len(results)} 全部可用')
    print('=' * 100)
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
