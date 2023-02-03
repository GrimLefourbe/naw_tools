import numpy as np
import scipy.optimize
import math


def duree_attaque(
    x1,
    y1,
    x2,
    y2,
    va=0,
):
    d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5

    return 3000 * (1 + 100*(1-math.exp(-d/1415)))/(1+va/10)


difficulte_params = {
    "a": np.float64(4.65958056e00),
    "b": np.float64(4.68417236e-01),
    "c": np.float64(1.10653816e00),
    "d": np.float64(1.06018296e-01),
    "e": np.float64(1.56116282e02),
}


def difficulte_chasse1(
    chasse,
    initial,
    a=difficulte_params["a"],
    b=difficulte_params["b"],
    c=difficulte_params["c"],
    d=difficulte_params["d"],
    e=difficulte_params["e"],
):
    return np.round(e + a * (chasse ** c) + b * (chasse ** d) * initial).astype(
        np.int64
    )


difficulte2_params = {
    "a": np.float64(4.68367882),
    "p": np.float64(1.05999077e-01),
    "c": np.float64(1.55860356e02),
}


def difficulte_chasse2(
    chasse,
    initial,
    a=difficulte2_params["a"],
    p=difficulte2_params["p"],
    c=difficulte2_params["c"],
):
    return np.round(
        c + a * (chasse ** (p + 1)) + (a / 10) * (chasse ** p) * initial
    ).astype(np.int64)


def difficulte_n_chasse2(
    chasse,
    initial,
    n,
    a=difficulte2_params["a"],
    p=difficulte2_params["p"],
    c=difficulte2_params["c"],
    return_chasses=False,
):
    chasses = []
    chasse = np.float64(chasse)
    t = 0
    for i in range(n):
        r = difficulte_chasse2(chasse//n, initial + i*(chasse//n), a=a, p=p, c=c)
        t += r
        chasses.append((int(chasse/n), r))

    # ratio = chasse / initial
    # r = n * c + (a / 20) * chasse ** (1 + p) * (n ** (-p) * (19 + n * (1 + 2 / ratio)))

    # m = (a/20) * initial ** (1 +p) * \
    #     n ** (-p) * \
    #     1/rapp
    # rrrrr = 1/(m * (19 +n))**(1/(1+p))
    # 1 / 1/(ratio ** (1 + p) * (19 + n + 2 * n / ratio)) = m
    # ratio ** (1+p) * (19 + n + 2*n / ratio) = 1/m
    # ratio ** (1+p) * (19 * ratio/ ratio + n*ratio/ratio + 2*n/ratio)
    # ratio ** (1+p) * (19 * ratio + n* ratio + 2*n)/ratio
    # ratio ** (p) * (19 * ratio + n * ratio + 2*n)
    # ratio ** (p) * (ratio * (19 +n) + 2*n)

    # ratio ** (p) * ratio * (19 +n) + ratio ** p * 2 * n = 1/m
    # (19+n) * ratio ** (p+1) + 2*n * ratio ** p = 1/m
    # r = ratio **p
    # (19+n) * r **(1 + 1/p) + 2*n * r = 1/m

    # ratio ** (p) * ratio * (19 +n) = 1/m
    # ratio ** (p+1) = 1/(m*(19+n))

    if return_chasses:
        return t, chasses
    return t


def recompute_params(f, initial_params, data, loss):
    def to_optimize(params):
        err = np.float64()

        for inputs, expected in data:
            err += loss(pred=f(*inputs, *params), gt=expected)
        return err

    return scipy.optimize.minimize(
        to_optimize,
        x0=initial_params,
        bounds=list((i * 0.9, i * 1.1) for i in initial_params),
        method="Powell",
    )


def format_matrix_to_data(init_idx, chasse_idx, data_mat):
    data = []
    for i, init in enumerate(init_idx):
        for j, chasse in enumerate(chasse_idx):
            data.append(((chasse, init), data_mat[i, j]))

    return data


if __name__ == "__main__":
    print(difficulte_n_chasse2(160000, 20000, 2))
    print(difficulte_n_chasse2(160000, 20000, 2))
    print(difficulte_n_chasse2(160000, 20000, 3))
    print(difficulte_n_chasse2(160000, 20000, 4))
    print(difficulte_n_chasse2(160000, 20000, 5))
    print(difficulte_n_chasse2(160000, 40000, 5))
