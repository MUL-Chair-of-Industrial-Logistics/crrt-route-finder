import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

DEBUG = False


def debug(message):
    if DEBUG:
        print(message)


def evaluate_contiguous_sections(min_freight_amount, min_d, df_contiguous_sections):
    df_notnull = df_contiguous_sections[df_contiguous_sections["freight_amount"] > min_freight_amount]
    df_notnull = df_notnull[df_notnull["distance"] > min_d]
    df_notnull.reset_index(drop=True, inplace=True)

    xs = df_notnull["distance"]
    ys = df_notnull["freight_amount"]

    # Get the indices of points in the Pareto front
    # pareto_front = get_pareto_front(xs, ys, data)

    # pf_X = [pair[0] for pair in pareto_front]
    # pf_Y = [pair[1] for pair in pareto_front]
    # pf_data = [pair[2] for pair in pareto_front]
    # df_pareto = pd.DataFrame(data={'x': pf_X, 'y': pf_Y, 'd': pf_data})
    # adjust for equal y-values

    # df_pareto = df_pareto[df_pareto["x"] > 550]
    # df_pareto = df_pareto[df_pareto["y"] > 600].copy()
    # df_pareto["keep"] = df_pareto.apply(lambda row: get_max_y_values(row), axis=1)
    # df_pareto = df_pareto[df_pareto["keep"] == 1]

    fig, ax = plt.subplots(figsize=(7, 7))

    ax.scatter(xs, ys, marker='.', label='Section comb.')
    # ax.plot(pf_X, pf_Y, color='r', label='Pareto Frontier')

    # ax.scatter(df_pareto["x"], df_pareto["y"], facecolors='none', edgecolors='r', marker='o', label='Best comb.')

    # df_pareto["xy"] = df_pareto.apply(lambda row: (row["x"], row["y"]), axis=1)
    # print(df_pareto.info())
    # print(df_pareto)

    ax.set_xlabel("Distance $d$, $[d]=km$")
    ax.set_ylabel("Yearly freight amount $f$, $[f]=TEU$")
    # ax.set_title("Freight amount and distances of section combinations having $f>f_{min}$ and $d>d_{min}$")
    ax.axhline(y=min_freight_amount, color='g', linestyle='--', label='$f_{min}=' + str(min_freight_amount) + 'TEU$')
    ax.axvline(x=min_d, color='orange', linestyle='--', label='$d_{min}=' + str(min_d) + 'km$')
    ax.legend(loc='lower left', fancybox=True, framealpha=1)
    ax.grid(True)
    # ax.set_xlim([90, 750])
    # ax.set_ylim([90, 1200])
    ax.set_title("Section combinations having $f>f_{min}$ and $d>d_{min}$")
    fig.tight_layout()
    plt.show()
    # plt.savefig('output/subsections_paretofront_small.svg')


def get_pareto_front(Xs, Ys, data, maxX=True, maxY=True):
    sorted_list = sorted([[Xs[i], Ys[i], data[i]] for i in range(len(Xs))], reverse=maxY)
    pareto_front = [sorted_list[0]]
    for pair in sorted_list[1:]:
        if maxY:
            if pair[1] >= pareto_front[-1][1]:
                pareto_front.append(pair)
        else:
            if pair[1] <= pareto_front[-1][1]:
                pareto_front.append(pair)

    return pareto_front


def get_max_y_values(row):
    global y_values
    if row["y"] in y_values:
        return 0
    y_values.append(row["y"])
    return 1
