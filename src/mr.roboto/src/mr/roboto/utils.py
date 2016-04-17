# -*- coding: utf-8 -*-
import pickle


def get_pickled_data(filename):
    return pickle.loads(open(filename).read())
