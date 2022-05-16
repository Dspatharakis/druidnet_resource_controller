from flask.cli import FlaskGroup
from project import app
from project.models import Rate

cli = FlaskGroup(app)

from project import db

@cli.command("create_db")
def create_db():
    db.drop_all()
    db.create_all()
    db.session.commit()

@cli.command("seed_db")
def seed_db():
    db.session.add(Rate(req_rate_flavor_small=0.1,req_rate_flavor_medium=1, req_rate_flavor_big=1, active_requests_flavor_small=0, active_requests_flavor_medium=0, active_requests_flavor_big=0, time_passed_since_last_event=0,time_of_experiment = 0,queue_size=0,queue_trigger=1,average_response_time=0,accumulative_response_time=0,counter_requests=0,interval_time=0,process_rate_flavor_small=1,process_rate_flavor_medium=1,process_rate_flavor_big=1,replicas_flavor_small=1,replicas_flavor_medium=1,replicas_flavor_big=1, rejected_requests =0, total_requests=0, percentage_rejected=0))
    db.session.commit()

if __name__ == "__main__":
    cli()