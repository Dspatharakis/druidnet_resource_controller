from project import db
# from bson.objectid import ObjectId


#define db table
class Rate(db.Model):
    __tablename__ = "rates"
    id = db.Column(db.Integer, primary_key=True)
    req_rate_flavor_small = db.Column(db.Float, nullable=False)
    req_rate_flavor_medium = db.Column(db.Float, nullable=False)
    req_rate_flavor_big = db.Column(db.Float, nullable=False)
    active_requests_flavor_small = db.Column(db.Integer, nullable=False)
    active_requests_flavor_medium = db.Column(db.Integer, nullable=False)
    active_requests_flavor_big = db.Column(db.Integer, nullable=False)
    time_passed_since_last_event = db.Column(db.Float, nullable=False)
    time_of_experiment = db.Column(db.Float, nullable=False)
    queue_size = db.Column(db.Float, nullable=False)
    queue_trigger = db.Column(db.Integer, nullable=False)
    average_response_time = db.Column(db.Float, nullable=False)
    accumulative_response_time = db.Column(db.Float, nullable=False)
    counter_requests = db.Column(db.Float, nullable=False)
    interval_time = db.Column(db.Float, nullable=False)
    process_rate_flavor_small = db.Column(db.Float, nullable=False)
    process_rate_flavor_medium = db.Column(db.Float, nullable=False)
    process_rate_flavor_big = db.Column(db.Float, nullable=False)
    replicas_flavor_small = db.Column(db.Float, nullable=False)
    replicas_flavor_medium = db.Column(db.Float, nullable=False)
    replicas_flavor_big = db.Column(db.Float, nullable=False)
    rejected_requests = db.Column(db.Float, nullable=False)
    total_requests = db.Column(db.Float, nullable=False)
    percentage_rejected = db.Column(db.Float, nullable=False)


    def __init__(self, req_rate_flavor_small,req_rate_flavor_medium,req_rate_flavor_big, active_requests_flavor_small, active_requests_flavor_medium, active_requests_flavor_big,time_passed_since_last_event,time_of_experiment,queue_size,queue_trigger,average_response_time,accumulative_response_time, counter_requests,interval_time,process_rate_flavor_small,process_rate_flavor_medium, process_rate_flavor_big, replicas_flavor_small,replicas_flavor_medium,replicas_flavor_big,rejected_requests, total_requests, percentage_rejected):
        self.req_rate_flavor_small = req_rate_flavor_small
        self.req_rate_flavor_medium = req_rate_flavor_medium
        self.req_rate_flavor_big = req_rate_flavor_big
        self.active_requests_flavor_small = active_requests_flavor_small
        self.active_requests_flavor_medium = active_requests_flavor_medium
        self.active_requests_flavor_big = active_requests_flavor_big
        self.time_passed_since_last_event = time_passed_since_last_event
        self.time_of_experiment  = time_of_experiment 
        self.queue_size = queue_size
        self.queue_trigger = queue_trigger
        self.average_response_time = average_response_time
        self.accumulative_response_time = accumulative_response_time
        self.counter_requests = counter_requests
        self.interval_time = interval_time
        self.process_rate_flavor_small = process_rate_flavor_small
        self.process_rate_flavor_medium = process_rate_flavor_medium
        self.process_rate_flavor_big = process_rate_flavor_big
        self.replicas_flavor_small = replicas_flavor_small
        self.replicas_flavor_medium = replicas_flavor_medium
        self.replicas_flavor_big = replicas_flavor_big
        self.rejected_requests = rejected_requests
        self.total_requests = total_requests
        self.percentage_rejected = percentage_rejected


