import numpy as np
import sys
import os


class Diagnostics(object):
    def __init__(self, params, pool=None):
        self.params = params
        self.pool = pool

        self.total_steps = 0
        self.means = np.zeros(len(params))
        self.m2 = np.zeros(len(params))

    def add_traces(self, traces):
        if traces.shape[1] != len(self.params):
            raise RuntimeError("The number of traces added to Diagnostics does not match the number of varied parameters!")

        num = float(self.total_steps)
        for x in traces:
            num += 1.0
            delta = x - self.means
            self.means += delta/num
            self.m2 += delta*(x - self.means)
        self.total_steps += traces.shape[0]

    def gelman_rubin(self):
        # takes current traces and returns 
        if self.pool is None:
            raise RuntimeError("Gelman-Rubin statistic is only valid for multiple chains")

        if self.total_steps == 0:
            raise RuntimeError("Gelman-Rubin statistic not defined for 0-length chains")

        # gather trace statistics to master process
        means = np.array(self.pool.gather(self.means)).T
        variances = np.array(self.pool.gather(self.m2/float(self.total_steps-1))).T

        if self.pool.is_master():
            B_over_n = np.var(means, ddof=1, axis=1)
            B = B_over_n * self.total_steps
            W = np.mean(variances, axis=1)
            V = (1. - 1./self.total_steps) * W + (1. + 1./self.pool.size) * B_over_n
            # TODO: check for 0-values in W
            Rhat = np.sqrt(V/W)
        else:
            Rhat = None
 
        Rhat = self.pool.bcast(Rhat)
        return Rhat