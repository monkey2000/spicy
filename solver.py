import numpy as np
from dataclasses import dataclass
import re
import sys
import time
import matplotlib
from matplotlib import pyplot as plt
matplotlib.use('Qt5Agg')


@dataclass
class Component:
    type: str
    nid: int
    u: int
    v: int
    val: float
    factor: float
    ref_u: int
    ref_v: int
    ref_comp: str

    def __eq__(self, other):
        return (self.type + str(self.nid)) == (other.type + str(other.nid))


class ComponentRegistry:
    def __init__(self):
        self.comps = []
        self.name_to_comps = {}

    def clear(self):
        self.comps = []
        self.name_to_comps = {}

    def getN(self):
        n = 0
        for comp in self.comps:
            n = max(n, comp.u)
            n = max(n, comp.v)
        return n + 1

    def getM(self):
        return len(self.comps)

    def has_component(self, name):
        return name in self.name_to_comps.keys()

    def get_component(self, name):
        return self.name_to_comps[name]

    def add_component(self, comp: Component):
        name = comp.type + str(comp.nid)
        if self.has_component(name):
            return False

        self.comps.append(comp)
        self.name_to_comps[name] = comp
        return True

    def del_component(self, comp: Component):
        name = comp.type + comp.nid
        if not self.has_component(name):
            return False

        self.comps.remove(comp)
        del self.name_to_comps[name]
        return True

    def forward(self, u: int):
        for comp in self.comps:
            if comp.u == u:
                yield comp

    def backward(self, v: int):
        for comp in self.comps:
            if comp.v == v:
                yield comp


class Solver:
    def __init__(self, registry):
        self.reg = reg


reg = ComponentRegistry()


def file_input(name):
    reg.clear()
    with open(name, 'r') as f:
        n, m = [int(x) for x in f.readline().strip().split()]
        # print(n)
        # print(m)
        for line in f.readlines():
            line = line.strip().split()
            match = re.match(r'([A-Z]+)([0-9]+)', line[0])
            _type = match.group(1)
            nid = int(match.group(2))
            u = int(line[1])
            v = int(line[2])
            val = float(line[3])
            if _type in ['VS', 'CS', 'R']:
                reg.add_component(Component(_type, nid, u, v, val, 0.0, 0, 0, ''))
            elif _type in ['VCVS', 'VCCS']:
                ref_u = int(line[4])
                ref_v = int(line[5])
                reg.add_component(Component(_type, nid, u, v, val, 0.0, ref_u, ref_v, ''))
            elif _type in ['CCVS', 'CCCS']:
                ref_comp = line[4]
                if not reg.has_component(ref_comp):
                    print('Cannot recognize reference component \'%s\'' % ref_comp, file=sys.stderr)
            elif _type in ['C', 'L']:
                factor = float(line[4])
                print(factor)
                reg.add_component(Component(_type, nid, u, v, val, factor, 0, 0, ''))
            else:
                print('Unrecognized type \'%s\'' % _type, file=sys.stderr)


def solve():
    n = reg.getN()
    m = reg.getM()
    power_number = 0

    for comp in reg.comps:
        if comp.type != 'R':
            power_number += 1
            if comp.type in ['CCVS', 'CCCS'] and reg.get_component(comp.ref_comp).type == 'R':
                power_number += 1

    equ_number = n + power_number
    used_power_number = 0
    power_id = {}
    current_note = {}
    dynamic_place = {}

    A = np.zeros((equ_number, equ_number), dtype=np.float64)
    b = np.zeros(equ_number, dtype=np.float64)

    for i in range(n):
        for comp in reg.forward(i):
            if comp.type == 'R':
                A[i][comp.u] += 1 / comp.val
                A[i][comp.v] += -1 / comp.val
            elif comp.type in ['VS', 'C']:
                p = n + used_power_number
                A[i][p] += -1
                if comp.type == 'C':
                    current_note[comp.type + str(comp.nid)] = p
                    dynamic_place[comp.type + str(comp.nid)] = p
                A[comp.v][p] += 1
                A[p][comp.u] += 1
                A[p][comp.v] += -1
                b[p] += comp.val
                power_id[comp.type + str(comp.nid)] = p
                used_power_number += 1
            elif comp.type in ['CS', 'L']:
                p = n + used_power_number
                A[i][p] += -1
                A[comp.v][p] += 1
                A[p][p] += 1
                b[p] += comp.val
                if comp.type == 'L':
                    dynamic_place[comp.type + str(comp.nid)] = p
                power_id[comp.type + str(comp.nid)] = p
                used_power_number += 1
            # elif comp.type == 'VCCS':
            #     p = n + used_power_number
            #     A[i][p] += -1
            #     A[comp.v][p] += 1
            #     A[p][comp.ref_u] += -comp.val
            #     A[p][comp.ref_v] += comp.val
            #     A[p][p] += 1
            #     power_id[comp.type + comp.nid] = p
            #     used_power_number += 1
            # elif comp.type == 'CCVS':
            #     p = n + used_power_number
            #     ref_comp = reg.get_component(comp.ref_comp)
            #     if ref_comp.type == 'R':
            #         A[p][ref_comp.u] += -1/comp.val
            #         A[p][ref_comp.v] += 1/comp.val
            #         A[p][p] += 1
            #         p += 1
            #         A[p][p - 1] += -comp.val
            #         A[p][comp.u] += 1
            #         A[p][comp.v] += -1
            #     else:
        for comp in reg.backward(i):
            if comp.type == 'R':
                A[i][comp.u] += -1 / comp.val
                A[i][comp.v] += 1 / comp.val

    A[0][0] = 1
    print('A:')
    print(A)
    print('b:')
    print(b)

    inv_A = np.linalg.inv(A)

    t = 0
    delta_t = 1e-5
    tt = []
    seq = []
    # hl, = plt.plot([], [])
    tick = 0
    plt.plot([], [])
    plt.pause(0.001)
    tic = time.time()
    while t < 1:
        x = inv_A.dot(b)
        tt.append(t)
        seq.append(x[2])
        print(t, x[2])
        if tick % 300 == 0:
            plt.clf()
            plt.plot(tt, seq)
            plt.pause(0.001)
        # hl.set_xdata(tt)
        # hl.set_ydata(seq)
        # plt.draw()
        # plt.pause(0.01)
        for comp in reg.comps:
            name = comp.type + str(comp.nid)
            if comp.type == 'C':
                comp.val += -x[current_note[name]] / comp.factor * delta_t
                b[dynamic_place[name]] = comp.val
            elif comp.type == 'L':
                comp.val += (x[comp.v] - x[comp.u]) / comp.factor * delta_t
                b[dynamic_place[name]] = comp.val
        t += delta_t
        tick += 1
    toc = time.time()
    print('%d iterations in %.2f sec, %d iter/s' % (tick, toc - tic, tick / (toc - tic)))
    plt.show()


def main():
    file_input('input.txt')

    for comp in reg.comps:
        print(comp)

    solve()


if __name__ == '__main__':
    main()
