"""Offline segment geometry, never a collision event or referee verdict."""
import math


def segment_box_distance(start, end, half):
    if any(len(v)!=3 for v in (start,end,half)) or not all(math.isfinite(v) for v in (*start,*end,*half)) or min(half)<=0:
        raise ValueError('Finite triples and positive half extents required')
    delta=[end[i]-start[i] for i in range(3)]
    def point(t):
        return [start[i]+t*delta[i] for i in range(3)]
    def squared(t):
        return sum(max(0.,abs(v)-h)**2 for v,h in zip(point(t),half))
    # Convex piecewise quadratic distance; partition at all face crossings.
    breaks={0.,1.}
    for i in range(3):
        if delta[i]:
            for face in (-half[i],half[i]):
                t=(face-start[i])/delta[i]
                if 0<t<1: breaks.add(t)
    cuts=sorted(breaks)
    candidates=list(cuts)
    for low,high in zip(cuts,cuts[1:]):
        mid=(low+high)/2
        aa=bb=0.
        for i,v in enumerate(point(mid)):
            if abs(v)>half[i]:
                offset=start[i]-math.copysign(half[i],v)
                aa+=delta[i]**2
                bb+=delta[i]*offset
        if aa:
            candidates.append(max(low,min(high,-bb/aa)))
    best=min(candidates,key=squared)
    return math.sqrt(squared(best)),point(best)
