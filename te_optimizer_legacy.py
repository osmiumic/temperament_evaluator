# © 2020-2022 Flora Canou | Version 0.21.3
# This work is licensed under the GNU General Public License version 3.

import warnings
import numpy as np
from scipy import optimize, linalg
np.set_printoptions (suppress = True, linewidth = 256, precision = 4)

PRIME_LIST = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]
SCALAR = 1200 #could be in octave, but for precision reason

def get_subgroup (main, subgroup):
    if subgroup is None:
        subgroup = PRIME_LIST[:main.shape[1]]
    elif main.shape[1] != len (subgroup):
        warnings.warn ("dimension does not match. Casting to the smaller dimension. ")
        dim = min (main.shape[1], len (subgroup))
        main = main[:, :dim]
        subgroup = subgroup[:dim]
    return main, subgroup

def get_weight (subgroup, wtype = "tenney"):
    if wtype == "tenney":
        return np.diag (1/np.log2 (subgroup))
    elif wtype == "frobenius":
        return np.eye (len (subgroup))
    elif wtype == "benedetti":
        return np.diag (1/np.array (subgroup))
    else:
        warnings.warn ("weighter type not supported, using default (\"tenney\")")
        return get_weight (subgroup, wtype = "tenney")

def get_skew (subgroup, skew = 0, order = 2):
    if skew == 0:
        return np.eye (len (subgroup))
    elif order == 2:
        r = skew/(len (subgroup)*skew**2 + 1)
        return np.append (np.eye (len (subgroup)) - skew*r*np.ones ((len (subgroup), len (subgroup))),
            r*np.ones ((len (subgroup), 1)), axis = 1)
    else:
        raise NotImplementedError ("Weil skew only works with Euclidean norm as of now.")

def weightskewed (main, subgroup, wtype = "tenney", skew = 0, order = 2):
    return main @ get_weight (subgroup, wtype) @ get_skew (subgroup, skew, order)

def error (gen, map, jip, order):
    return linalg.norm (gen @ map - jip, ord = order)

def optimizer_main (map, subgroup = None, wtype = "tenney", skew = 0, order = 2,
        cons_monzo_list = None, des_monzo = None, show = True):
    map, subgroup = get_subgroup (np.array (map), subgroup)

    jip = np.log2 (subgroup)*SCALAR
    map_wx = weightskewed (map, subgroup, wtype, skew, order)
    jip_wx = weightskewed (jip, subgroup, wtype, skew, order)
    if order == 2 and cons_monzo_list is None: #te with no constraints, simply use lstsq for better performance
        res = linalg.lstsq (map_w.T, jip_wx)
        gen = res[0]
        print ("L2 tuning without constraints, solved using lstsq. ")
    else:
        gen0 = [SCALAR]*map.shape[0] #initial guess
        cons = () if cons_monzo_list is None else {'type': 'eq', 'fun': lambda gen: (gen @ map - jip) @ cons_monzo_list}
        res = optimize.minimize (error, gen0, args = (map_wx, jip_wx, order), method = "SLSQP",
            options = {'ftol': 1e-9}, constraints = cons)
        print (res.message)
        if res.success:
            gen = res.x
        else:
            raise ValueError ("infeasible optimization problem. ")

    if not des_monzo is None:
        if np.array (des_monzo).ndim > 1 and np.array (des_monzo).shape[1] != 1:
            raise IndexError ("only one destretch target is allowed. ")
        elif (tempered_size := gen @ map @ des_monzo) == 0:
            raise ZeroDivisionError ("destretch target is in the nullspace. ")
        else:
            gen *= (jip @ des_monzo)/tempered_size

    tuning_map = gen @ map
    mistuning_map = tuning_map - jip

    if show:
        print (f"Generators: {gen} (¢)",
            f"Tuning map: {tuning_map} (¢)",
            f"Mistuning map: {mistuning_map} (¢)", sep = "\n")

    return gen, tuning_map, mistuning_map

optimiser_main = optimizer_main
