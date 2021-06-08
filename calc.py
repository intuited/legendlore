"""Probability functionality.

(test functions)
>>> round4 = lambda value: round(value, ndigits=4)
>>> range23 = lambda fn: {target: round4(fn(target)) for target in range(23)}

Odds for rolling saving throws and ability checks with no auto-pass or auto-fail on 20 or 1:
>>> range23(meetorbeat)
{0: 1.0, 1: 1.0, 2: 0.95, 3: 0.9, 4: 0.85, 5: 0.8, 6: 0.75, 7: 0.7, 8: 0.65, 9: 0.6, 10: 0.55, 11: 0.5, 12: 0.45, 13: 0.4, 14: 0.35, 15: 0.3, 16: 0.25, 17: 0.2, 18: 0.15, 19: 0.1, 20: 0.05, 21: 0.0, 22: 0.0}

Same with advantage:
>>> range23(meetorbeat.adv)
{0: 1.0, 1: 1.0, 2: 0.9975, 3: 0.99, 4: 0.9775, 5: 0.96, 6: 0.9375, 7: 0.91, 8: 0.8775, 9: 0.84, 10: 0.7975, 11: 0.75, 12: 0.6975, 13: 0.64, 14: 0.5775, 15: 0.51, 16: 0.4375, 17: 0.36, 18: 0.2775, 19: 0.19, 20: 0.0975, 21: 0.0, 22: 0.0}

Odds for normal attacks where a 1 always misses and a 20 always hits:
>>> range23(attackodds)
{0: 0.95, 1: 0.95, 2: 0.95, 3: 0.9, 4: 0.85, 5: 0.8, 6: 0.75, 7: 0.7, 8: 0.65, 9: 0.6, 10: 0.55, 11: 0.5, 12: 0.45, 13: 0.4, 14: 0.35, 15: 0.3, 16: 0.25, 17: 0.2, 18: 0.15, 19: 0.1, 20: 0.05, 21: 0.05, 22: 0.05}

Same with advantage:
>>> range23(attackodds.adv)
{0: 0.9975, 1: 0.9975, 2: 0.9975, 3: 0.99, 4: 0.9775, 5: 0.96, 6: 0.9375, 7: 0.91, 8: 0.8775, 9: 0.84, 10: 0.7975, 11: 0.75, 12: 0.6975, 13: 0.64, 14: 0.5775, 15: 0.51, 16: 0.4375, 17: 0.36, 18: 0.2775, 19: 0.19, 20: 0.0975, 21: 0.0975, 22: 0.0975}
"""
# average die roll calculations
def avg(expression):
    """Calculates the average total of `expression`.

    `expression` can contain die-roll notation of the form [0-9]+d[0-9]+.

    >>> avg('1')
    1
    >>> avg('1 - 2')
    -1

    Average roll on a four-sided die is 2.5
    >>> avg('1d4')
    2.5

    So anyway, I started blasting
    >>> avg('1d10+5')
    10.5

    I put a spell on you... (specifically a Hex)
    >>> avg('1d10+5 + 1d6')
    14.0

    Level 5 warlock damage for Eldritch Blast + Hex with 20 Charisma (if both attacks hit)
    >>> avg('2d10+10 + 2d6')
    28.0
    """
    from simpleeval import simple_eval
    import re
    d_re = r'\b([0-9]+)d([0-9]+)\b'
    subbed = re.sub(d_re, r'(float(\1)*\2 + \1)/2', expression)
    return simple_eval(subbed)

def dpr(ac, attack_bonus, damage):
    """Calculates average DPR for the given AC, attack bonus, and damage roll.

    If our spell attack bonus is +8 and their AC is 17, what's our average damage with Eldritch Blast at L5?
    >>> dpr(17, 8, '2d10+10 + 2d6')
    16.8
    """
    return attackodds(ac - attack_bonus) * avg(damage)

# die roll odds
adv = lambda odds: 1.0 - ((1.0 - odds) * (1.0 - odds))
meetorbeat = lambda target: max(min(1.0 - (target - 1.0) / 20, 1.0), 0.0)
meetorbeat.adv = lambda target: adv(meetorbeat(target))
attackodds = lambda target: max(min(1.0 - (target - 1.0) / 20, 0.95), 0.05)
attackodds.adv = lambda target: adv(attackodds(target))

# rounding; passes None values through
round4 = lambda x: round(x, 4) if x is not None else None
