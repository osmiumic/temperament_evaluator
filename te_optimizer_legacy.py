# © 2020-2023 Flora Canou | Version 0.26.0
# This work is licensed under the GNU General Public License version 3.

import warnings
import numpy as np
from scipy import optimize, linalg
np.set_printoptions (suppress = True, linewidth = 256, precision = 4)

PRIME_LIST = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89]
SCALAR = 1200 #could be in octave, but for precision reason

# norm profile for the tuning space
class Norm: 
    def __init__ (self, wtype = "tenney", wamount = 1, skew = 0, order = 2):
        self.wtype = wtype
        self.wamount = wamount
        self.skew = skew
        self.order = order

    def __get_weight (self, subgroup):
        if self.wtype == "tenney":
            weight_vec = np.reciprocal (np.log2 (np.array (subgroup, dtype = float)))
        elif self.wtype == "wilson" or self.wtype == "benedetti":
            weight_vec = np.reciprocal (np.array (subgroup, dtype = float))
        elif self.wtype == "equilateral":
            weight_vec = np.ones (len (subgroup))
        else:
            warnings.warn ("weighter type not supported, using default (\"tenney\")")
            self.wtype = "tenney"
            return self.__get_weight (subgroup)
        return np.diag (weight_vec**self.wamount)

    def __get_skew (self, subgroup):
        if self.skew == 0:
            return np.eye (len (subgroup))
        elif self.order == 2:
            if self.skew != np.inf:
                r = self.skew/(len (subgroup)*self.skew**2 + 1)
                kr = self.skew*r
            else:
                r = 0
                kr = 1/len (subgroup)
        else:
            raise NotImplementedError ("Weil skew only works with Euclidean norm as of now.")
        return np.append (
            np.eye (len (subgroup)) - kr*np.ones ((len (subgroup), len (subgroup))),
            r*np.ones ((len (subgroup), 1)), axis = 1)

    def weightskewed (main, subgroup):
        return main @ self.__get_weight (subgroup) @ self.__get_skew (subgroup)

def __get_subgroup (main, subgroup):
    main = np.asarray (main)
    if subgroup is None:
        subgroup = PRIME_LIST[:main.shape[1]]
    elif main.shape[1] != len (subgroup):
        warnings.warn ("dimension does not match. Casting to the smaller dimension. ")
        dim = min (main.shape[1], len (subgroup))
        main = main[:, :dim]
        subgroup = subgroup[:dim]
    return main, subgroup

def __error (gen, vals, jip, order):
    return linalg.norm (gen @ vals - jip, ord = order)

def optimizer_main (vals, subgroup = None, norm = Norm (), #"map" is a reserved word
        cons_monzo_list = None, des_monzo = None, show = True):
    vals, subgroup = __get_subgroup (vals, subgroup)

    jip = np.log2 (subgroup)*SCALAR
    vals_wx = weightskewed (vals, subgroup, norm)
    jip_wx = weightskewed (jip, subgroup, norm)
    if norm.order == 2 and cons_monzo_list is None: #simply using lstsq for better performance
        res = linalg.lstsq (vals_wx.T, jip_wx)
        gen = res[0]
        print ("Euclidean tuning without constraints, solved using lstsq. ")
    else:
        gen0 = [SCALAR]*vals.shape[0] #initial guess
        cons = () if cons_monzo_list is None else {'type': 'eq', 'fun': lambda gen: (gen @ vals - jip) @ cons_monzo_list}
        res = optimize.minimize (__error, gen0, args = (vals_wx, jip_wx, norm.order), method = "SLSQP",
            options = {'ftol': 1e-9}, constraints = cons)
        print (res.message)
        if res.success:
            gen = res.x
        else:
            raise ValueError ("infeasible optimization problem. ")

    if not des_monzo is None:
        if np.asarray (des_monzo).ndim > 1 and np.asarray (des_monzo).shape[1] != 1:
            raise IndexError ("only one destretch target is allowed. ")
        elif (tempered_size := gen @ vals @ des_monzo) == 0:
            raise ZeroDivisionError ("destretch target is in the nullspace. ")
        else:
            gen *= (jip @ des_monzo)/tempered_size

    tuning_map = gen @ vals
    mistuning_map = tuning_map - jip

    if show:
        print (f"Generators: {gen} (¢)",
            f"Tuning map: {tuning_map} (¢)",
            f"Mistuning map: {mistuning_map} (¢)", sep = "\n")

    return gen, tuning_map, mistuning_map

optimiser_main = optimizer_main
