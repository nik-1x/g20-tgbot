def convert_g2t(gram, price):
    # 2000000 * (0.004/10000)
    return gram * price


def convert_t2g(ton, price):
    # 0,8 / (0.004/10000)
    return ton / price
