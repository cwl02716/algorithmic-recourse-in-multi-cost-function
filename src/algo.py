import math
import igraph as ig
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import kneighbors_graph


def make_knn_adj(df: pd.DataFrame, k: int) -> csr_matrix:
    X = df.drop(columns="50K")
    A = kneighbors_graph(X, k)
    assert isinstance(A, csr_matrix)
    return A


def adj_to_graph(A: csr_matrix) -> ig.Graph:
    graph = ig.Graph.Adjacency(A.astype(np.int_))
    return graph


def cost(df: pd.DataFrame, i: int, j: int) -> tuple[float, float]:
    time = 0.0
    payment = 0.0
    a: pd.Series[float] = df.loc[i]  # type: ignore
    b: pd.Series[float] = df.loc[j]  # type: ignore

    # for age
    time = max(time, b["age"] - a["age"])

    # education
    time = max(time, b["education-num"] - a["education-num"])

    # workclass
    time = max(time, b["workclass"] - a["workclass"])

    # sigmoid(workclass : hours-per-week)
    m = a["workclass"] / a["hours-per-week"] - b["workclass"] / b["hours-per-week"]
    payment += 1.0 / (1.0 + math.exp(m))

    # gain and loss
    payment += b["capital-gain"] - a["capital-gain"]
    payment -= b["capital-loss"] - a["capital-loss"]

    return time, payment


def merge(
    dists: list[set[tuple[float, float]]],
    i: int,
    j: int,
    w: tuple[float, float],
    *,
    limit: int = 100000,
) -> None:
    u = dists[i]
    v = dists[j]

    new_v = {(x[0] + w[0], x[1] + w[1]) for x in u}
    v.update(new_v)

    if len(v) > limit:
        raise ValueError("too many paths")


def set_cost(graph: ig.Graph, df: pd.DataFrame) -> None:
    for e in graph.es:
        u, v = e.tuple
        e["cost"] = cost(df, u, v)


def multicost_shortest_path(
    graph: ig.Graph,
    source: int,
    *,
    limit: int = 100000,
) -> list[set[tuple[float, float]]]:
    dists = [set() for _ in range(graph.vcount())]
    dists[source].add((0.0, 0.0))
    # use s-u to u-v to merge s-v
    for _ in range(graph.vcount() - 1):
        for e in graph.es:
            u, v = e.tuple
            merge(dists, u, v, e["cost"], limit=limit)
    return dists


def recourse(
    df: pd.DataFrame,
    source: int,
    *,
    limit: int = 100000,
) -> list[set[tuple[float, float]]]:
    adj = make_knn_adj(df, 5)
    graph = adj_to_graph(adj)
    set_cost(graph, df)
    dists = multicost_shortest_path(graph, source, limit=limit)
    return dists


def dominant_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    points.sort(key=lambda point: (-point[1], point[0]))
    dominant_points_list: list[tuple[float, float]] = []

    for point in points:
        #  A point (x1, y1) is dominated by another point (x2, y2) if x1 < x2 and y1 < y2.
        is_dominated = any(
            point[0] > x and point[1] > y for x, y in dominant_points_list
        )

        if not is_dominated:
            dominant_points_list.append(point)

            if len(dominant_points_list) == 5:
                break

    return dominant_points_list
