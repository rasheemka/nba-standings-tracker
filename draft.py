#!/usr/bin/env python3
"""
Record the current season's snake draft in season_config.json.

    python3 draft.py order JJ Andy Nate Chris Adam Duke Nick   # set round-1 order
    python3 draft.py order --random                           # shuffle last season's players
    python3 draft.py pick thunder                             # next pick (any unique part of a team name)
    python3 draft.py undo                                     # remove the last pick
    python3 draft.py                                          # show the board + who's on the clock

Every change rewrites the season's `team_assignments` from the picks (undrafted
teams go to "Undrafted"), so the rest of the site needs nothing else. Commit and
push season_config.json to publish the board.
"""

import argparse
import json
import random
import sys

from nba_tracker import ALL_TEAMS, SEASON_CONFIG_FILE

ROUNDS = 4
ALIASES = {'sixers': 'Philadelphia 76ers', 'okc': 'Oklahoma City Thunder', 'cavs': 'Cleveland Cavaliers',
           'mavs': 'Dallas Mavericks', 'wolves': 'Minnesota Timberwolves', 'blazers': 'Portland Trail Blazers',
           'dubs': 'Golden State Warriors', 'nola': 'New Orleans Pelicans', 'clips': 'LA Clippers'}


def snake_owner(order, pick_index):
    """Drafter making pick `pick_index` (0-based) in a snake draft."""
    rnd, pos = divmod(pick_index, len(order))
    return order[pos] if rnd % 2 == 0 else order[-1 - pos]


def assignments_from_draft(draft):
    order, picks = draft['order'], draft['picks']
    out = {name: [] for name in order}
    for i, team in enumerate(picks):
        out[snake_owner(order, i)].append(team)
    out['Undrafted'] = [t for t in ALL_TEAMS if t not in picks]
    return out


def match_team(query, taken):
    q = query.lower().strip()
    hits = [ALIASES[q]] if q in ALIASES else [t for t in ALL_TEAMS if q in t.lower()]
    exact = [t for t in hits if t.lower().split()[-1] == q or t.lower() == q]
    hits = exact or hits
    if len(hits) != 1:
        sys.exit(f"'{query}' matches {hits or 'no teams'} — be more specific.")
    if hits[0] in taken:
        sys.exit(f"{hits[0]} was already picked.")
    return hits[0]


def show(draft):
    order, picks = draft['order'], draft['picks']
    total = len(order) * draft.get('rounds', ROUNDS)
    for i, team in enumerate(picks):
        rnd = i // len(order) + 1
        print(f"  R{rnd} #{i + 1:>2}  {snake_owner(order, i):<10} {team}")
    if len(picks) < total:
        print(f"\n⏱  On the clock: {snake_owner(order, len(picks))} (pick {len(picks) + 1} of {total})")
    else:
        print(f"\n✅ Draft complete ({total} picks).")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd')
    o = sub.add_parser('order', help='set the round-1 draft order (resets picks)')
    o.add_argument('names', nargs='*')
    o.add_argument('--random', action='store_true', help="shuffle the given names (default: last season's players)")
    pk = sub.add_parser('pick', help='record the next pick')
    pk.add_argument('team', nargs='+')
    sub.add_parser('undo', help='remove the last pick')
    args = p.parse_args()

    with open(SEASON_CONFIG_FILE) as f:
        cfg = json.load(f)
    season = cfg['seasons'][cfg['current_season']]
    draft = season.get('draft')

    if args.cmd == 'order':
        names = args.names or [n for n in season['team_assignments'] if n != 'Undrafted']
        if args.random:
            random.shuffle(names)
        elif not args.names:
            sys.exit("Give the names in order, or use --random.")
        if draft and draft['picks']:
            print(f"⚠️  Discarding {len(draft['picks'])} existing picks.")
        draft = season['draft'] = {'rounds': ROUNDS, 'order': names, 'picks': []}
        print("Draft order: " + ", ".join(f"{i + 1}. {n}" for i, n in enumerate(names)))
    elif not draft:
        sys.exit("No draft order yet — run `draft.py order ...` first.")
    elif args.cmd == 'pick':
        if len(draft['picks']) >= len(draft['order']) * draft['rounds']:
            sys.exit("Draft is already complete.")
        team = match_team(' '.join(args.team), draft['picks'])
        who = snake_owner(draft['order'], len(draft['picks']))
        draft['picks'].append(team)
        print(f"#{len(draft['picks'])}: {who} takes {team}")
    elif args.cmd == 'undo':
        if not draft['picks']:
            sys.exit("No picks to undo.")
        print(f"Removed #{len(draft['picks'])}: {draft['picks'].pop()}")

    if args.cmd:
        season['team_assignments'] = assignments_from_draft(draft)
        with open(SEASON_CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
            f.write('\n')
    show(draft)


if __name__ == '__main__':
    main()
