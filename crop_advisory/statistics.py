"""Small standard-library statistical functions for transparent experiment reports."""
import math
import random
from collections import Counter


def percentile(values,q):
    if not values:return None
    ordered=sorted(values);pos=(len(ordered)-1)*q
    lo=int(pos);hi=min(lo+1,len(ordered)-1)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(pos-lo)


def wilson(successes,total,z=1.959963984540054):
    if total<=0:return None
    if not 0<=successes<=total:raise ValueError('Invalid numerator/denominator.')
    p=successes/total;den=1+z*z/total
    center=(p+z*z/(2*total))/den
    margin=z*math.sqrt((p*(1-p)+z*z/(4*total))/total)/den
    return [max(0,center-margin),min(1,center+margin)]


def paired_bootstrap(left,right,repetitions=2000,seed=42):
    if len(left)!=len(right) or not left:raise ValueError('Nonempty paired observations with equal length are required.')
    if repetitions<1:raise ValueError('Bootstrap repetitions must be positive.')
    differences=[float(a)-float(b) for a,b in zip(left,right)]
    rng=random.Random(seed);n=len(differences)
    draws=[sum(differences[rng.randrange(n)] for _ in range(n))/n for _ in range(repetitions)]
    return {'mean_paired_difference':sum(differences)/n,'ci95':[percentile(draws,.025),percentile(draws,.975)],
        'paired_cases':n,'bootstrap_repetitions':repetitions,'seed':seed}


def cohen_kappa(left,right):
    if len(left)!=len(right) or not left:raise ValueError('Equal, nonempty paired ratings are required.')
    n=len(left);a=Counter(left);b=Counter(right)
    observed=sum(x==y for x,y in zip(left,right))/n
    expected=sum(a[k]*b[k] for k in set(a)|set(b))/(n*n)
    return None if expected==1 else (observed-expected)/(1-expected)
