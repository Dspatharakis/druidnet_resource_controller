import requests
import random
import time
import os
import math
from project import db, celery
from project.models import Rate
from psycopg2 import InternalError
from celery.utils.log import get_task_logger
from functools import reduce

logger = get_task_logger(__name__)

@celery.task(name="create_task_flavor_small", queue="flavor_small")
def create_task_flavor_small(img_id,start_time): # kubernetes access with nodeport and exposed port
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_flavor_small = active_requests_flavor_small + 1")
        conn.commit()
    try:
        result = requests.post("http://flavor-small:6004/",files={"file": open('/tmp/'+img_id,"rb")}, timeout=3) #"http://flavor_small:6004/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        with db.session() as conn:
            conn.execute("UPDATE rates SET rejected_requests = rejected_requests + 1")
            conn.execute("UPDATE rates SET active_requests_flavor_small = active_requests_flavor_small - 1")
            conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
            conn.commit()
        print('Error while trying to post once: {}'.format(err))
        return False
    os.remove('/tmp/'+img_id)
    art = time.time() - start_time
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_flavor_small = active_requests_flavor_small - 1")
        conn.execute("UPDATE rates SET accumulative_response_time = accumulative_response_time + '%s'" % art)
        conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
        conn.commit()
    return True

@celery.task(name="create_task_flavor_medium", queue="flavor_medium")
def create_task_flavor_medium(img_id, start_time):
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_flavor_medium = active_requests_flavor_medium + 1")
        conn.commit()
    try:
        result = requests.post("http://flavor-medium:6004/",files={"file": open('/tmp/'+img_id,"rb" )},timeout=3) #"http://flavor_medium:6005/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        with db.session() as conn:
            conn.execute("UPDATE rates SET rejected_requests = rejected_requests + 1")
            conn.execute("UPDATE rates SET active_requests_flavor_medium = active_requests_flavor_medium - 1")
            conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
            conn.commit()
        print('Error while trying to post once: {}'.format(err))
        return False
    os.remove('/tmp/'+img_id)
    art = time.time() - start_time
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_flavor_medium = active_requests_flavor_medium - 1")
        conn.execute("UPDATE rates SET accumulative_response_time = accumulative_response_time + '%s'" % art)
        conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
        conn.commit()
    return True

@celery.task(name="create_task_flavor_big", queue="flavor_big")
def create_task_flavor_big(img_id, start_time):
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_flavor_big = active_requests_flavor_big + 1")
        conn.commit()
    try:
        result = requests.post("http://flavor-big:6004/",files={"file": open('/tmp/'+img_id,"rb") },timeout=3) #"http://flavor_big:6005/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        with db.session() as conn:
            conn.execute("UPDATE rates SET rejected_requests = rejected_requests + 1")
            conn.execute("UPDATE rates SET active_requests_flavor_big = active_requests_flavor_big - 1")
            conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
            conn.commit()
        print('Error while trying to post once: {}'.format(err))
        return False
    os.remove('/tmp/'+img_id)
    art = time.time() - start_time
    with db.session() as conn:
        conn.execute("UPDATE rates SET active_requests_flavor_big = active_requests_flavor_big - 1")
        conn.execute("UPDATE rates SET accumulative_response_time = accumulative_response_time + '%s'" % art)
        conn.execute("UPDATE rates SET counter_requests = counter_requests + 1")
        conn.commit()
    return True

@celery.task(name="create_task_queue", queue="queue")
def create_task_queue(img_id,start_time):
    print ("Image queue id:", img_id)
    data = Rate.query.first()
    req_rate_flavor_small = data.req_rate_flavor_small 
    req_rate_flavor_medium = data.req_rate_flavor_medium 
    req_rate_flavor_big = data.req_rate_flavor_big
    sum = req_rate_flavor_small + req_rate_flavor_medium + req_rate_flavor_big 
    d = [req_rate_flavor_small, req_rate_flavor_medium, req_rate_flavor_big]
    p = map(lambda pc:pc/sum,d)
    c = reduce(lambda c, x: c+[c[-1]+x], p,[0])[1:]
    rand = random.uniform(0,1)
    host_id = next(i for i, v in enumerate(c) if v > rand)
    print ("Host id:", host_id)
    if host_id == 0:  
        create_task_flavor_small.delay(img_id,start_time)
    elif host_id ==1:
        create_task_flavor_medium.delay(img_id,start_time)
    elif host_id ==2:
        create_task_flavor_big.delay(img_id,start_time)
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

                # os.environ["beta1"] = str(1 / (data.req_rate_flavor_small + data.req_rate_flavor_medium))
                # os.environ["beta2"] = str(1 / (data.req_rate_flavor_small + data.req_rate_flavor_medium))
                try: 
                    data.process_rate_flavor_small = float(os.environ.get("beta1", "0.5")) *  data.req_rate_flavor_small + math.sqrt(2* float(os.environ.get("alpha1", "2"))*data.active_requests_flavor_small)
                except ValueError as err:
                    print('Error while trying to calculate process rate1: {}'.format(err))
                    data.process_rate_flavor_small = float(os.environ.get("beta1", "0.5")) *  data.req_rate_flavor_small
                try:
                    data.process_rate_flavor_medium = float(os.environ.get("beta2", "0.5")) *  data.req_rate_flavor_medium + math.sqrt(2* float(os.environ.get("alpha2", "2"))*data.active_requests_flavor_medium)
                except ValueError as err:
                    print('Error while trying to calculate process rate2: {}'.format(err))
                    data.process_rate_flavor_medium = float(os.environ.get("beta2", "0.5")) *  data.req_rate_flavor_medium
                try:
                    data.process_rate_flavor_big = float(os.environ.get("beta3", "0.5")) *  data.req_rate_flavor_big + math.sqrt(2* float(os.environ.get("alpha3", "2"))*data.active_requests_flavor_big)
                except ValueError as err:
                    print('Error while trying to calculate process rate3: {}'.format(err))
                    data.process_rate_flavor_big = float(os.environ.get("beta3", "0.5")) *  data.req_rate_flavor_big
                # Need a proper mapping between \gamma and replicas
                data.replicas_flavor_small = data.process_rate_flavor_small // float(os.environ.get("flavor_small", "2"))
                if data.replicas_flavor_small < 1 : data.replicas_flavor_small = 1
                data.replicas_flavor_medium = data.process_rate_flavor_medium // float(os.environ.get("flavor_medium", "10"))
                if data.replicas_flavor_medium < 1 : data.replicas_flavor_medium = 1
                data.replicas_flavor_big = data.process_rate_flavor_big // float(os.environ.get("flavor_big", "20"))
                if data.replicas_flavor_big < 1 : data.replicas_flavor_big = 1

                data.time_passed_since_last_event = 0 
                time_passed = 0
        req_flavor_small = float(os.environ.get("beta1", "0.5")) * data.req_rate_flavor_small + float(os.environ.get("alpha1", "2"))*(data.time_passed_since_last_event+time_passed)
        req_flavor_medium = float(os.environ.get("beta2", "0.5")) * data.req_rate_flavor_medium + float(os.environ.get("alpha2", "3"))*(data.time_passed_since_last_event+time_passed)
        req_flavor_big = float(os.environ.get("beta2", "0.5")) * data.req_rate_flavor_big + float(os.environ.get("alpha3", "3"))*(data.time_passed_since_last_event+time_passed)
        
        if req_flavor_small < 0.5: req_flavor_small=0.5
        if req_flavor_medium < 0.5: req_flavor_medium=0.5
        if req_flavor_big < 0.5: req_flavor_big=0.5
        data.req_rate_flavor_small = req_flavor_small
        data.req_rate_flavor_medium = req_flavor_medium
        data.req_rate_flavor_big = req_flavor_big
        data.time_passed_since_last_event = data.time_passed_since_last_event + time_passed 
        data.time_of_experiment = data.time_of_experiment + 1
        data.queue_size = length
        data.interval_time = data.interval_time + float(os.environ.get("CELERY_BEAT", "1"))
        if data.interval_time >= 1:
            if data.counter_requests > 0:
                art = data.accumulative_response_time / data.counter_requests
                data.average_response_time = art
            else: 
                data.average_response_time = 0
            data.interval_time = 0
            data.counter_requests = 0
            data.accumulative_response_time = 0
        db.session.commit()
        print ("Request Rate for flavor_small: ", data.req_rate_flavor_small, " Request Rate for flavor_medium: ",data.req_rate_flavor_medium, " Request Rate for flavor_big: ",data.req_rate_flavor_big)
        time_start = time.time()
        celery.control.rate_limit('create_task_queue', str(data.req_rate_flavor_small+ data.req_rate_flavor_medium + data.req_rate_flavor_big)+"/s", destination=['celery@queue_worker'])
        time_end = time.time()
        print ("Time to set rate: ", time_end - time_start)
    except InternalError:
        pass   