"""Begleitversuche zum Studienbuch von Christian Stenzel. Python 3.12, NumPy, SciPy.
Start: python labor.py --help
Für "archiv" beide CSV-Dateien aus der PDF neben dieses Skript legen.
"""
import argparse
import csv
import math
from collections import Counter
from fractions import Fraction
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq
from scipy.special import airy, ellipk


def pumpe():
    """Volumen in ml nach 1 s. Trapezregel und Reihenintervalle mit rationaler Arithmetik."""
    def rate_bounds(time):
        power = -(time**2)
        term = Fraction(1)
        partial = term
        for k in range(1, 17):
            term *= power/k
            partial += term
        return partial + term*power/17, partial

    def integral_sum(last_index):
        return sum((Fraction((-1)**k, math.factorial(k)*(2*k+1))
                    for k in range(last_index+1)), Fraction(0))

    series_lower, series_upper = 1000*integral_sum(17), 1000*integral_sum(18)
    rows = []
    for panels in (1, 2, 4, 8, 16, 32):
        low = high = Fraction(0)
        for j in range(panels+1):
            weight = Fraction(1, 2) if j in (0, panels) else Fraction(1)
            left, right = rate_bounds(Fraction(j, panels))
            low += weight*left
            high += weight*right
        low *= Fraction(1000, panels)
        high *= Fraction(1000, panels)
        bound = Fraction(1000, 6*panels**2)
        assert low-bound <= series_lower <= series_upper <= high+bound
        lower, upper = low-bound, high+bound
        rows.append((panels, float((low+high)/2), float(bound), float(lower), float(upper)))
        if panels==16:
            assert lower < 747 < upper
        if panels==32:
            assert upper < 747
    library_value = 1000*math.sqrt(math.pi)*math.erf(1)/2
    assert abs(library_value-float((series_lower+series_upper)/2)) < 1e-10
    return np.array(rows), (float(series_lower), float(series_upper))


def pruefwagen():
    """Geschwindigkeit unter einer Kraftrampe, SI-Zahlenwerte der normierten Gleichung."""
    def rhs(t, y):
        return t-y*abs(y)

    def heun(stop, n):
        y = 0.
        h = stop/n
        for j in range(n):
            t = j*h
            k1 = rhs(t, y)
            k2 = rhs(t+h, y+h*k1)
            y += h*(k1+k2)/2
        return y

    nodes = np.array([.5, 1., 2.])
    sol = solve_ivp(rhs, (0., 2.), [0.], t_eval=nodes, method="DOP853",
                    rtol=1e-11, atol=1e-13, max_step=.1)
    assert sol.success
    _, ap0, _, bp0 = airy(0.)
    ai, ap, bi, bp = airy(nodes)
    reference = (bp0*ap-ap0*bp)/(bp0*ai-ap0*bi)
    np.testing.assert_allclose(sol.y[0], reference, rtol=0, atol=2e-10)
    rows = []
    for t, model_ode, exact in zip(nodes, sol.y[0], reference):
        by_half = heun(t, round(t/.5))
        by_quarter = heun(t, round(t/.25))
        assert abs(by_quarter-exact) < abs(by_half-exact)
        rows.append((t, by_half, by_quarter, model_ode, exact, t*t/2))
    return np.array(rows)


def periode():
    """Ungedämpftes Pendel. Winkel in Grad als Eingaben, Ergebnisse in Sekunden."""
    gravity, length = 9.81, 1.
    time_scale = math.sqrt(length/gravity)
    linear_period = 2*math.pi*time_scale

    def exact(degrees):
        amplitude = math.radians(degrees)
        return 4*time_scale*ellipk(math.sin(amplitude/2)**2)

    def integrated(degrees, max_step, tol):
        def rate(t, state):
            angle, speed = state
            return speed, -(gravity/length)*math.sin(angle)
        def center(t, state):
            return state[0]
        center.terminal, center.direction = True, -1
        sol = solve_ivp(rate, (0., 3.), [math.radians(degrees), 0.],
                        method="DOP853", rtol=tol, atol=tol/100, max_step=max_step,
                        events=center)
        assert sol.success and len(sol.t_events[0]) == 1
        return 4*sol.t_events[0][0]

    rows = []
    for angle in (5., 15., 30., 60.):
        reference = exact(angle)
        coarse = integrated(angle, .2, 1e-6)
        fine = integrated(angle, .1, 1e-10)
        assert abs(fine-reference) < 1e-9 and abs(fine-reference) < abs(coarse-reference)
        rows.append((angle, reference, linear_period, 100*(1-linear_period/reference), coarse, fine))
    limit = brentq(lambda degrees: 1-linear_period/exact(degrees)-.01, 5., 60.)
    return np.array(rows), limit


def normalform():
    """Feder mit m=1, d=3, k=2, sowie eine Gleichung dritter Ordnung."""
    def feder(t, x):
        q, v = x
        return v, -3*v - 2*q
    t = np.linspace(0, 4, 201)
    sol = solve_ivp(feder, (0, 4), [1., 0.], t_eval=t, rtol=1e-10, atol=1e-12)
    exact = np.array([2*np.exp(-t)-np.exp(-2*t), -2*np.exp(-t)+2*np.exp(-2*t)])
    assert sol.success and np.max(np.abs(sol.y-exact)) < 1e-9
    def dritte(t, x):
        return x[1], x[2], -x[0]-3*x[1]-3*x[2]
    order3 = solve_ivp(dritte, (0, 1), [0., 0., 2.], t_eval=[1], rtol=1e-11, atol=1e-13)
    np.testing.assert_allclose(order3.y[:, -1], np.array([1, 1, -1])/math.e, atol=3e-11)
    return exact[:, 50], order3.y[:, -1]


def rc():
    """Rückwärts Euler als ODE und als volles Maschenresiduum, bei h=0,5 s."""
    capacitance, resistance, source, step = 1e-3, 2000., 5., .5
    matrix = np.array([[capacitance/step, -1.], [1., resistance]])
    u = reduced = 0.
    rows = []
    for k in range(1, 5):
        b = np.array([capacitance*u/step, source])
        u, current = np.linalg.solve(matrix, b)
        reduced = (reduced + step*source/(resistance*capacitance))/(1+step/(resistance*capacitance))
        assert abs(u-reduced)<5e-15
        residual = matrix @ np.array([u, current])-b
        assert max(abs(residual))<1e-13
        exact = source*(-math.expm1(-k*step/(resistance*capacitance)))
        rows.append((k*step, u, current*1000, exact))
    return rows


def c05():
    """Phasenreferenz und zwei unabhängige adaptive Integrationen."""
    a, b, stop = 2.7e6, 3.5651205, 3.5
    modes = [(.4, 5.5, 5.8, 1), (-.3, 2.73, 2.5, -1)]
    def calculate(method):
        time, state, hits = 0., np.array([4.2, .3]), []
        nfev = nlu = 0
        while time < stop:
            c2, c4, limit, direction = modes[len(hits)%2]
            if method == "Phase":
                d = state[1]-c4
                weight = a*d/(a-b)
                def phase(dt, c4=c4, c2=c2, weight=weight, state=state, d=d):
                    return np.array([c4+c2+weight*math.exp(-b*dt)
                                     +(state[0]-c4-c2-weight)*math.exp(-a*dt),
                                     c4+d*math.exp(-b*dt)])
                upper = stop-time
                if direction*(phase(upper)[0]-limit) < 0:
                    return hits, phase(upper), nfev, nlu
                dt = brentq(lambda s, limit=limit: phase(s)[0]-limit, 0, upper, xtol=1e-14)
                state = phase(dt)
                time += dt
            else:
                def rhs(t, y, c2=c2, c4=c4):
                    return a*(y[1]+c2-y[0]), b*(c4-y[1])
                def guard(t, y, limit=limit):
                    return y[0]-limit
                guard.terminal, guard.direction = True, direction
                result = solve_ivp(rhs, (time, stop), state, method=method,
                                   jac=[[-a,a],[0.,-b]], events=guard,
                                   rtol=1e-8, atol=1e-10, max_step=.2)
                assert result.success
                nfev += result.nfev
                nlu += result.nlu
                time, state = result.t[-1], result.y[:, -1]
                if len(result.t_events[0])==0:
                    return hits, state, nfev, nlu
            assert not hits or time > hits[-1]
            hits.append(time)
            assert len(hits)<=4
        return hits, state, nfev, nlu
    base, endpoint, _, _ = calculate("Phase")
    assert len(base)==3
    rows=[]
    for method in ("Radau", "BDF"):
        hits, y, calls, decompositions = calculate(method)
        assert len(hits)==len(base)
        et, ey = np.max(np.abs(np.array(hits)-base)), np.max(np.abs(y-endpoint))
        assert et<1e-5 and ey<1e-5
        rows.append((method, calls, decompositions, et, ey))
    return base, endpoint, rows


def c07(method="DOP853", tolerance=1e-11, linearisiert=False):
    """C07 A(i), Konfiguration wie in Tabelle 3 der SNE-Studie."""
    m, damping, g = 1.02, .2, 9.81
    pin, short = -math.pi/12, .3
    state, time, length = [math.pi/6, 0.], 0., 1.
    hits, pieces = [], []
    while time < 10.:
        def rhs(t, y, length=length):
            restoring = y[0] if linearisiert else np.sin(y[0])
            return y[1], -(g/length)*restoring-damping/m*y[1]
        def guard(t, y):
            return y[0]-pin
        guard.terminal, guard.direction = True, (-1 if length==1 else 1)
        result = solve_ivp(rhs, (time, 10.), state, method=method, events=guard,
                           dense_output=True, max_step=.05, rtol=tolerance, atol=tolerance/100)
        assert result.success
        pieces.append((length, result))
        if not len(result.t_events[0]):
            break
        hit = result.t_events[0][0]
        before = result.y_events[0][0,1]
        new_length = short if length==1 else 1.
        after = length*before/new_length
        assert math.isclose(length*before,new_length*after,rel_tol=1e-14)
        assert not hits or hit>hits[-1][0]
        hits.append((hit, before, after))
        assert len(hits)<=12
        state, time, length = [pin, after], hit, new_length
    assert len(hits)==8
    return np.array(hits), pieces


def c07_linearvergleich():
    """Lineare Phasenlösung in geschlossener Form, gerichtet eingeklammerte Kontakte."""
    gravity, pin, end_time = 9.81, -math.pi/12, 10.
    alpha = .2/(2*1.02)
    time, length, angle, speed = 0., 1., math.pi/6, 0.
    analytic_hits = []
    while time < end_time:
        beta = math.sqrt(gravity/length-alpha**2)
        cosine = angle
        sine = (speed+alpha*angle)/beta
        speed_sine = -alpha*sine-beta*cosine

        def state(dt, beta=beta, cosine=cosine, sine=sine, speed=speed, speed_sine=speed_sine):
            c, s, decay = math.cos(beta*dt), math.sin(beta*dt), math.exp(-alpha*dt)
            return decay*(cosine*c+sine*s), decay*(speed*c+speed_sine*s)

        remaining = end_time-time
        first_extremum = (math.atan2(speed, -speed_sine) % math.pi)/beta
        step = math.pi/beta
        extrema = np.arange(first_extremum, remaining, step)
        boundaries = [0., *(t for t in extrema if t>0.), remaining]
        direction = -1 if length==1. else 1
        for left, right in pairwise(boundaries):
            if direction*(state(left)[0]-pin)<0<direction*(state(right)[0]-pin):
                dt = brentq(lambda t: state(t)[0]-pin, left, right, xtol=5e-15)
                break
        else:
            break
        next_length = .3 if length==1. else 1.
        _, arrival_speed = state(dt)
        speed = arrival_speed*length/next_length
        angle, length, time = pin, next_length, time+dt
        analytic_hits.append(time)
        assert len(analytic_hits)<=12
    nonlinear, _ = c07()
    linear_ode, _ = c07(linearisiert=True)
    analytic_hits = np.array(analytic_hits)
    np.testing.assert_allclose(linear_ode[:, 0], analytic_hits, rtol=0, atol=1e-8)
    # Grujic et al., SNE 31(4), Tabelle 3, Spalte J (Sekunden).
    published_linear = [.692023, 1.120545, 2.540860, 2.931800, 4.465756, 4.790785, 6.532060, 6.652993]
    np.testing.assert_allclose(analytic_hits, published_linear, rtol=0, atol=3e-6)
    return np.column_stack([nonlinear[:,0], analytic_hits, 1000*(nonlinear[:,0]-analytic_hits)]), max(abs(linear_ode[:,0]-analytic_hits))


def c07_protokoll():
    primary, _ = c07()
    second, _ = c07("RK45", 1e-8)
    # Grujic et al., SNE 31(4), Tabelle 3, Spalte F, Sekunden.
    published = np.array([.703427, 1.151778, 2.590338, 2.990403,
                          4.542705, 4.867492, 6.648731, 6.720995])
    delta = primary[:, 0]-published
    assert max(abs(delta))<.001
    method_error = max(abs(primary[:, 0]-second[:, 0]))
    assert method_error<1e-6
    return primary, delta*1000, method_error


def c12():
    """Vier gleich schwere Kugeln, freie Abstände 1 m. x sind abstandsbereinigte Orte."""
    x = np.arange(4, dtype=float)
    speed = np.array([1., 0., 0., 0.])
    time, history = 0., []
    while time < 3.5:
        gaps, closing = np.diff(x), -np.diff(speed)
        dt = np.full(3, np.inf)
        np.divide(gaps,closing,out=dt,where=closing>0)
        pair = int(np.argmin(dt))
        if not np.isfinite(dt[pair]) or time+dt[pair]>3.5:
            x += (3.5-time)*speed
            break
        time += dt[pair]
        x += dt[pair]*speed
        speed[pair], speed[pair+1] = speed[pair+1], speed[pair]
        history.append((time, pair+1, pair+2))
        assert np.isclose(speed.sum(), 1.) and np.isclose(speed@speed/2, .5)
    np.testing.assert_allclose([s[0] for s in history],[1,2,3])
    return history, x, speed


def c19r():
    """Kontinuierliche Punktquelle in unendlicher Ebene, direkt über das Quellalter integriert."""
    t, x, y = 10*86400., 5., 0.
    speed, alpha, thickness, porosity, rate = 1e-5, .05, 10., .25, 2.
    disp = alpha*speed
    def per_fraction(u):
        if u==0:
            return 0.
        age = t*u
        exponential = -((x-speed*age)**2 + y*y)/(4*disp*age)
        return rate*t*math.exp(exponential)/(4*math.pi*disp*age*thickness*porosity)
    estimates=[]
    for tolerance in (1e-8,1e-12):
        value, err = quad(per_fraction,0.,1.,epsabs=1e-8,epsrel=tolerance,points=[x/(speed*t)])
        estimates.append((value,err))
    assert abs(estimates[-1][0]-45021.62)<.01
    return estimates


def c21():
    g, height, restitution = 9.81, 10., .9
    t1 = math.sqrt(2*height/g)
    times = [t1, t1*(1+2*restitution)]
    # Fehler des zweiten Aufprallzeitpunkts bei e -> e + 0,01.
    t2_changed = t1*(1+2*(restitution+.01))
    sensitivity = (t2_changed-times[1])/.01
    assert abs(sensitivity-2*t1)<1e-12
    return times, sensitivity, .026*math.log(.026/(20*1e-8))


def c09():
    """Erster Reglertakt von C09. Der vollständige 16-Takte-Versuch steht in den CSV-Daten."""
    pump = (.10+.14+.175)/3
    start = np.array([.503, .30])
    def rates(t, h):
        difference = h[0]-h[1]
        coupling = .06624*.4*math.copysign(math.sqrt(abs(difference)),difference)
        outlet = .0605*.3*math.sqrt(max(0.,h[1]))*(1.2 if h[1]<.16 else 1.)
        return .067*pump-coupling, coupling-outlet
    result=solve_ivp(rates,(0.,1.),start,method="DOP853",rtol=1e-12,atol=1e-14)
    assert result.success
    slopes=rates(0.,start)
    assert abs(sum(slopes)-(.067*pump-.0605*.3*math.sqrt(start[1])))<1e-14
    return pump, slopes, result.y[:,-1]


def c09_vergleich():
    """Ein Euler-Schritt in Meter, Gegenrechnung und Fehler in Millimetern am ersten Reglertakt."""
    _, slopes, reference = c09()
    predicted = np.array([.503, .30])+np.asarray(slopes)
    difference_mm = (predicted-reference)*1000
    assert np.all(np.abs(difference_mm) < .5) and np.all(np.abs(difference_mm) > .05)
    return np.column_stack([predicted, reference, difference_mm])


def c13():
    """Lineares C13-Studienfenster mit Lastpuls, fünf Größen an drei Terminen."""
    from scipy.linalg import expm
    m_cart, m_load, length = 10., 100., 5.
    dc, dl, gravity, setpoint = .5, .001, 9.81, 160.
    state = np.zeros(5)
    other = state.copy()
    rows=[]
    for left, right, load in ((0.,4.,0.),(4.,7.,-800.),(7.,15.,0.)):
        augmented = np.array([
            [0,1,0,0,0,0],[0,-.05,98.1,0,.1,0],
            [0,0,0,1,0,0],[0,(.05-.00001)/5,-9.81*11/5,-.00001,-.02,load/500],
            [0,0,0,0,-4,640],[0,0,0,0,0,0]])
        state = (expm((right-left)*augmented)@np.r_[state,1.])[:5]
        def rhs(t, y, load=load):
            _, v, phi, omega, drive = y
            accel=(drive-dc*v+gravity*m_load*phi)/m_cart
            angular=(-gravity*(1+m_load/m_cart)*phi+(dc/m_cart-dl/m_load)*v
                     -length*dl/m_load*omega-drive/m_cart+load/m_load)/length
            return v,accel,omega,angular,4*(setpoint-drive)
        sol=solve_ivp(rhs,(left,right),other,method="DOP853",rtol=1e-11,atol=1e-13)
        assert sol.success
        other=sol.y[:,-1]
        np.testing.assert_allclose(other,state,rtol=1e-9,atol=1e-9)
        rows.append((right,*state))
    return np.array(rows)


def archiv():
    result={}
    for name, n in (("qss-extension.csv",456),("rk23-devs.csv",138)):
        path = Path(__file__).with_name(name)
        with path.open(encoding="utf-8",newline="") as fp:
            rows = list(csv.DictReader(fp))
        assert len(rows)==n
        result[name] = dict(Counter(row["status"] for row in rows))
    return result


if __name__ == "__main__":
    routines = {"pumpe":pumpe, "wagen":pruefwagen, "periode":periode, "normalform":normalform, "rc":rc, "c05":c05,
                "c07":c07_protokoll, "c07linear":c07_linearvergleich, "c09":c09, "c09vergleich":c09_vergleich,
                "c12":c12, "c13":c13, "c19r":c19r, "c21":c21}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("versuch",choices=["alle", *routines, "archiv"],nargs="?",default="alle")
    selection=parser.parse_args().versuch
    for name, run in routines.items():
        if selection in ("alle",name):
            print(name,run())
    if selection=="archiv":
        print(archiv())
