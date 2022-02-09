# project/main/views.py
import base64
from sys import prefix
from celery.result import AsyncResult
from flask import render_template, Blueprint, jsonify, request
from project import app, db, mongo_db
from project.models import Rate, FileContent
import time
import os
import uuid
from project.tasks import create_task_queue



main_blueprint = Blueprint("main", __name__,)


@main_blueprint.route("/tasks", methods=["POST"])
def run_task():
    start_time = time.time()
    file = request.files['file']
    filename_prefix = str(uuid.uuid4())
    file.save(os.path.join('/tmp/', filename_prefix))
    print ("image saving time: ", time.time() - start_time)
    # from project.tasks import create_task_queue
    task = create_task_queue.delay(filename_prefix, start_time)
    return jsonify({"image name": filename_prefix}), 202


