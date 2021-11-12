import functools
import scipy.optimize
import numpy as np
import formula


def opti_chasse(tdc_initial, diff, n=2, params=formula.difficulte2_params, **kwargs):

    f = functools.partial(formula.difficulte_n_chasse2, initial=tdc_initial, n=n, **params)
    tdc_chasse = scipy.optimize.minimize_scalar(lambda x: abs(f(x) - diff), bracket=[50, 1e10], method="Golden", **kwargs).x

    total_dif, chasses = formula.difficulte_n_chasse2(chasse=tdc_chasse, initial=tdc_initial, n=n, **params, return_chasses=True)

    return total_dif, chasses


if __name__ == '__main__':
    print(opti_chasse(20000, 1100000))
