import requests
import random
import time
import string
from project import db, celery, mongo_db
from project.models import Rate, FileContent 
from psycopg2 import InternalError
from celery.utils.log import get_task_logger
from PIL import Image
import os
import math
from functools import reduce

logger = get_task_logger(__name__)

@celery.task(name="create_task_red", queue="red")
def create_task_red(img_id,start_time): # kubernetes access with nodeport and exposed port
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_app1 = active_requests_app1 + 1")
        conn.commit()
    try:
        result = requests.post("http://app1:6004/",files={"file": open('/tmp/'+img_id,"rb")}) #"http://app1:6004/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        print('Error while trying to post once: {}'.format(err))
    os.remove('/tmp/'+img_id)
    art = time.time() - start_time
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_app1 = active_requests_app1 - 1")
        conn.execute("UPDATE rates SET accumulative_response_time = accumulative_response_time + '%s'" % art)
        conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
        conn.commit()
    return True

@celery.task(name="create_task_green", queue="green")
def create_task_green(img_id, start_time):
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_app2 = active_requests_app2 + 1")
        conn.commit()
    try:
        result = requests.post("http://app2:6005/",files={"file": open('/tmp/'+img_id,"rb")}) #"http://app2:6005/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        print('Error while trying to post once: {}'.format(err))
    os.remove('/tmp/'+img_id)
    art = time.time() - start_time
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_app2 = active_requests_app2 - 1")
        conn.execute("UPDATE rates SET accumulative_response_time = accumulative_response_time + '%s'" % art)
        conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
        conn.commit()
    
    return True

@celery.task(name="create_task_queue", queue="queue")
def create_task_queue(img_id,start_time):
    print ("Image queue id:", img_id)
    data = Rate.query.first()
    req_rate_app1 = data.req_rate_app1 
    req_rate_app2 = data.req_rate_app2 
    # for i in range(2):  #TODO scale for workers 
        # sum += placement[topology][i] * workload_per_vdu[i] 
        # d[i] = placement[topology][i] * workload_per_vdu[i] 
    sum = req_rate_app1 + req_rate_app2
    d = [req_rate_app1, req_rate_app2]
    p = map(lambda pc:pc/sum,d)
    c = reduce(lambda c, x: c+[c[-1]+x], p,[0])[1:]
    rand = random.uniform(0,1)
    host_id = next(i for i, v in enumerate(c) if v > rand)
    print ("Host id:", host_id)
    # host_id=1
    if host_id == 0:  
        create_task_red.delay(img_id,start_time)
    else: 
        create_task_green.delay(img_id,start_time)
    return True

@celery.task(queue='celery_periodic')
def update_per_interval():
    from project import celery
    client = celery.connection().channel().client
    length = client.llen('queue')
    try:
        data = Rate.query.first()
        time_passed = 1
        if data.time_passed_since_last_event >= int(os.environ.get("event_cooldown", "0")): 
            if (length == 0):
                print ("Event! queue is empty")
                try: 
                    data.process_rate_app1 = float(os.environ.get("beta1", "0.5")) *  data.req_rate_app1 + math.sqrt(2* float(os.environ.get("alpha1", "2"))*data.active_requests_app1)
                except ValueError as err:
                    print('Error while trying to calculate process rate1: {}'.format(err))
                    data.process_rate_app1 = float(os.environ.get("beta1", "0.5")) *  data.req_rate_app1
                try:
                    data.process_rate_app2 = float(os.environ.get("beta2", "0.5")) *  data.req_rate_app2 + math.sqrt(2* float(os.environ.get("alpha2", "2"))*data.active_requests_app2)
                except ValueError as err:
                    print('Error while trying to calculate process rate2: {}'.format(err))
                    data.process_rate_app2 = float(os.environ.get("beta2", "0.5")) *  data.req_rate_app2
                # Need a proper mapping between \gamma and replicas
                data.replicas_app1 = data.process_rate_app1 // float(os.environ.get("flavor_app1", "2"))
                if data.replicas_app1 < 1 : data.replicas_app1 = 1
                data.replicas_app2 = data.process_rate_app2 // float(os.environ.get("flavor_app2", "10"))
                if data.replicas_app2 < 1 : data.replicas_app2 = 1
                data.queue_trigger = 2  #TODO: remove
                data.time_passed_since_last_event = 0 
                time_passed = 0
            else:
                data.queue_trigger = 1
        req1 = float(os.environ.get("beta1", "0.5")) * data.req_rate_app1 + float(os.environ.get("alpha1", "2"))*(data.time_passed_since_last_event+time_passed)
        req2 = float(os.environ.get("beta2", "0.5")) * data.req_rate_app2 + float(os.environ.get("alpha2", "3"))*(data.time_passed_since_last_event+time_passed)
        if req1 < 0.5: req1=0.5
        if req2 < 0.5: req2=0.5
        data.req_rate_app1 = req1
        data.req_rate_app2 = req2
        data.time_passed_since_last_event = data.time_passed_since_last_event + time_passed 
        data.time_of_experiment = data.time_of_experiment + 1
        data.queue_size = length
        data.interval_time = data.interval_time + 1
        if data.counter_requests > 0:
            art = data.accumulative_response_time / data.counter_requests
            data.average_response_time = art
        else: 
            data.average_response_time = 0
        data.counter_requests = 0
        data.accumulative_response_time = 0
        data.interval_time = 0 
        db.session.commit()
        print ("Request Rate for App1: ", data.req_rate_app1, " Request Rate for App2: ",data.req_rate_app2)
        celery.control.rate_limit('create_task_queue', str(data.req_rate_app2 + data.req_rate_app1)+"/s", destination=['celery@queue_worker'])

    except InternalError:
        pass   