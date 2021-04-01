"""
# please install scikit-optimize
# provide max cc limit, HOST, PORT of the server in main functions
1. send message: "start" to start the optmizer
2. it will send back cc value for probing, for example: "1" and will wait for throughput value
3. send back throughput values in Mbps, for example: "10000.07"
4. send "-1" to terminate the optimizer
"""
import warnings
import socket
import numpy as np
import time
import logging as logger
from skopt.space import Integer
from skopt import Optimizer as BO

warnings.filterwarnings('ignore')

log_FORMAT = '%(created)f -- %(levelname)s: %(message)s'
logger.basicConfig(format=log_FORMAT, 
                    datefmt='%m/%d/%Y %I:%M:%S %p', 
                    level=logger.INFO)


recv_buffer_size = 8192
  

def harp_response(params):
    global sock, max_cc
    cc = params[0]
    logger.info("Sample Transfer -- Probing Parameters: {0}".format(params))
    thrpt = 0
    
    output = str(cc)
    sock.sendall(output.encode('utf-8'))
    
    while True:
        try:
            message  = sock.recv(recv_buffer_size).decode()
            thrpt = float(message)
            
            if thrpt is not None:
                break
            
        except Exception as e:
            logger.exception(e)
                
    if thrpt == -1:
        score = thrpt
    else:
        cc_factor = (cc - 1)/max_cc
        score = np.round(thrpt * (1 - cc_factor) * (-1))
    
    logger.info("Sample Transfer -- Throughput: {0}Mbps, Score: {1}".format(
        np.round(thrpt), score))
    return score


def base_optimizer(black_box_function):
    global max_cc
    limit_obs, count = 100, 0
    max_thread = max_cc
    search_space  = [Integer(1, max_thread)]
        
    optimizer = BO(
        dimensions=search_space,
        base_estimator="GP", #[GP, RF, ET, GBRT],
        acq_func="gp_hedge", # [LCB, EI, PI, gp_hedge]
        acq_optimizer="auto", #[sampling, lbfgs, auto]
        n_random_starts=5,
        model_queue_size= limit_obs,
    )
        
    while True:
        count += 1

        if len(optimizer.yi) > limit_obs:
            optimizer.yi = optimizer.yi[-limit_obs:]
            optimizer.Xi = optimizer.Xi[-limit_obs:]
            
        logger.info("Iteration {0} Starts ...".format(count))

        t1 = time.time()
        res = optimizer.run(func=black_box_function, n_iter=1)
        t2 = time.time()

        logger.info("Iteration {0} Ends, Took {3} Seconds. Best Params: {1} and Score: {2}.".format(
            count, res.x, res.fun, np.round(t2-t1, 2)))

        if optimizer.yi[-1] == -1:
            logger.info("Optimizer Exits ...")
            break


if __name__ == '__main__':
    max_cc = 64
    HOST, PORT = "localhost", 32000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    
    if sock.recv(recv_buffer_size).decode() == "start":
        base_optimizer(harp_response)
    
    sock.close()