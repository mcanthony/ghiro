# Ghiro - Copyright (C) 2013-2015 Ghiro Developers.
# This file is part of Ghiro.
# See the file 'docs/LICENSE.txt' for license terms.

import json

from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from ghiro.common import log_activity
from api.common import api_authenticate
from analyses.models import Case, Analysis
from lib.db import save_file
from lib.utils import create_thumb

@require_POST
@csrf_exempt
def new_case(request):
    """Creates a new case."""
    user = api_authenticate(request.POST.get("api_key"))

    if request.POST.get("name"):
        case = Case(name=request.POST.get("name"),
                    description=request.POST.get("description"),
                    owner=user)
        case.save()

        # Auditing.
        log_activity("C",
                     "Created new case via API %s" % case.name,
                     request,
                     user)

        response_data = {"id": case.id}
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse("Request not valid", status=400)

@require_POST
@csrf_exempt
def show_case(request):
    """Shows a case."""
    user = api_authenticate(request.POST.get("api_key"))

    if request.POST.get("case_id"):
        case = get_object_or_404(Case, pk=request.POST.get("case_id"))

        # Security check.
        if not case.can_read(user):
            return HttpResponse("You are not authorized to read this case", status=400)

        response_data = {"id": case.id, "status": case.state, "name": case.name,
                         "description": case.description, "images":
                             [image.id for image in case.images.all()]}
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse("Missing parameter case_id", status=400)

@require_POST
@csrf_exempt
def new_image(request):
    """Upload a new image."""
    user = api_authenticate(request.POST.get("api_key"))

    if request.POST.get("case_id"):
        case = get_object_or_404(Case, pk=request.POST.get("case_id"))

        # Security check.
        if not case.can_write(user):
            return HttpResponse("You are not authorized to add image to this", status=400)

        if case.state == "C":
            return HttpResponse("You cannot add an image to a closed case", status=400)
    else:
        case = None

    task = Analysis.add_task(request.FILES["image"].temporary_file_path(),
                    file_name=request.FILES["image"].name, case=case, user=user,
                    content_type=request.FILES["image"].content_type,
                    image_id=save_file(file_path=request.FILES["image"].temporary_file_path(),
                              content_type=request.FILES["image"].content_type),
                    thumb_id=create_thumb(request.FILES["image"].temporary_file_path()))

    # Auditing.
    log_activity("I",
                 "Created new analysis via API %s" % task.file_name,
                 request,
                 user=user)

    response_data = {"id": task.id}
    return HttpResponse(json.dumps(response_data), content_type="application/json")

@require_POST
@csrf_exempt
def get_report(request):
    """Returns a report."""
    user = api_authenticate(request.POST.get("api_key"))

    if request.POST.get("task_id"):
        task = get_object_or_404(Analysis, pk=request.POST.get("task_id"))

        # Security check.
        if not task.can_read(user):
            return HttpResponse("You are not authorized to read this analysis", status=400)

        if task.state == "C":
            response_data = {"id": task.id, "status": task.state, "data": task.to_json}
        else:
            response_data = {"id": task.id, "status": task.state}
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse("Missing parameter task_id", status=400)