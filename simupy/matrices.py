import numpy as np
import sympy as sp
from sympy.physics.mechanics import dynamicsymbols
from simupy.systems import DynamicalSystem
from simupy.utils import callable_from_trajectory


def construct_explicit_matrix(name, n, m, symmetric=False, diagonal=0,
                              dynamic=False, **kwass):
    """
    construct a matrix of symbolic elements

    args:
    name - string base name for variables; each variable is name_ij, which
        admitedly only works clearly for n,m < 10
    n - number of rows
    m - number of columns
    symmetric - use to enforce a symmetric matrix (repeat symbols above/below
        diagonal)
    diagonal - zeros out off diagonals. takes precedence over symmetry.
    dynamic - use sympy.physics.mechanics.dynamicsymbol (defaults to
        sp.symbols)

    kwargs: remaining kwargs passed to symbol function

    returns sympy.Matrix of explicit symbolic elements
    """
    if dynamic:
        symbol_func = dynamicsymbols
    else:
        symbol_func = sp.symbols

    if n != m and (diagonal or symmetric):
        raise ValueError("Cannot make symmetric or diagonal if n != m")

    if diagonal:
        return sp.diag(
            *[symbol_func(
                name+'_{}{}'.format(i+1, i+1), **kwass) for i in range(m)])
    else:
        matrix = sp.Matrix([
            [symbol_func(name+'_{}{}'.format(j+1, i+1), **kwass)
             for i in range(m)] for j in range(n)
        ])

        if symmetric:
            for i in range(1, m):
                for j in range(i):
                    matrix[i, j] = matrix[j, i]
        return matrix


def matrix_subs(*subs):
    """
    pass in 2-tuples of (symbolic,numeric) matrices OR dict of {symbolic:
    numeric} pairs

    returns object that can be passed into sp.subs
    """
    # I guess checking symmetry would be better, this will do for now.
    if len(subs) == 2 and not isinstance(subs[0], (list, tuple, dict)):
        subs = [subs]
    if isinstance(subs, (list, tuple)):
        return tuple(
            (sub[0][i, j], sub[1][i, j])
            for sub in subs
            for i in range(sub[0].shape[0])
            for j in range(sub[0].shape[1]) if sub[0][i, j] != 0
        )
    elif isinstance(subs, dict):
        return {
            sub[0][i, j]: sub[1][i, j]
            for sub in subs.items()
            for i in range(sub[0].shape[0])
            for j in range(sub[0].shape[1]) if sub[0][i, j] != 0
        }


def block_matrix(blocks):
    """
    construct a block matrix, element by element
    """
    return sp.Matrix.col_join(
        *tuple(
            sp.Matrix.row_join(
                *tuple(mat for mat in row)) for row in blocks
        )
    )


def matrix_callable_from_vector_trajectory(tt, x, unraveled, raveled):
    """
    convert a trajectory into an interpolating callable that returns a matrix.

    tt: m time indeces
    x: m x n vector of samples
    unravled: list of symbols in the same order of the data x
    raveled: matrix-like of symbols in the desired positions

    """
    xn, xm = x.shape

    vector_callable = callable_from_trajectory(tt, x)
    if isinstance(unraveled, sp.Matrix):
        unraveled = sp.flatten(unraveled.tolist())

    def matrix_callable(t):
        vector_result = vector_callable(t)
        as_array = False
        if isinstance(t, (list, tuple, np.ndarray)) and len(t) > 1:
            matrix_result = np.zeros((len(t),)+raveled.shape)
            as_array = True
        else:
            matrix_result = np.matlib.zeros(raveled.shape)

        iterator = np.nditer(raveled, flags=['multi_index', 'refs_ok'])
        for it in iterator:
            i, j = iterator.multi_index
            idx = unraveled.index(raveled[i, j])
            if as_array:
                matrix_result[..., i, j] = vector_result[idx]
            else:
                matrix_result[i, j] = vector_result[idx]
        return matrix_result

    return matrix_callable


def system_from_matrix_DE(mat_DE, mat_var, mat_input=sp.Matrix([]),
                          constants={}):
    # Sorry, not going to be clever and allow sets of DEs and variable matrices
    vec_var = list(set(sp.flatten(mat_var.tolist())))
    vec_DE = sp.Matrix.zeros(len(vec_var), 1)

    iterator = np.nditer(mat_DE, flags=['multi_index', 'refs_ok'])
    for it in iterator:
        i, j = iterator.multi_index
        idx = vec_var.index(mat_var[i, j])
        vec_DE[idx] = mat_DE[i, j]

    sys = DynamicalSystem(vec_DE, sp.Matrix(vec_var), mat_input,
                          constants_values=constants)
    return sys
