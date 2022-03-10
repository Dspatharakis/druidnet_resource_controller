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

logger = get_task_logger(__name__)

@celery.task(name="create_task_red", queue="red")
def create_task_red(img_id,start_time): # kubernetes access with nodeport and exposed port
    preprocess_time = time.time()-start_time
    print ("preprocess_time:" , preprocess_time)
    try:
        result = requests.post("http://app1:6004/",files={"file": open('/tmp/'+img_id,"rb")}) #"http://app1:6004/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        print('Error while trying to post once: {}'.format(err))
    rt = time.time() - start_time
    print ("rt:" , rt)
    os.remove('/tmp/'+img_id)
    data = Rate.query.first()
    art = time.time() - start_time
    data.accumulative_response_time = data.accumulative_response_time + art
    data.active_requests_app1 = data.active_requests_app1 - 1
    data.counter_requests = data.counter_requests + 1
    db.session.commit()
    return True

@celery.task(name="create_task_green", queue="green")
def create_task_green(img_id, start_time):
    preprocess_time = time.time()-start_time
    print ("preprocess_time:" , preprocess_time)
    try:
        result = requests.post("http://app2:6005/",files={"file": open('/tmp/'+img_id,"rb")}) #"http://app2:6005/", timeout=45)
    except requests.exceptions.ConnectionError as err:
        print('Error while trying to post once: {}'.format(err))
    rt = time.time() - start_time
    print ("rt:" , rt)
    os.remove('/tmp/'+img_id)
    data = Rate.query.first()
    art = time.time() - start_time
    data.accumulative_response_time = data.accumulative_response_time + art
    data.active_requests_app2 = data.active_requests_app2 - 1
    data.counter_requests = data.counter_requests + 1
    db.session.commit()
    return True

@celery.task(name="create_task_queue", queue="queue")
def create_task_queue(img_id,start_time):
    print ("Image queue id:", img_id)
    data = Rate.query.first()
    req_rate_app1 = data.req_rate_app1 
    req_rate_app2 = data.req_rate_app2 
    propability = random.randint(0,(int(req_rate_app1)+int(req_rate_app2)))
    data = Rate.query.first()
    if propability < req_rate_app1:  
        task = create_task_red.delay(img_id,start_time)
        data.active_requests_app1 = data.active_requests_app1 + 1
    else: 
        task = create_task_green.delay(img_id,start_time)
        data.active_requests_app2 = data.active_requests_app2 + 1
    db.session.commit()
    return True

@celery.task(queue='celery_periodic')
def update_per_interval():
    from project import celery
    client = celery.connection().channel().client
    length = client.llen('queue')
    try:
        data = Rate.query.first()
        time_passed = 1
        if data.time_passed_since_last_event >= int(os.environ.get("event_cooldown", "2")): 
            if (length == 0):
                print ("queue is empty")
                data.process_rate_app1 = float(os.environ.get("beta1", "0.5")) *  data.req_rate_app1 + math.sqrt(2* float(os.environ.get("alpha1", "2"))*data.active_requests_app1)
                data.process_rate_app2 = float(os.environ.get("beta2", "0.5")) *  data.req_rate_app2 + math.sqrt(2* float(os.environ.get("alpha2", "2"))*data.active_requests_app2)
                # Need a proper mapping between \gamma and replicas
                data.replicas_app1 = data.process_rate_app1 // data.process_rate_app1
                data.replicas_app2 = data.process_rate_app2 // data.process_rate_app2
                data.queue_trigger = 2 
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